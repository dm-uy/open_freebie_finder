"""Two-Tier Cascade Failover Router with Circuit Breaker and Structured Telemetry."""
import anyio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional
from collections import defaultdict, deque
from backend.app.core.adapters.openai_client import (
    OpenAIProviderClient,
    UpstreamProviderError,
    UpstreamRateLimitError,
)
from backend.app.core.balancer.resilience import HealthOutcome
from backend.app.core.eligibility.request import prepare_dispatch
from backend.app.core.providers.models import DiscoveredModel, ProviderManifest
from backend.app.core.providers.registry import ProviderRegistry
from backend.app.core.telemetry.models import CandidateAttempt, RequestTrace
from backend.app.core.telemetry.store import get_telemetry_store

logger = logging.getLogger(__name__)
telemetry_logger = logging.getLogger("backend.app.telemetry")

MAX_FAILOVER_ATTEMPTS = 3


class AmbiguousModelError(ValueError):
    """A raw ID refers to different canonical identities."""

DEFAULT_COOLDOWN_SECONDS = 60.0


def _sanitize_error(exc: Exception, status_code: Optional[int]) -> str:
    """Sanitize error message to prevent leaking prompt echoes or raw upstream response bodies."""
    exc_name = exc.__class__.__name__
    if isinstance(exc, UpstreamRateLimitError):
        return f"{exc_name}: 429 rate limit exceeded"
    if status_code:
        return f"{exc_name}: HTTP status {status_code}"
    return f"{exc_name}: upstream error"


