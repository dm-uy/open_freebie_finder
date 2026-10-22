"""Two-Tier Cascade Failover Router with Circuit Breaker and Structured Telemetry."""
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional
from backend.app.core.adapters.openai_client import (
    OpenAIProviderClient,
    UpstreamProviderError,
    UpstreamRateLimitError,
)
from backend.app.core.providers.models import DiscoveredModel, ProviderManifest
from backend.app.core.providers.registry import ProviderRegistry
from backend.app.core.telemetry.models import CandidateAttempt, RequestTrace
from backend.app.core.telemetry.store import get_telemetry_store

logger = logging.getLogger(__name__)
telemetry_logger = logging.getLogger("backend.app.telemetry")

MAX_FAILOVER_ATTEMPTS = 3
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


class CascadeRouter:
    """Manages model candidate resolution, circuit breaker, and cascade retries."""

    def __init__(
        self,
        registry: ProviderRegistry,
        provider_client: Optional[OpenAIProviderClient] = None,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
    ) -> None:
        self.registry = registry
        self.client = provider_client or OpenAIProviderClient()
        self.cooldown_seconds = cooldown_seconds
        # Cooldown map: (provider_id, model_id) -> expiration_timestamp
        self._cooldowns: dict[tuple[str, str], float] = {}

    async def _record_trace_safely(self, trace: RequestTrace) -> None:
        """Record telemetry trace fail-safely, ensuring store exceptions never disrupt requests (BR-4, AC-9)."""
        try:
            store = get_telemetry_store()
            await store.record_trace(trace)
        except Exception as exc:
            logger.warning("Failed to record telemetry trace: %s", str(exc))

    def is_on_cooldown(self, provider_id: str, model_id: str) -> bool:
        """Check whether a specific provider/model is currently in cool-off period using monotonic clock."""
        exp = self._cooldowns.get((provider_id, model_id))
        if exp is None:
            return False
        if time.monotonic() >= exp:
            del self._cooldowns[(provider_id, model_id)]
            return False
        return True

    def set_cooldown(self, provider_id: str, model_id: str, duration: Optional[float] = None) -> None:
        """Place a candidate model on cooldown after a 429/5xx error."""
        dur = duration if duration is not None else self.cooldown_seconds
        self._cooldowns[(provider_id, model_id)] = time.monotonic() + dur
        logger.info("Candidate (%s, %s) placed on cooldown for %ds", provider_id, model_id, int(dur))

    def resolve_candidates(self, requested_model: str) -> list[DiscoveredModel]:
        """Resolve prioritized candidates applying Two-Tier failover strategy.

        Tier 1: Candidates matching the exact requested canonical name across active providers.
        Tier 2: Alternative active free models sorted deterministically by (provider_id, canonical_name).
        """
        active_manifests = {p.id: p for p in self.registry.get_active_providers()}
        all_models = self.registry.get_models()

        # Filter models from active providers that are not currently on cooldown
        active_models = [
            m for m in all_models
            if m.provider_id in active_manifests and not self.is_on_cooldown(m.provider_id, m.id)
        ]

        # Case 1: auto:free requested -> return all active models sorted alphabetically
        if requested_model.lower() == "auto:free":
            return sorted(active_models, key=lambda m: (m.provider_id, m.canonical_name))

        target_canonical = requested_model.strip().lower()

        # If model is not auto:free, verify it is a known model in the registry (by canonical or raw id)
        is_known = any(
            m.canonical_name.lower() == target_canonical or m.id.lower() == target_canonical
            for m in all_models
        )
        if not is_known:
            return []

        # Tier 1: Same model across active providers
        tier_1 = [
            m for m in active_models
            if m.canonical_name.lower() == target_canonical or m.id.lower() == target_canonical
        ]
        # Sort Tier 1 deterministically
        tier_1_sorted = sorted(tier_1, key=lambda m: (m.provider_id, m.id))

        # Tier 2: Alternative backup models (excluding those already in Tier 1)
        tier_1_ids = {(m.provider_id, m.id) for m in tier_1_sorted}
        tier_2 = [
            m for m in active_models
            if (m.provider_id, m.id) not in tier_1_ids
        ]
        tier_2_sorted = sorted(tier_2, key=lambda m: (m.provider_id, m.canonical_name))

        # Combined candidate queue: Tier 1 followed by Tier 2
        return tier_1_sorted + tier_2_sorted

    async def route_completion(
        self,
        requested_model: str,
        payload: dict[str, Any],
        timeout: float = 15.0,
        request_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Route non-streaming completion with cascade retry and structured telemetry."""
        req_id = request_id or str(uuid.uuid4())
        start_total = time.perf_counter()
        trace = RequestTrace(
            request_id=req_id,
            requested_model=requested_model,
            stream=False,
        )

        candidates = self.resolve_candidates(requested_model)
        if not candidates:
            trace.total_duration_ms = (time.perf_counter() - start_total) * 1000
            trace.success = False
            await self._record_trace_safely(trace)
            raise UpstreamProviderError(
                f"No active candidates available for model '{requested_model}'",
                503,
                "none",
                requested_model,
            )

        attempts = 0
        last_error: Optional[Exception] = None

        for candidate in candidates:
            manifest = self.registry.get_manifest(candidate.provider_id)
            if not manifest:
                continue

            if attempts >= MAX_FAILOVER_ATTEMPTS:
                break
            attempts += 1

            hop_start = time.perf_counter()
            try:
                response = await self.client.complete(
                    manifest=manifest,
                    raw_model_id=candidate.id,
                    canonical_model=requested_model,
                    payload=payload,
                    timeout=timeout,
                )
                dur = (time.perf_counter() - hop_start) * 1000
                _log_hop(
                    request_id=req_id,
                    hop_index=attempts,
                    provider_id=candidate.provider_id,
                    model_id=candidate.id,
                    status="success",
                    status_code=200,
                    duration_ms=dur,
                )
                trace.attempts.append(
                    CandidateAttempt(
                        hop_index=attempts,
                        provider_id=candidate.provider_id,
                        model_id=candidate.id,
                        status="success",
                        status_code=200,
                        duration_ms=dur,
                    )
                )
                trace.resolved_candidate = f"{candidate.provider_id}/{candidate.id}"
                trace.success = True
                trace.total_duration_ms = (time.perf_counter() - start_total) * 1000
                await self._record_trace_safely(trace)
                return response
            except (UpstreamRateLimitError, UpstreamProviderError) as exc:
                dur = (time.perf_counter() - hop_start) * 1000
                last_error = exc
                status_code = getattr(exc, "status_code", 429 if isinstance(exc, UpstreamRateLimitError) else 500)
                err_msg = _sanitize_error(exc, status_code)
                _log_hop(
                    request_id=req_id,
                    hop_index=attempts,
                    provider_id=candidate.provider_id,
                    model_id=candidate.id,
                    status="http_error",
                    status_code=status_code,
                    duration_ms=dur,
                    error=err_msg,
                )
                trace.attempts.append(
                    CandidateAttempt(
                        hop_index=attempts,
                        provider_id=candidate.provider_id,
                        model_id=candidate.id,
                        status="http_error",
                        status_code=status_code,
                        duration_ms=dur,
                        error=err_msg,
                    )
                )
                self.set_cooldown(candidate.provider_id, candidate.id)
                logger.warning(
                    "Failover triggered from (%s, %s): %s. Moving to next candidate.",
                    candidate.provider_id,
                    candidate.id,
                    str(exc),
                )

        trace.total_duration_ms = (time.perf_counter() - start_total) * 1000
        trace.success = False
        await self._record_trace_safely(trace)
        raise UpstreamProviderError(
            f"All free pool candidates exhausted for model '{requested_model}'. Last error: {last_error}",
            503,
            "pool",
            requested_model,
        )

    async def route_stream_completion(
        self,
        requested_model: str,
        payload: dict[str, Any],
        timeout: float = 15.0,
        request_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Route streaming completion with first-token pre-buffering and structured telemetry."""
        req_id = request_id or str(uuid.uuid4())
        start_total = time.perf_counter()
        trace = RequestTrace(
            request_id=req_id,
            requested_model=requested_model,
            stream=True,
        )

        candidates = self.resolve_candidates(requested_model)
        if not candidates:
            trace.total_duration_ms = (time.perf_counter() - start_total) * 1000
            trace.success = False
            await self._record_trace_safely(trace)
            raise UpstreamProviderError(
                f"No active candidates available for model '{requested_model}'",
                503,
                "none",
                requested_model,
            )

        attempts = 0
        last_error: Optional[Exception] = None

        for candidate in candidates:
            manifest = self.registry.get_manifest(candidate.provider_id)
            if not manifest:
                continue

            if attempts >= MAX_FAILOVER_ATTEMPTS:
                break
            attempts += 1

            hop_start = time.perf_counter()
            try:
                # Open candidate stream generator
                stream_gen = self.client.stream_complete(
                    manifest=manifest,
                    raw_model_id=candidate.id,
                    canonical_model=requested_model,
                    payload=payload,
                    timeout=timeout,
                )

                # Attempt to retrieve first chunk to verify stream validity (pre-buffering)
                first_chunk = await stream_gen.__anext__()

                dur = (time.perf_counter() - hop_start) * 1000
                _log_hop(
                    request_id=req_id,
                    hop_index=attempts,
                    provider_id=candidate.provider_id,
                    model_id=candidate.id,
                    status="success",
                    status_code=200,
                    duration_ms=dur,
                )
                trace.attempts.append(
                    CandidateAttempt(
                        hop_index=attempts,
                        provider_id=candidate.provider_id,
                        model_id=candidate.id,
                        status="success",
                        status_code=200,
                        duration_ms=dur,
                    )
                )
                trace.resolved_candidate = f"{candidate.provider_id}/{candidate.id}"
                trace.success = True
                trace.total_duration_ms = (time.perf_counter() - start_total) * 1000
                await self._record_trace_safely(trace)

                # First chunk succeeded! Yield it, then stream remaining chunks from this candidate
                async def stream_wrapper(initial: str, rest_gen):
                    yield initial
                    async for chunk in rest_gen:
                        yield chunk

                return stream_wrapper(first_chunk, stream_gen)

            except (UpstreamRateLimitError, UpstreamProviderError, StopAsyncIteration) as exc:
                dur = (time.perf_counter() - hop_start) * 1000
                last_error = exc
                status_code = getattr(exc, "status_code", 429 if isinstance(exc, UpstreamRateLimitError) else 500)
                status_name = "stream_error" if isinstance(exc, StopAsyncIteration) else "http_error"
                err_msg = _sanitize_error(exc, status_code)
                _log_hop(
                    request_id=req_id,
                    hop_index=attempts,
                    provider_id=candidate.provider_id,
                    model_id=candidate.id,
                    status=status_name,
                    status_code=status_code,
                    duration_ms=dur,
                    error=err_msg,
                )
                trace.attempts.append(
                    CandidateAttempt(
                        hop_index=attempts,
                        provider_id=candidate.provider_id,
                        model_id=candidate.id,
                        status=status_name,
                        status_code=status_code,
                        duration_ms=dur,
                        error=err_msg,
                    )
                )
                self.set_cooldown(candidate.provider_id, candidate.id)
                logger.warning(
                    "Streaming failover triggered on pre-buffer from (%s, %s): %s",
                    candidate.provider_id,
                    candidate.id,
                    str(exc),
                )

        trace.total_duration_ms = (time.perf_counter() - start_total) * 1000
        trace.success = False
        await self._record_trace_safely(trace)
        raise UpstreamProviderError(
            f"All free pool candidates exhausted for model '{requested_model}'. Last error: {last_error}",
            503,
            "pool",
            requested_model,
        )
