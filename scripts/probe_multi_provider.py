"""Reproducible T-007 catalog and real-loopback proxy checks; prints metadata only."""
import argparse
import asyncio
import json
from pathlib import Path
import socket
import sys
import threading
import time
from contextlib import contextmanager, asynccontextmanager

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import uvicorn

from backend.app.config import get_settings
from backend.app.core.discovery.orchestrator import DiscoveryOrchestrator
from backend.app.core.discovery.privacy import private_http
from backend.app.core.providers.registry import ProviderRegistry
from backend.app.core.telemetry.store import get_telemetry_store
from backend.app.core.balancer.router import CascadeRouter
from backend.app.core.adapters.openai_client import OpenAIProviderClient, valid_completion
from backend.app.core.eligibility.evidence import decimal
from backend.app.main import create_app


@contextmanager
def serve(app):
    sock = socket.socket()
    server = None
    thread = None
    try:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_config=None, access_log=False, log_level="critical"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        deadline = time.monotonic() + 5
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        if not server.started:
            raise RuntimeError("Probe server failed to start.")
        yield f"http://127.0.0.1:{port}"
    finally:
        if server:
            server.should_exit = True
        if thread:
            thread.join(timeout=5)
            if thread.is_alive():
                raise RuntimeError("Probe server failed to stop.")
        sock.close()


def emit(**metadata):
    print(json.dumps(metadata, allow_nan=False))


def has_answer(value):
    """Live proof requires visible text/tool output; reasoning alone is not an answer."""
    if not isinstance(value,dict):
        return False
    content=value.get("content")
    return bool((isinstance(content,str) and content.strip()) or
                (isinstance(value.get("tool_calls"),list) and value["tool_calls"]))


def safe_attempts(trace):
    """Keep enough failure evidence without upstream text or secret-bearing IDs."""
    if trace is None:
        return []
    return [{"status":attempt.status if attempt.status in {"success","http_error","stream_error","cooldown_skipped"} else "unknown",
             "http_status":attempt.status_code if type(attempt.status_code) is int else None}
            for attempt in trace.attempts]


def safe_upstream_diagnostic(status, payload):
    """Classify untrusted errors for operator diagnosis, never for admission."""
    error=payload.get("error") if isinstance(payload,dict) else None
    message=error.get("message") if isinstance(error,dict) else None
    text=message.lower() if isinstance(message,str) else ""
    # Provider messages may contain a JSON-encoded validation array or a nested
    # metadata.raw error. Decode only within the existing bounded observation;
    # emit fixed field/type/code vocabulary, never arbitrary provider strings.
    fields={"provider","max_price","prompt","completion","request","image","require_parameters",
            "max_tokens","max_completion_tokens","messages","role","content","model","stream"}
    types={"string","number","integer","boolean","object","array","null","undefined"}
    codes={"invalid_type","invalid_value","too_small","too_big","unrecognized_keys","invalid_union","custom"}
    validations=[]
    fragments=[]
    pending=[payload]
    visited=0
    while pending and visited<100:
        node=pending.pop();visited+=1
        if isinstance(node,str):
            fragments.append(node.lower())
            try:
                decoded=json.loads(node)
                if isinstance(decoded,(dict,list)):pending.append(decoded)
            except (ValueError,RecursionError):pass
        elif isinstance(node,list):pending.extend(node[:100])
        elif isinstance(node,dict):
            path=node.get("path",node.get("loc"))
            if isinstance(path,list) and path and all((isinstance(v,str) and v in fields) or (type(v) is int and 0<=v<=100) for v in path):
                item={"path":[v for v in path if isinstance(v,str)]}
                if isinstance(node.get("code"),str) and node["code"] in codes:item["code"]=node["code"]
                if isinstance(node.get("expected"),str) and node["expected"] in types:item["expected"]=node["expected"]
                if isinstance(node.get("received"),str) and node["received"] in types:item["received"]=node["received"]
                validations.append(item)
            for key in ("message","raw","error","errors","details","metadata"):
                if key in node:pending.append(node[key])
    text=" ".join(fragments)
    references=sorted(field for field in fields if field in text)
    code=error.get("code") if isinstance(error,dict) else None
    effective=code if type(code) is int and 400<=code<=599 else status
    reason=None
    if effective==401:reason="authentication_rejected"
    elif effective==402:reason="billing_or_credit_limit"
    elif effective==429:reason="rate_limited"
    elif effective==404 and "no endpoints found" in text:
        if "data policy" in text:reason="data_policy_mismatch"
        elif "parameters" in text:reason="unsupported_parameters"
        elif "price" in text:reason="price_ceiling_no_route"
        else:reason="no_matching_endpoints"
    elif effective==400 and "provider returned error" in text and "request contains an invalid argument" in text:reason="provider_invalid_argument"
    elif effective==400 and validations:reason="request_schema_validation_failed"
    elif effective==400 and ("max_tokens" in text or "max_completion_tokens" in text):reason="token_limit_rejected"
    elif effective>=500:reason="upstream_service_error"
    elif effective>=400:reason="upstream_request_rejected"
    return {"http_status":status,"error_status":code if type(code) is int and 400<=code<=599 else None,"reason":reason,"field_references":references,"validation":validations}


