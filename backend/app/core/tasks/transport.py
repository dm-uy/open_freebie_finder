"""One exact task route, fully buffered; shared financial/auth/quota ownership."""
import asyncio
from contextlib import aclosing
from dataclasses import dataclass
import json
import logging

import anyio
import httpx

from backend.app.core.balancer.resilience import HealthOutcome, retry_hint
from backend.app.core.discovery.privacy import private_http
from backend.app.core.eligibility.billing import BillingInterrupted, classify_billing
from backend.app.core.tasks import catalog
from backend.app.core.tasks.http import safe_request_id
from backend.app.core.tasks.protocol import (RequestError, ProtocolError, parse_json, validate_request,
    validate_capabilities, validate_response, validate_audio)

logger = logging.getLogger(__name__)


class TaskError(Exception):
    def __init__(self, status=503, code="task_unavailable", request_id=None):
        self.status, self.code = status, code
        self.request_id = request_id
        super().__init__("Task request unavailable.")


@dataclass
class TaskResult:
    data: object
    media_type: str = "application/json"
    request_id: str = ""


def private_output(registry, value):
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str) and registry.is_private_identifier(item):
            return True
        if isinstance(item, bytes) and any(secret.encode("utf-8") in item for secret in registry.secrets()):
            return True
        if isinstance(item, dict):
            pending.extend(item.keys()); pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return False


