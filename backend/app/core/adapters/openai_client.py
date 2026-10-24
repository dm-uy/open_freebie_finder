"""Owned OpenAI-compatible inference with scoped billing and semantic SSE boundaries."""
import asyncio
import anyio
import json
import time
from typing import Any, AsyncGenerator, Optional

import httpx

from backend.app.config import get_settings
from backend.app.core.discovery.privacy import private_http
from backend.app.core.eligibility.billing import BillingInterrupted, classify_billing
from backend.app.core.providers.models import ProviderManifest

MAX_RESPONSE_BYTES = 4 * 1024 * 1024


class UpstreamRateLimitError(Exception):
    def __init__(self, message, provider_id, raw_model_id, *, retry=None):
        from backend.app.core.balancer.resilience import retry_hint
        super().__init__(message)
        self.provider_id=provider_id
        self.raw_model_id=raw_model_id
        self.actual_http_status=429
        self.status_code=429
        self.failure_kind="http"
        self.retry_hint=retry or retry_hint(None)


class UpstreamProviderError(Exception):
    def __init__(self, message, status_code, provider_id, raw_model_id, billing_reason=None, *, failure_kind="http", retry=None):
        from backend.app.core.balancer.resilience import retry_hint
        super().__init__(message)
        self.status_code=status_code
        self.actual_http_status=status_code if failure_kind=="http" else None
        self.provider_id=provider_id
        self.raw_model_id=raw_model_id
        self.billing_reason=billing_reason
        self.failure_kind=failure_kind
        self.retry_hint=retry or retry_hint(None)


def semantic(delta):
    return isinstance(delta,dict) and any(value for key,value in delta.items() if key not in {"role"})


def error_code(data,default=502):
    error=data.get("error") if isinstance(data,dict) else None
    value=error.get("code") if isinstance(error,dict) else None
    return value if type(value) is int and 400<=value<=599 else default


def valid_completion(data):
    if not isinstance(data,dict) or "error" in data:
        return False
    choices=data.get("choices")
    if not isinstance(choices,list) or len(choices)!=1 or not isinstance(choices[0],dict):return False
    choice=choices[0]
    if "index" in choice and (type(choice["index"]) is not int or choice["index"]!=0):return False
    if choice.get("finish_reason") is not None and (not isinstance(choice["finish_reason"],str) or choice["finish_reason"] not in {"stop","length","tool_calls","function_call","content_filter"}):return False
    message=choice.get("message")
    if not isinstance(message,dict) or ("role" in message and message["role"]!="assistant"):return False
    if "content" in message and message["content"] is not None and not isinstance(message["content"],str):return False
    calls=message.get("tool_calls")
    if calls is not None and not (isinstance(calls,list) and all(isinstance(c,dict) and c.get("type")=="function"
        and isinstance(c.get("id"),str) and isinstance(c.get("function"),dict)
        and isinstance(c["function"].get("name"),str) and isinstance(c["function"].get("arguments"),str) for c in calls)):
        return False
    return "content" in message or bool(calls)