class _DiagnosticStream(httpx.AsyncByteStream):
    """Observe a bounded identity-encoded response without changing adapter reads."""
    def __init__(self, upstream, status, output):
        self.upstream=upstream
        self.status=status
        self.output=output
        self.prefix=bytearray()
        self.truncated=False
        self.finished=False

    async def __aiter__(self):
        try:
            async for chunk in self.upstream:
                remaining=65536-len(self.prefix)
                self.prefix.extend(chunk[:remaining])
                self.truncated=self.truncated or len(chunk)>remaining
                yield chunk
        finally:
            self._finish()

    def _finish(self):
        if self.finished:return
        self.finished=True
        payload=None
        try:
            if not self.truncated:
                try:payload=json.loads(self.prefix)
                except ValueError:
                    for line in self.prefix.decode("utf-8").splitlines():
                        if line.startswith("data:") and line[5:].strip()!="[DONE]":
                            value=json.loads(line[5:].strip())
                            if isinstance(value,dict) and "error" in value:
                                payload=value
                                break
        except (ValueError,TypeError,RecursionError):pass
        self.output.append(safe_upstream_diagnostic(self.status,payload))
        self.prefix.clear()

    async def aclose(self):
        try:await self.upstream.aclose()
        finally:self._finish()


async def probe(args):
    settings = get_settings()
    original = ProviderRegistry(settings=settings)
    manifest = original.get_manifest(args.provider_id)
    if manifest is None:
        emit(outcome="failed", code="unknown_provider")
        return 1
    skip = original.profile_skip(manifest)
    if skip:
        emit(outcome="SKIPPED" if skip in {"excluded", "retired", "unsupported_profile"} else "UNVERIFIED", code=skip)
        return 0 if skip in {"excluded", "retired", "unsupported_profile"} else 1
    manifest = manifest.model_copy(deep=True)
    attempt_budget = getattr(args,"max_attempts",1)
    if type(attempt_budget) is not int or not 1 <= attempt_budget <= settings.max_failover_attempts:
        emit(outcome="failed",code="invalid_attempt_budget")
        return 1
    isolated_settings = settings.model_copy(update={"routing_provider_priority": [manifest.id], "max_failover_attempts":attempt_budget, "free_account_confirmations":[]})
    registry = ProviderRegistry(settings=isolated_settings, manifests=[manifest])
    start = time.monotonic()
    if args.mode in {"catalog", "evidence"}:
        discovery = DiscoveryOrchestrator(registry)
        await discovery.run_cycle()
        status = discovery.statuses[manifest.id]
        eligible = registry.get_eligible_models()
        evidence = registry.eligibility.diagnostics(manifest)
        source_records = [r for (p, _), r in registry.eligibility.records.items() if p == manifest.id]
        metadata = dict(catalog_outcome=status.outcome, code=status.code, catalog_count=status.catalog_count,
            admitted_count=len(eligible), duration_ms=round((time.monotonic()-start)*1000,2),
            eligibility=evidence, billing=registry.billing.diagnostics(registry.eligibility.scope(manifest)),
            source_ids=sorted({r.source_id for r in source_records}),
            bases=sorted({r.verdict.basis for r in source_records}),
            source_age_seconds=max((round(time.monotonic()-r.observed_at,3) for r in source_records),default=None),
            observed_at=min((r.observed_utc for r in source_records),default=None),
            expires_in_seconds=min((max(0,round(r.expires_at-time.monotonic(),3)) for r in source_records),default=None))
        if args.mode == "evidence":
            verified=status.outcome == "succeeded" and bool(eligible)
            emit(outcome="verified" if verified else "UNVERIFIED", **metadata)
            return 0 if verified else 1
        emit(outcome=status.outcome, **metadata)
        return 0 if status.outcome == "succeeded" else 1
    app = create_app(provider_registry=registry)
    # Observe the actual dispatch on a real HTTP transport, never a fake response.
    # The observer validates constraints before transport and retains metadata only.
    wire = []
    wire_ids = []  # Private transient identity correlation; never included in output.
    upstream_statuses = []
    upstream_diagnostics = []
    async def observe(request):
        body=json.loads(request.content)
        caps_valid=(body.get("provider")=={"max_price":{"prompt":"0","completion":"0","request":"0","image":"0"},"require_parameters":True})
        if registry.dispatch_profile(manifest)=="openrouter_zero_price" and not caps_valid:
            raise RuntimeError("Probe rejected missing zero-price constraints.")
        if body.get("max_tokens")!=32 or len(wire)>=2*attempt_budget:
            raise RuntimeError("Probe generation bound exceeded.")
        eligible_ids={m.id for m in registry.get_eligible_models() if m.provider_id==manifest.id}
        wire_ids.append(body.get("model"))
        wire.append({"stream":body.get("stream") is True,"max_tokens":32,"zero_caps_verified":caps_valid,
            "model_matches":body.get("model") in eligible_ids})
    async def observe_response(response):
        upstream_statuses.append(response.status_code)
        if response.headers.get("content-encoding", "identity").lower()=="identity":
            response.stream=_DiagnosticStream(response.stream,response.status_code,upstream_diagnostics)
    original_lifespan=app.router.lifespan_context
    @asynccontextmanager
    async def observed_lifespan(application):
        async with httpx.AsyncClient(trust_env=False,follow_redirects=False,headers={"Accept-Encoding":"identity"},event_hooks={"request":[observe],"response":[observe_response]}) as outbound:
            application.state.cascade_router=CascadeRouter(registry,OpenAIProviderClient(outbound))
            async with original_lifespan(application):
                yield
    app.router.lifespan_context=observed_lifespan
    headers = {"Authorization": f"Bearer {settings.proxy_master_key}"} if settings.proxy_master_key else {}
    with serve(app) as base_url:
        # The normal lifespan worker owns discovery; no fake transport or replacement
        # router is used in proxy mode.
        async with asyncio.timeout(20):
            while not getattr(app.state, "discovery", None) or manifest.id not in app.state.discovery.statuses:
                await asyncio.sleep(0.02)
        status = app.state.discovery.statuses[manifest.id]
        if status.outcome != "succeeded" or not registry.get_eligible_models():
            emit(outcome="UNVERIFIED", code=status.code or "no_eligible_models", catalog_count=status.catalog_count)
            return 1
        available=sorted(registry.get_eligible_models(), key=lambda m:(
            "max_tokens" not in m.metadata.get("supported_parameters",[]),
            "reasoning" in m.metadata.get("supported_parameters",[]), m.id))
        matching = [m for m in available if not args.model_id or m.id == args.model_id]
        index = getattr(args,"candidate_index",0)
        selected = matching[index] if 0 <= index < len(matching) else None
        if selected is None:
            emit(outcome="UNVERIFIED", code="model_not_eligible")
            return 1
        requested_model = "auto:free" if getattr(args,"auto",False) else selected.canonical_name
        payload = {"model": requested_model, "messages":[{"role":"user","content":"1+1=?"}], "max_tokens":32}
        results = []
        async with httpx.AsyncClient(base_url=base_url, trust_env=False, timeout=45) as client:
            modes={"both":(False,True),"buffered":(False,),"sse":(True,)}[getattr(args,"generation","both")]
            for streaming in modes:
                correlation = "t007-live-stream" if streaming else "t007-live-buffered"
                with private_http():
                    response = await client.post("/v1/chat/completions", json={**payload,"stream":streaming},
                                                 headers={**headers,"X-Request-ID":correlation})
                passed = response.status_code == 200 and response.headers.get("X-Request-ID") == correlation
                monetary = "unavailable"
                semantic_output = False
                protocol_valid = False
                answer_shape = None
                chunks = []
                try:
                    if passed and not streaming:
                        body=response.json()
                        protocol_valid=valid_completion(body) and body.get("model")==requested_model
                        semantic_output=bool(protocol_valid and has_answer(body["choices"][0]["message"]))
                        chunks=[body]
                        if protocol_valid:
                            choice=body["choices"][0];message=choice["message"]
                            finish=choice.get("finish_reason")
                            usage=body.get("usage",{})
                            answer_shape={"content_chars":len(message.get("content") or ""),
                                "reasoning_present":any(message.get(k) for k in ("reasoning","reasoning_content","reasoning_details")),
                                "finish_reason":finish if finish in {"stop","length","tool_calls","content_filter",None} else "other",
                                "completion_tokens":usage.get("completion_tokens") if type(usage.get("completion_tokens")) is int else None}
                    elif passed:
                        done=0
                        valid=True
                        terminal=False
                        for line in response.text.splitlines():
                            if not line.startswith("data:"):continue
                            value=line[5:].strip()
                            if value=="[DONE]":
                                done+=1
                                continue
                            body=json.loads(value)
                            valid=valid and isinstance(body,dict) and "error" not in body and body.get("model")==requested_model
                            choices=body.get("choices",[])
                            if choices:
                                delta=choices[0].get("delta",{})
                                semantic_output=semantic_output or has_answer(delta)
                                terminal=terminal or choices[0].get("finish_reason") is not None
                            chunks.append(body)
                        protocol_valid=bool(valid and done==1 and (semantic_output or terminal))
                    for body in chunks:
                        usage=body.get("usage")
                        if isinstance(usage,dict) and usage.get("cost") is not None:
                            try:monetary="positive" if decimal(usage["cost"])>0 else "zero"
                            except ValueError:monetary="invalid"
                            if monetary in {"positive","invalid"}:break
                except (ValueError,TypeError,AttributeError,KeyError,IndexError):
                    protocol_valid=False
                traces=await get_telemetry_store().get_recent(10)
                trace=next((item for item in traces if item.request_id==correlation),None)
                hold=registry.billing.diagnostics(registry.eligibility.scope(manifest))
                resolved=next((m for m in registry.get_eligible_models() if trace and trace.attempts and m.provider_id==manifest.id and m.id==trace.attempts[-1].model_id),None)
                record=registry.eligibility.get(manifest,resolved.id) if resolved else None
                wire_for_request=[item for item in wire if item["stream"]==streaming]
                attempts=trace.attempts if trace else []
                sent_ids=[wire_ids[i] for i,item in enumerate(wire) if item["stream"]==streaming]
                passed=bool(passed and protocol_valid and semantic_output and trace is not None and trace.success
                    and 1<=len(attempts)<=attempt_budget and all(a.provider_id==manifest.id for a in attempts)
                    and sent_ids==[a.model_id for a in attempts]
                    and record and record.verdict.state=="free" and resolved and registry.admits(manifest,resolved)
                    and hold["kind"] is None and monetary not in {"positive","invalid"}
                    and len(wire_for_request)==len(attempts) and all(item["model_matches"] for item in wire_for_request))
                results.append({"stream":streaming,"http_status":response.status_code,"passed":passed,
                    "protocol_valid":protocol_valid,"semantic_output":bool(semantic_output),"answer_shape":answer_shape,"cost_reporting":monetary,
                    "attempt_count":len(trace.attempts) if trace else None,"attempts":safe_attempts(trace),
                    "basis":record.verdict.basis if record else None,"reason":record.verdict.reason if record else None,
                    "billing":hold,"wire":wire_for_request})
                if not passed:
                    break  # Never retry a failed/charged micro-generation or proceed to SSE.
        success = len(results)==len(modes) and all(result["passed"] for result in results)
        emit(outcome="passed" if success else "failed", catalog_count=status.catalog_count,
             admitted_count=status.admitted_count, candidate_index=index, attempt_budget=attempt_budget, auto=getattr(args,"auto",False), results=results, generation_modes=["sse" if v else "buffered" for v in modes],
             duration_ms=round((time.monotonic()-start)*1000,2),
             eligibility=registry.eligibility.diagnostics(manifest),upstream_http_statuses=upstream_statuses,upstream_diagnostics=upstream_diagnostics)
        return 0 if success else 1