class TaskExecutor:
    def __init__(self, registry, http_client=None, before_send=None):
        self.registry = registry
        self._external_client = http_client
        # Synchronous optional tooling budget hook; not a free-admission override.
        self.before_send = before_send

    def _preflight(self, task, payload):
        store = self.registry.tasks
        row = store.get(task, payload["model"])
        if row is None:
            mismatch = any(store.get(other, payload["model"]) for other in catalog.TASKS if other != task)
            raise TaskError(400 if mismatch else 404, "unsupported_free_request" if mismatch else "model_not_found")
        if not store.eligible(row):
            raise TaskError()
        validate_capabilities(task, payload, row.capabilities)
        return row

    async def execute(self, task, payload, rid):
        attempts, delivered, code = 0, False, "task_unavailable"
        handle = ticket = response = client = result = None
        health = HealthOutcome()
        target = None
        try:
            payload = validate_request(task, payload)
            if self.registry.is_private_identifier(payload["model"]):
                raise RequestError()
            target = payload["model"]
            manifest = self.registry.get_manifest("openrouter")
            if manifest is not None:
                # Consumer admission observes credential epochs. Pure catalog
                # reads cannot do this maintenance; restored keys need reproof.
                self.registry.eligibility.scope(manifest)
            row = self._preflight(task, payload)
            manifest = self.registry.get_manifest("openrouter")
            client = self._external_client or httpx.AsyncClient(trust_env=False, follow_redirects=False)
            body = {**payload, "model": row.raw_id}
            owned_policy = catalog.policy(task)
            if owned_policy is not None:
                body["provider"] = owned_policy
            key = self.registry.credential(manifest)
            request = httpx.Request("POST", "https://openrouter.ai" + catalog.DISPATCH_PATHS[task], json=body,
                headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                         "Accept": "audio/*" if task == "speech" else "application/json"},
                extensions={"timeout": httpx.Timeout(15).as_dict()})
            # Final synchronous admission: no await between recheck and owned I/O.
            if self._preflight(task, payload) is not row:
                raise TaskError()
            handle = self.registry.billing.begin(row.scope)
            if handle is None:
                raise TaskError()
            ticket = self.registry.resilience.acquire(manifest, ("task", task, row.raw_id))
            if ticket is None:
                raise TaskError()
            if self.before_send is not None:
                self.before_send(task, row)
            if (not self.registry.tasks.current(row) or handle.interrupted.is_set()
                    or not self.registry.billing.available(row.scope) and handle.recovery_hold is None):
                self.registry.resilience.rollback(ticket)
                raise TaskError()
            attempts = 1
            with private_http():
                async with asyncio.timeout(15):
                    response = await handle.wait_io(client.send(request, stream=True, auth=None, follow_redirects=False))
                    if response.status_code != 200:
                        health.kind, health.status = "http", response.status_code
                        health.actual_http_status = response.status_code
                        health.retry = retry_hint(response.headers.get_list("Retry-After"))
                    limit = 8 * 1024 * 1024 if response.status_code == 200 else 64 * 1024
                    body_bytes = bytearray()
                    iterator = response.aiter_bytes()
                    while True:
                        try:
                            part = await handle.wait_io(iterator.__anext__())
                        except StopAsyncIteration:
                            break
                        if len(body_bytes) + len(part) > limit:
                            raise ProtocolError()
                        body_bytes.extend(part)
            data = None
            if (response.status_code == 200 and task != "speech"
                    and response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json"):
                raise ProtocolError()
            if response.status_code != 200 or task != "speech":
                try:
                    data = parse_json(body_bytes)
                except RequestError:
                    if response.status_code == 200:
                        raise ProtocolError() from None
            if response.status_code != 200 or isinstance(data, dict) and "error" in data:
                effective = response.status_code
                if effective == 200:
                    error_data = data.get("error")
                    effective = error_data.get("code") if isinstance(error_data, dict) else None
                    if type(effective) is not int or not 400 <= effective <= 599:
                        raise ProtocolError()
                financial = classify_billing("openrouter", effective, data)
                if financial:
                    self.registry.billing.hold(row.scope, financial, retry_after=response.headers.get("Retry-After"))
                health.kind = "neutral" if financial else "http"
                health.status, health.actual_http_status = effective, response.status_code
                health.retry = retry_hint(response.headers.get_list("Retry-After"))
                raise TaskError()
            if any(secret.encode("utf-8") in body_bytes for secret in self.registry.secrets()):
                raise ProtocolError()
            if task == "speech":
                result = TaskResult(validate_audio(payload, bytes(body_bytes), response.headers.get("Content-Type", "")),
                    "audio/mpeg" if payload["response_format"] == "mp3" else "audio/pcm")
            else:
                result = TaskResult(validate_response(task, payload, data, row.raw_id))
            # Completion and financial incident are independent. A valid body
            # obtained concurrently with a latch must not be discarded.
            handle.complete = True
            delivered = True
            health.kind = "success"
            code = "delivered"
            return result
        except RequestError:
            code = "unsupported_free_request"
            raise TaskError(400, code) from None
        except ProtocolError:
            if health.kind != "http":
                health.kind = "protocol"
            code = "invalid_upstream_response"
            raise TaskError(502, code) from None
        except BillingInterrupted:
            code = "billing_unavailable"
            raise TaskError(503, code) from None
        except asyncio.CancelledError:
            code = "cancelled"
            raise
        except (httpx.RequestError, TimeoutError) as exc:
            if health.kind != "http":
                health.kind = "timeout" if isinstance(exc, (TimeoutError, httpx.TimeoutException)) else "transport"
            code = "upstream_unavailable"
            raise TaskError(503, code) from None
        except TaskError as exc:
            code = exc.code
            raise
        finally:
            with anyio.CancelScope(shield=True), private_http():
                try:
                    if response is not None:
                        try:
                            await response.aclose()
                        except Exception:
                            if health.kind != "http": health.kind = "transport"
                finally:
                    if client is not None and self._external_client is None:
                        try:
                            await client.aclose()
                        except Exception:
                            if health.kind != "http": health.kind = "transport"
                    if ticket is not None:
                        # A malformed/cancelled error body cannot erase the
                        # trustworthy status already received from the server.
                        if health.actual_http_status == 402 and not self.registry.billing.diagnostics(handle.scope).get("kind"):
                            self.registry.billing.hold(handle.scope, "billing_access_unverified")
                        financial = bool(handle and self.registry.billing.diagnostics(handle.scope).get("kind"))
                        self.registry.resilience.finish(ticket, health, financial=financial)
                    if handle is not None:
                        self.registry.billing.finish(handle, delivered)
                    # Re-evaluate current keys after every awaited cleanup too.
                    # The public model includes a prefix absent from raw bodies.
                    rejected = result is not None and private_output(self.registry, result.data)
                    if rejected:
                        delivered, code = False, "private_response_identifier"
                    rid = safe_request_id(rid, self.registry)
                    if result is not None:
                        result.request_id = rid
                    if target and self.registry.is_private_identifier(target):
                        target = None
                    logger.info(json.dumps({"event": "task_request", "task": task, "request_id": rid,
                        "target": target, "attempt_count": attempts, "delivery": "success" if delivered else "failed", "code": code}))
                    if rejected:
                        raise TaskError(503, code, rid)