def _log_hop(
    request_id: str,
    hop_index: int,
    provider_id: str,
    model_id: str,
    status: str,
    status_code: Optional[int],
    duration_ms: float,
    error: Optional[str] = None,
) -> None:
    """Emit a single-line structured JSON log for an individual candidate hop (BR-6, AC-6)."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "hop_index": hop_index,
        "provider_id": provider_id,
        "model_id": model_id,
        "status": status,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "error": error,
    }
    telemetry_logger.info(json.dumps(entry))


class _BufferedStream:
    """Own upstream and finalize exactly one terminal trace, even before iteration."""
    def __init__(self, initial, upstream, finalize):
        self.initial = initial
        self.upstream = upstream
        self.finalize = finalize
        self.closed = False
        self.done = False
        self.finished = False
        self.error = None

    def __aiter__(self): return self

    async def __anext__(self):
        if self.closed: raise StopAsyncIteration
        try:
            if self.initial is not None:
                value, self.initial = self.initial, None
            else:
                value = await self.upstream.__anext__()
            if "data: [DONE]" in value: self.done = True
            return value
        except StopAsyncIteration:
            self.finished = self.done
            await self.aclose()
            raise
        except (UpstreamProviderError, UpstreamRateLimitError) as exc:
            self.error = exc
            reason = getattr(exc, "billing_reason", None)
            code = reason if reason in {"unexpected_paid_cost", "unverifiable_cost"} else "billing_unavailable" if reason else "upstream_stream_error"
            await self.aclose()
            return 'data: ' + json.dumps({"error":{"type":"billing_guard_error" if reason else "api_error",
                "code":code,"message":"Upstream billing guard stopped this response." if reason else "Upstream stream interrupted."}}) + '\n\n'
        except BaseException:
            await self.aclose()
            raise

    async def aclose(self):
        if self.closed: return
        self.closed = True
        self.initial = None
        with anyio.CancelScope(shield=True):
            try:
                await self.upstream.aclose()
            finally:
                await self.finalize(self.finished, self.error)


class CascadeRouter:
    """Manages model candidate resolution, circuit breaker, and cascade retries."""

    def __init__(
        self,
        registry: ProviderRegistry,
        provider_client: Optional[OpenAIProviderClient] = None,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
        max_attempts: int | None = None,
    ) -> None:
        self.registry = registry
        self.client = provider_client or OpenAIProviderClient()
        self.cooldown_seconds = cooldown_seconds
        self.max_attempts = registry.settings.max_failover_attempts if max_attempts is None else max_attempts
        if type(self.max_attempts) is not int or not 1 <= self.max_attempts <= 10:
            raise ValueError("Invalid failover attempt configuration.")
        # Cooldown map: (provider_id, model_id) -> expiration_timestamp
        self.resilience = registry.resilience

    async def _record_trace_safely(self, trace: RequestTrace) -> None:
        """Record telemetry trace fail-safely, ensuring store exceptions never disrupt requests (BR-4, AC-9)."""
        try:
            store = get_telemetry_store()
            safe_trace = trace.model_copy(deep=True)
            for secret in self.registry.secrets():
                safe_trace.requested_model = safe_trace.requested_model.replace(secret, "[REDACTED]")
                if safe_trace.resolved_candidate:
                    safe_trace.resolved_candidate = safe_trace.resolved_candidate.replace(secret, "[REDACTED]")
                for attempt in safe_trace.attempts:
                    attempt.model_id = attempt.model_id.replace(secret, "[REDACTED]")
                    attempt.provider_id = attempt.provider_id.replace(secret, "[REDACTED]")
            await store.record_trace(safe_trace)
        except Exception as exc:
            logger.warning("Failed to record telemetry trace.")

    @property
    def _cooldowns(self):
        """Read-only compatibility snapshot for protected validation isolation tests."""
        return self.resilience.cooldown_snapshot()

    def is_on_cooldown(self, provider_id: str, model_id: str) -> bool:
        manifest = self.registry.get_manifest(provider_id)
        return bool(manifest and not self.resilience.peek(manifest, model_id))

    def set_cooldown(self, provider_id: str, model_id: str, duration: Optional[float] = None) -> None:
        manifest = self.registry.get_manifest(provider_id)
        if manifest:
            self.resilience.manual_cooldown(manifest, model_id, self.cooldown_seconds if duration is None else duration)

    def _finish_health(self, ticket, outcome, handle):
        hold = self.registry.billing.holds.get(handle.scope)
        financial = handle.interrupted.is_set() or (hold is not None and hold is not handle.recovery_hold)
        self.resilience.finish(ticket, outcome, financial=financial)

    def _safe_id(self, value: str) -> str:
        for secret in self.registry.secrets():
            value = value.replace(secret, "[REDACTED]")
        return value

    def _diverse(self, models: list[DiscoveredModel]) -> list[DiscoveredModel]:
        groups = defaultdict(deque)
        for model in sorted(models, key=lambda item: item.id):
            groups[model.provider_id].append(model)
        priority = self.registry.settings.routing_provider_priority
        order = sorted(groups, key=lambda provider: (priority.index(provider) if provider in priority else len(priority), provider))
        result = []
        while any(groups.values()):
            for provider in order:
                if groups[provider]:
                    result.append(groups[provider].popleft())
        return result

    def resolve_candidates(self, requested_model: str, *, include_blocked=False) -> list[DiscoveredModel]:
        if self.registry.is_private_identifier(requested_model):
            return []
        models = self.registry.get_eligible_models()
        eligible = [m for m in models if include_blocked or not self.is_on_cooldown(m.provider_id, m.id)]
        target = requested_model.strip()
        if target.lower() == "auto:free":
            return self._diverse(eligible)
        # An exact canonical name takes precedence; otherwise resolve a raw ID once.
        canonical = {m.canonical_name for m in models if m.canonical_name == target}
        if not canonical:
            canonical = {m.canonical_name for m in models if m.id == target}
            # Preserve unambiguous legacy case-insensitive lookup without merging
            # distinct case-sensitive provider identities.
            if not canonical:
                canonical = {m.canonical_name for m in models if m.canonical_name.lower() == target.lower() or m.id.lower() == target.lower()}
            if len(canonical) > 1:
                raise AmbiguousModelError("Ambiguous model identifier.")
        if not canonical:
            return []
        tier1 = [m for m in eligible if m.canonical_name in canonical]
        tier2 = [m for m in eligible if m.canonical_name not in canonical]
        return self._diverse(tier1) + self._diverse(tier2)

    def _attempt(self, trace, candidate, hop, started, success, exc=None):
        status_code = 200 if success else getattr(exc, "status_code", 429 if isinstance(exc, UpstreamRateLimitError) else 502)
        error = None if success else _sanitize_error(exc or RuntimeError(), status_code)
        duration = (time.perf_counter() - started) * 1000
        status = "success" if success else "http_error"
        trace.attempts.append(CandidateAttempt(hop_index=hop, provider_id=candidate.provider_id,
            model_id=candidate.id, status=status, status_code=status_code, duration_ms=duration, error=error))
        _log_hop(trace.request_id, hop, self._safe_id(candidate.provider_id), self._safe_id(candidate.id), status, status_code, duration, error)

    async def _route(self, requested_model, payload, timeout, request_id, streaming):
        # Validate even internal callers; clients cannot inject routing overrides.
        from backend.app.core.eligibility.request import validate_request
        validate_request({"model":requested_model, **payload})
        trace = RequestTrace(request_id=request_id or str(uuid.uuid4()), requested_model=requested_model, stream=streaming)
        start = time.perf_counter()
        candidates = self.resolve_candidates(requested_model)
        attempts = 0
        budget = False
        for candidate in candidates:
            current = {(m.provider_id,m.id,m.canonical_name):m for m in self.registry.get_eligible_models()}
            candidate = current.get((candidate.provider_id,candidate.id,candidate.canonical_name))
            if candidate is None or self.registry.is_private_identifier(requested_model):continue
            manifest = self.registry.get_manifest(candidate.provider_id)
            if not manifest or not self.registry.request_supported(manifest,candidate.id,payload):continue
            if attempts >= self.max_attempts:
                budget = True
                break
            scope = self.registry.eligibility.scope(manifest)
            handle = self.registry.billing.begin(scope)
            if handle is None:continue
            ticket = self.resilience.acquire(manifest,candidate.id)
            if ticket is None:
                self.registry.billing.finish(handle,False)
                continue
            health = HealthOutcome()
            attempts += 1
            hop_start = time.perf_counter()
            stream = None
            handed_off = False
            success = False
            kwargs = dict(manifest=manifest,raw_model_id=candidate.id,canonical_model=requested_model,
                payload=prepare_dispatch(self.registry.dispatch_profile(manifest), {"model":requested_model, **payload}), timeout=timeout)
            if isinstance(self.client, OpenAIProviderClient):
                kwargs.update(guard=self.registry.billing,handle=handle,profile=self.registry.dispatch_profile(manifest),
                    credential=self.registry.credential(manifest),health=health)
            try:
                if not streaming:
                    response = await self.client.complete(**kwargs)
                    handle.complete = True
                    if not isinstance(self.client, OpenAIProviderClient):health.kind="success"
                    success = True
                    self._attempt(trace,candidate,attempts,hop_start,True)
                    trace.resolved_candidate = f"{candidate.provider_id}/{candidate.id}"
                    trace.success = True
                    trace.total_duration_ms = (time.perf_counter()-start)*1000
                    await self._record_trace_safely(trace)
                    return response
                stream = self.client.stream_complete(**kwargs)
                first = await stream.__anext__()

                # Bind locals: generator ownership moves beyond this stack frame.
                async def finalize(ok, exc=None, c=candidate, h=handle, n=attempts, t=hop_start, ticket=ticket, outcome=health):
                    if exc is not None:outcome.error(exc)
                    elif ok and not isinstance(self.client,OpenAIProviderClient):outcome.kind="success"
                    self._finish_health(ticket,outcome,h)
                    self.registry.billing.finish(h,ok)
                    self._attempt(trace,c,n,t,ok)
                    trace.resolved_candidate = f"{c.provider_id}/{c.id}"
                    trace.success = ok
                    trace.total_duration_ms = (time.perf_counter()-start)*1000
                    await self._record_trace_safely(trace)
                wrapper = _BufferedStream(first,stream,finalize)
                handed_off = True
                return wrapper
            except (UpstreamProviderError, UpstreamRateLimitError, StopAsyncIteration) as exc:
                health.error(exc)
                self._attempt(trace,candidate,attempts,hop_start,False,exc)
            finally:
                if not handed_off:
                    with anyio.CancelScope(shield=True):
                        try:
                            if stream is not None: await stream.aclose()
                        finally:
                            self._finish_health(ticket,health,handle)
                            self.registry.billing.finish(handle,success)
        trace.total_duration_ms = (time.perf_counter()-start)*1000
        await self._record_trace_safely(trace)
        message = "No active candidates available." if not candidates else "Failover attempt budget reached." if budget else "All free pool candidates exhausted."
        raise UpstreamProviderError(message,503,"pool",requested_model)

    async def route_completion(self, requested_model, payload, timeout=15.0, request_id=None):
        return await self._route(requested_model,payload,timeout,request_id,False)

    async def route_stream_completion(self, requested_model, payload, timeout=15.0, request_id=None):
        return await self._route(requested_model,payload,timeout,request_id,True)