async def account_probe(args):
    """Explicit isolated H4 packet: no primary configuration or ambient worker."""
    import hashlib
    from backend.app.core.eligibility.account import PROFILES
    from backend.app.core.eligibility.probes import ProbeWorker
    from backend.app.core.eligibility.protocol import ProbeProtocol
    from backend.app.core.adapters.openai_client import UpstreamProviderError
    if args.provider_id not in PROFILES or not args.confirm_nonbillable_account:
        emit(outcome="UNVERIFIED", code="explicit_nonbillable_assertion_required")
        return 1
    offset=getattr(args,"candidate_offset",0)
    limit=getattr(args,"candidate_limit",3)
    send_limit=getattr(args,"send_limit",8)
    if type(offset) is not int or not 0<=offset<1000 or type(limit) is not int or not 1<=limit<=3 or type(send_limit) is not int or not 1<=send_limit<=8:
        emit(outcome="UNVERIFIED",code="invalid_packet_bounds")
        return 1
    settings=get_settings()
    original=ProviderRegistry(settings=settings)
    manifest=original.get_manifest(args.provider_id)
    if not manifest or original.profile_skip(manifest):
        emit(outcome="UNVERIFIED", code="credential_or_profile_unavailable")
        return 1
    isolated=settings.model_copy(update={"free_account_confirmations":[manifest.id],
        "routing_provider_priority":[manifest.id], "max_failover_attempts":1})
    registry=ProviderRegistry(settings=isolated, manifests=[manifest.model_copy(deep=True)])
    manifest=registry.get_manifest(manifest.id)
    wire=[]
    state={"done":False,"qualified":False,"phase":"qualification","code":"pending"}
    history=[]
    async def observe(request):
        if request.method!="POST":return
        body=json.loads(request.content)
        if body.get("max_tokens")!=32 or len(wire)>=send_limit:
            raise UpstreamProviderError("Isolated probe budget exhausted.",503,manifest.id,"redacted")
        if request.url.host!=httpx.URL(manifest.base_url).host or request.url.path!=httpx.URL(manifest.base_url).path.rstrip('/')+'/chat/completions':
            raise UpstreamProviderError("Isolated probe route rejected.",503,manifest.id,"redacted")
        fingerprint=hashlib.sha256(body['model'].encode()).hexdigest()[:16]
        wire.append({"phase":state["phase"],"stream":body.get('stream') is True,"max_tokens":32,
            "route_fingerprint":fingerprint,"auth_bound":request.headers.get('authorization')=='Bearer '+registry.credential(manifest)})
    @asynccontextmanager
    async def isolated_lifespan(app):
        async with httpx.AsyncClient(trust_env=False,follow_redirects=False,event_hooks={"request":[observe]}) as outbound:
            discovery=DiscoveryOrchestrator(registry,outbound)
            worker=ProbeWorker(registry,OpenAIProviderClient(outbound))
            app.state.discovery=discovery
            app.state.cascade_router=CascadeRouter(registry,OpenAIProviderClient(outbound),max_attempts=1)
            async def qualify():
                try:
                    await discovery.discover_provider(manifest)
                    candidates=[c for (p,_),c in registry.accounts.candidates.items() if p==manifest.id]
                    emit(stage="account_catalog",provider=manifest.id,candidates=len(candidates),
                        assurance="user_asserted",assertion_loaded_at=registry.accounts.loaded_at)
                    # Catalog order only: no saved model IDs or model-name heuristic.
                    for c in candidates[offset:offset+limit]:
                        while not worker.budget.can_reserve(manifest.id,'new'):
                            await asyncio.sleep(1)
                        if registry.accounts.suspended or not registry.billing.available(c.scope):
                            state['code']='held';break
                        await discovery.discover_provider(manifest)
                        current=registry.accounts.candidates.get((manifest.id,c.model_id))
                        if current is None:continue
                        if await worker.qualify(manifest,current):
                            state.update(qualified=True,canonical=registry.canonical_name(manifest,current.metadata.get('base_model_id',current.model_id)),code='available')
                            break
                        emit(stage="account_qualification",provider=manifest.id,requests=len(wire),
                            recent=list(worker.history)[-2:],admitted=len(registry.get_eligible_models()))
                    if not state['qualified'] and state['code']=='pending':state['code']='no_qualified_route_within_packet'
                except Exception:
                    state['code']='qualification_transport_or_configuration_failure'
                finally:
                    history.extend(worker.history)
                    state['done']=True
            task=asyncio.create_task(qualify())
            try:yield
            finally:
                task.cancel()
                await asyncio.gather(task,return_exceptions=True)
    app=create_app(provider_registry=registry)
    app.router.lifespan_context=isolated_lifespan
    results=[]
    headers={"Authorization":"Bearer "+settings.proxy_master_key} if settings.proxy_master_key else {}
    with serve(app) as base_url:
        async with httpx.AsyncClient(base_url=base_url,trust_env=False,timeout=35) as local:
            async with asyncio.timeout(240):
                while not state['done']:
                    await asyncio.sleep(.2)
            if state['qualified']:
                state['phase']='proxy'
                for streaming in (False,True):
                    correlation='t007-account-'+('sse' if streaming else 'buffered')
                    response=await local.post('/v1/chat/completions',json={"model":state['canonical'],
                        "messages":[{"role":"user","content":"1+1=?"}],"max_tokens":32,"stream":streaming},
                        headers={**headers,"X-Request-ID":correlation})
                    protocol=ProbeProtocol()
                    if response.status_code==200:
                        try:
                            if not streaming:protocol.buffered(response.json())
                            else:
                                for line in response.text.splitlines():
                                    if line.startswith('data:'):protocol.event(line[5:].strip())
                        except (ValueError,TypeError,KeyError):protocol.invalid=True
                    traces=await get_telemetry_store().get_recent(20)
                    trace=next((t for t in traces if t.request_id==correlation),None)
                    passed=bool(response.status_code==200 and protocol.passed and trace and trace.success
                        and len(trace.attempts)==1 and response.headers.get('X-Request-ID')==correlation)
                    results.append({"stream":streaming,"http_status":response.status_code,"passed":passed,
                        "visible_output":protocol.visible,"completion_tokens":protocol.tokens,
                        "done_count":protocol.done if streaming else None,"attempt_count":len(trace.attempts) if trace else None,
                        "cost_reporting":"unavailable","assurance":"user_asserted"})
                    if not passed:break
    success=len(results)==2 and all(r['passed'] for r in results)
    emit(outcome="PASS" if success else "UNVERIFIED",provider=manifest.id,
        code="conditional_account_delivery" if success else state['code'],
        assertion="operator_asserted_nonbillable",cost_reporting="unavailable",primary_activated=False,
        inference_sends=len(wire),candidate_offset=offset,candidate_limit=limit,send_limit=send_limit,qualification=history,results=results,wire=wire,
        eligibility=registry.eligibility.diagnostics(manifest),
        billing=registry.billing.diagnostics(registry.eligibility.scope(manifest)))
    return 0 if success else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider-id", required=True)
    parser.add_argument("--mode", choices=["catalog","evidence","proxy","account"], required=True)
    parser.add_argument("--generation", choices=["both","buffered","sse"], default="both", help="Select only the explicitly authorized probe modes; does not grant eligibility or extra attempts.")
    parser.add_argument("--max-attempts", type=int, default=1, help="Bound each mode by this many cascade attempts, at most the configured router limit; every hop stays at 32 tokens and zero ceilings.")
    parser.add_argument("--auto", action="store_true", help="Exercise normal auto:free routing instead of preferring a diagnostic candidate.")
    parser.add_argument("--candidate-index", type=int, default=0, help="Select an index in the current eligible set for diagnosis; never grants eligibility or retries.")
    parser.add_argument("--model-id", help="Optional selection among currently dynamically eligible raw IDs; cannot grant admission.")
    parser.add_argument("--confirm-nonbillable-account", action="store_true", help="Explicit operator assertion covering no paid overflow/PAYG/purchased balance/BYOK/bill_to. Account mode only; at most eight 32-token sends in this isolated process.")
    parser.add_argument("--candidate-offset",type=int,default=0,help="Account diagnostic start index in fresh catalog order; never a model allowlist.")
    parser.add_argument("--candidate-limit",type=int,default=3,help="Account packet explores 1..3 fresh catalog candidates.")
    parser.add_argument("--send-limit",type=int,default=8,help="Lower account packet ceiling, 1..8 sends; used to preserve an authorized remaining budget.")
    args=parser.parse_args()
    try:
        return asyncio.run(account_probe(args) if args.mode=="account" else probe(args))
    except Exception:
        emit(outcome="failed",code="probe_transport_or_configuration_error")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