class OpenAIProviderClient:
    def __init__(self, http_client: Optional[httpx.AsyncClient]=None):
        self._external_client=http_client

    def _build_headers(self,manifest,credential=None):
        import os
        headers={"Content-Type":"application/json","Accept":"application/json","User-Agent":"open-freebie-finder/0.1.0"}
        if manifest.auth.type!="none" and manifest.auth.api_key_env:
            key=credential or os.getenv(manifest.auth.api_key_env) or getattr(get_settings(),manifest.auth.api_key_env.lower(),None)
            if key:
                name="Authorization" if manifest.auth.type=="bearer" else manifest.auth.custom_header_name
                if name:headers[name]=f"Bearer {key}" if manifest.auth.type=="bearer" else key
        return headers

    def _get_completions_url(self,manifest):
        base=manifest.base_url.rstrip("/")
        return base if base.endswith("/chat/completions") else base+"/chat/completions"

    @staticmethod
    def _error(status,manifest,model_id,data=None,guard=None,handle=None,retry_after=None,actual_status=None):
        from backend.app.core.balancer.resilience import retry_hint
        synthetic = actual_status == 200 and error_code(data,None) is None
        reason=None if synthetic else classify_billing(manifest.id,status,data)
        if reason and guard and handle:guard.hold(handle.scope,reason,retry_after=retry_after)
        if status==429:
            exc=UpstreamRateLimitError("Upstream rate limit exceeded.",manifest.id,model_id,retry=retry_hint(retry_after))
        else:
            exc=UpstreamProviderError(f"Upstream HTTP status {status}.",status,manifest.id,model_id,reason,
                                      failure_kind="protocol" if synthetic else "http",retry=retry_hint(retry_after))
        exc.actual_http_status=status if actual_status is None else actual_status
        return exc

    async def _error_body(self,response,handle,deadline,diagnostics=None):
        # Headers already establish HTTP failure. A broken/untrusted diagnostic
        # body cannot erase401/429 or its server retry bound.
        try:
            return await self._body(response,handle,deadline,diagnostics)
        except (httpx.RequestError,httpx.InvalidURL,ValueError,TypeError,TimeoutError,RecursionError):
            return None

    async def _io(self,awaitable,handle,deadline):
        async with asyncio.timeout(max(.001,deadline-time.monotonic())):
            return await handle.wait_io(awaitable) if handle else await awaitable

    async def _body(self,response,handle,deadline,diagnostics=None):
        body=bytearray()
        chunks=response.aiter_bytes()
        while True:
            try:chunk=await self._io(chunks.__anext__(),handle,deadline)
            except StopAsyncIteration:break
            if len(body)+len(chunk)>MAX_RESPONSE_BYTES:raise ValueError
            body.extend(chunk)
        try:
            data = json.loads(body)
            if diagnostics is not None:
                from backend.app.core.eligibility.protocol import safe_probe_diagnostics
                diagnostics.update(safe_probe_diagnostics(data))
            return data
        except (ValueError,RecursionError):
            if diagnostics is not None:
                from backend.app.core.eligibility.protocol import safe_probe_diagnostics
                diagnostics.update(safe_probe_diagnostics(None, non_json_body=body))
            return None

    async def qualify(self, permit, payload):
        """Use the owned I/O/auth/guard path with stricter raw probe framing."""
        from backend.app.core.eligibility.protocol import ProbeOutcome, ProbeProtocol
        from backend.app.core.eligibility.request import validate_request
        validate_request(payload)
        expected = {"model": permit.candidate.model_id, "messages": [{"role": "user", "content": "1+1=?"}],
                    "max_tokens": 32, "stream": permit.mode}
        if payload != expected:
            return ProbeOutcome(code="permit_unavailable")
        manifest = permit.manifest
        registry = permit.worker.registry
        guard = registry.billing
        if not permit.authorize():
            return ProbeOutcome(code="permit_unavailable")
        handle = guard.begin(permit.candidate.scope)
        if handle is None:
            return ProbeOutcome(code="held")
        client = self._external_client or httpx.AsyncClient(trust_env=False, follow_redirects=False)
        response = None
        protocol = ProbeProtocol()
        diagnostics = {}
        status = None
        sent = False
        cost = "unavailable"
        success = False
        try:
            deadline = min(permit.deadline, time.monotonic() + 15)
            with private_http():
                headers = self._build_headers(manifest, registry.credential(manifest))
                if permit.mode: headers["Accept"] = "text/event-stream"
                request = client.build_request("POST", self._get_completions_url(manifest),
                    json=payload, headers=headers, timeout=15)
                sent = True
                response = await self._io(client.send(request, stream=True, follow_redirects=False), handle, deadline)
                status = response.status_code
                if status != 200 or not permit.mode:
                    data = await (self._error_body(response,handle,deadline,diagnostics) if status != 200 else self._body(response,handle,deadline,diagnostics))
                    cost = guard.inspect_cost(handle, manifest.eligibility_profile, data)
                    if status != 200 or (isinstance(data, dict) and "error" in data):
                        effective = status if status != 200 else error_code(data)
                        failure=self._error(effective, manifest, permit.candidate.model_id, data, guard, handle, response.headers.get("Retry-After"),actual_status=response.status_code)
                        from backend.app.core.balancer.resilience import retry_hint
                        failure.retry_hint=retry_hint(response.headers.get_list("Retry-After"))
                        permit.health.error(failure)
                        return ProbeOutcome(status=effective, code="upstream_http_error", cost_status=cost,
                                            retry_after=response.headers.get("Retry-After"), diagnostics=diagnostics)
                    protocol.buffered(data)
                else:
                    size = 0
                    pending = b""
                    chunks = response.aiter_bytes()
                    while True:
                        try:
                            part = await self._io(chunks.__anext__(), handle, deadline)
                        except StopAsyncIteration:
                            break
                        size += len(part)
                        if size > MAX_RESPONSE_BYTES:
                            raise ValueError
                        pending += part
                        while b"\n" in pending:
                            line, pending = pending.split(b"\n", 1)
                            line = line.decode("utf-8").strip()
                            if line.startswith("data:"):
                                data = protocol.event(line[5:].strip())
                                if isinstance(data, dict):
                                    observed = guard.inspect_cost(handle, manifest.eligibility_profile, data)
                                    if observed != "unavailable": cost = observed
                                    if "error" in data:
                                        status = error_code(data)
                                        failure=self._error(status,manifest,permit.candidate.model_id,data,guard,handle,actual_status=200)
                                        permit.health.error(failure)
                                        return ProbeOutcome(status=status,code="upstream_http_error",cost_status=cost,diagnostics=diagnostics)
                                if handle.interrupted.is_set():
                                    raise BillingInterrupted(handle.reason)
                    if pending.strip():
                        protocol.invalid = True
            success = protocol.passed and guard.available(handle.scope) and not handle.interrupted.is_set()
            return ProbeOutcome(success, status, "available" if success else "probe_inconclusive", protocol.tokens, cost, diagnostics=diagnostics)
        except (httpx.RequestError, httpx.InvalidURL, ValueError, TypeError, TimeoutError, BillingInterrupted, RecursionError) as exc:
            kind = "neutral" if not sent or isinstance(exc,(BillingInterrupted,httpx.UnsupportedProtocol,httpx.InvalidURL)) else "timeout" if isinstance(exc,(TimeoutError,httpx.TimeoutException)) else "transport" if isinstance(exc,httpx.RequestError) else "protocol"
            permit.health.kind=kind
            permit.health.actual_http_status=response.status_code if response is not None else None
            return ProbeOutcome(status=status, cost_status=cost, diagnostics=diagnostics)
        finally:
            with anyio.CancelScope(shield=True), private_http():
                if response is not None: await response.aclose()
                if self._external_client is None: await client.aclose()
                guard.finish(handle, success)

    async def complete(self,manifest,raw_model_id,canonical_model,payload,timeout=15.0,
                       guard=None,handle=None,profile=None,credential=None,health=None):
        client=self._external_client or httpx.AsyncClient(trust_env=False,follow_redirects=False)
        response=None
        from backend.app.core.balancer.resilience import HealthOutcome, retry_hint
        health = health if health is not None else HealthOutcome()
        sent=False
        deadline=time.monotonic()+timeout
        try:
            with private_http():
                request=client.build_request("POST",self._get_completions_url(manifest),json={**payload,"model":raw_model_id,"stream":False},
                    headers=self._build_headers(manifest,credential),timeout=timeout)
                sent=True
                response=await self._io(client.send(request,stream=True,follow_redirects=False),handle,deadline)
                data=await (self._error_body(response,handle,deadline) if response.status_code!=200 else self._body(response,handle,deadline))
            if response.status_code!=200 or (isinstance(data,dict) and "error" in data):
                status=response.status_code if response.status_code!=200 else error_code(data)
                if guard and handle:guard.inspect_cost(handle,profile,data)
                exc=self._error(status,manifest,raw_model_id,data,guard,handle,response.headers.get("Retry-After"),actual_status=response.status_code)
                exc.retry_hint=retry_hint(response.headers.get_list("Retry-After"))
                raise exc
            valid = valid_completion(data)
            if handle:handle.complete=valid
            if guard and handle:guard.inspect_cost(handle,profile,data)
            if not valid:raise ValueError
            data["model"]=canonical_model
            if not data.get("usage"):data["usage"]={"prompt_tokens":0,"completion_tokens":0,"total_tokens":0}
            health.kind="success"
            return data
        except BillingInterrupted as exc:
            raise UpstreamProviderError("Upstream billing guard stopped this response.",503,manifest.id,raw_model_id,exc.code) from None
        except (httpx.RequestError,httpx.InvalidURL,ValueError,TimeoutError,TypeError,RecursionError) as exc:
            kind = "neutral" if not sent or isinstance(exc,(httpx.UnsupportedProtocol,httpx.InvalidURL)) else "timeout" if isinstance(exc,(TimeoutError,httpx.TimeoutException)) else "transport" if isinstance(exc,httpx.RequestError) else "protocol"
            raise UpstreamProviderError("Invalid or unavailable upstream completion.",502,manifest.id,raw_model_id,failure_kind=kind) from None
        finally:
            with anyio.CancelScope(shield=True), private_http():
                if response is not None:await response.aclose()
                if self._external_client is None:await client.aclose()

    async def stream_complete(self,manifest,raw_model_id,canonical_model,payload,timeout=15.0,
                              guard=None,handle=None,profile=None,credential=None,health=None)->AsyncGenerator[str,None]:
        client=self._external_client or httpx.AsyncClient(trust_env=False,follow_redirects=False)
        response=None
        from backend.app.core.balancer.resilience import HealthOutcome, retry_hint
        health = health if health is not None else HealthOutcome()
        sent=False
        started=complete=False
        deadline=time.monotonic()+timeout
        try:
            headers=self._build_headers(manifest,credential)
            headers["Accept"]="text/event-stream"
            with private_http():
                req=client.build_request("POST",self._get_completions_url(manifest),json={**payload,"model":raw_model_id,"stream":True},headers=headers,timeout=timeout)
                sent=True
                response=await self._io(client.send(req,stream=True,follow_redirects=False),handle,deadline)
            if response.status_code!=200:
                with private_http():data=await self._error_body(response,handle,deadline)
                exc=self._error(response.status_code,manifest,raw_model_id,data,guard,handle,response.headers.get("Retry-After"),actual_status=response.status_code)
                exc.retry_hint=retry_hint(response.headers.get_list("Retry-After"))
                raise exc
            # Bound individual SSE lines/initial role-only prebuffer; parse without
            # permitting an unlimited line inside httpx's aiter_lines buffer.
            chunks=response.aiter_bytes()
            pending=b""
            buffered=[]
            buffered_bytes=0
            async def lines():
                nonlocal pending
                while True:
                    while b"\n" in pending:
                        line,pending=pending.split(b"\n",1)
                        yield line.decode("utf-8").strip()
                    try:
                        with private_http():part=await self._io(chunks.__anext__(),handle,deadline)
                    except StopAsyncIteration:
                        if pending:yield pending.decode("utf-8").strip()
                        return
                    pending+=part
                    if len(pending)>MAX_RESPONSE_BYTES:raise ValueError
            async for line in lines():
                if not line.startswith("data:"):continue
                value=line[5:].strip()
                if value=="[DONE]":
                    if not (started or complete):raise ValueError
                    complete=True
                    if handle:handle.complete=True
                    if buffered:yield "".join(buffered)
                    health.kind="success"
                    yield "data: [DONE]\n\n"
                    return
                chunk=json.loads(value)
                if not isinstance(chunk,dict):raise ValueError
                if "error" in chunk:
                    if guard and handle:guard.inspect_cost(handle,profile,chunk)
                    if handle and handle.interrupted.is_set() and not complete:raise BillingInterrupted(handle.reason)
                    raise self._error(error_code(chunk),manifest,raw_model_id,chunk,guard,handle,actual_status=200)
                valid = True
                terminal = False
                delta = {}
                try:
                    choices=chunk.get("choices",[])
                    if not isinstance(choices,list) or len(choices)>1:raise ValueError
                    if choices:
                        choice=choices[0]
                        if not isinstance(choice,dict):raise ValueError
                        if "index" in choice and (type(choice["index"]) is not int or choice["index"]!=0):raise ValueError
                        delta=choice.get("delta",{})
                        if not isinstance(delta,dict):raise ValueError
                        if "content" in delta and delta["content"] is not None and not isinstance(delta["content"],str):raise ValueError
                        if delta.get("tool_calls") is not None and not isinstance(delta["tool_calls"],list):raise ValueError
                        finish=choice.get("finish_reason")
                        if finish is not None:
                            if not isinstance(finish,str) or finish not in {"stop","length","tool_calls","function_call","content_filter"}:raise ValueError
                            terminal=True
                except (ValueError,TypeError):
                    valid=False
                if valid and terminal:
                    complete=True
                    if handle:handle.complete=True
                # Monetary inspection is independent of generation validity.
                if guard and handle:guard.inspect_cost(handle,profile,chunk)
                if handle and handle.interrupted.is_set() and not complete:raise BillingInterrupted(handle.reason)
                if not valid:raise ValueError
                chunk["model"]=canonical_model
                encoded=f"data: {json.dumps(chunk)}\n\n"
                if started or complete:
                    if buffered:
                        encoded="".join(buffered)+encoded
                        buffered.clear()
                    if semantic(delta):started=True
                    yield encoded
                else:
                    buffered.append(encoded)
                    buffered_bytes+=len(encoded)
                    if buffered_bytes>MAX_RESPONSE_BYTES:raise ValueError
                    if semantic(delta):
                        started=True
                        yield "".join(buffered)
                        buffered.clear()
            if not complete:raise ValueError
            health.kind="success"
            yield "data: [DONE]\n\n"
        except BillingInterrupted as exc:
            raise UpstreamProviderError("Upstream billing guard stopped this response.",503,manifest.id,raw_model_id,exc.code) from None
        except (httpx.RequestError,httpx.InvalidURL,ValueError,TimeoutError,TypeError,RecursionError) as exc:
            kind = "neutral" if not sent or isinstance(exc,(httpx.UnsupportedProtocol,httpx.InvalidURL)) else "timeout" if isinstance(exc,(TimeoutError,httpx.TimeoutException)) else "transport" if isinstance(exc,httpx.RequestError) else "protocol"
            failure=UpstreamProviderError("Invalid or unavailable upstream stream.",502,manifest.id,raw_model_id,failure_kind=kind)
            failure.actual_http_status=response.status_code if response is not None else None
            if complete:
                # Preserve the completed answer independently of future health.
                health.error(failure)
                yield "data: [DONE]\n\n"
                return
            raise failure from None
        finally:
            with anyio.CancelScope(shield=True), private_http():
                if response is not None:await response.aclose()
                if self._external_client is None:await client.aclose()
