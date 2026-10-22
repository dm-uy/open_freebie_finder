"""Two-Tier Cascade Failover Router with Circuit Breaker."""
import logging
import time
from typing import Any, AsyncGenerator, Optional
from backend.app.core.adapters.openai_client import (
    OpenAIProviderClient,
    UpstreamProviderError,
    UpstreamRateLimitError,
)
from backend.app.core.providers.models import DiscoveredModel, ProviderManifest
from backend.app.core.providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)

MAX_FAILOVER_ATTEMPTS = 3
DEFAULT_COOLDOWN_SECONDS = 60.0


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

    def is_on_cooldown(self, provider_id: str, model_id: str) -> bool:
        """Check whether a specific provider/model is currently in cool-off period."""
        exp = self._cooldowns.get((provider_id, model_id))
        if exp is None:
            return False
        if time.time() >= exp:
            del self._cooldowns[(provider_id, model_id)]
            return False
        return True

    def set_cooldown(self, provider_id: str, model_id: str, duration: Optional[float] = None) -> None:
        """Place a candidate model on cooldown after a 429/5xx error."""
        dur = duration if duration is not None else self.cooldown_seconds
        self._cooldowns[(provider_id, model_id)] = time.time() + dur
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
    ) -> dict[str, Any]:
        """Route non-streaming completion with cascade retry across candidates."""
        candidates = self.resolve_candidates(requested_model)
        if not candidates:
            raise UpstreamProviderError(
                f"No active candidates available for model '{requested_model}'",
                503,
                "none",
                requested_model,
            )

        attempts = 0
        last_error: Optional[Exception] = None

        for candidate in candidates:
            if attempts >= MAX_FAILOVER_ATTEMPTS:
                break
            attempts += 1

            manifest = self.registry.get_manifest(candidate.provider_id)
            if not manifest:
                continue

            try:
                response = await self.client.complete(
                    manifest=manifest,
                    raw_model_id=candidate.id,
                    canonical_model=requested_model,
                    payload=payload,
                    timeout=timeout,
                )
                return response
            except (UpstreamRateLimitError, UpstreamProviderError) as exc:
                last_error = exc
                self.set_cooldown(candidate.provider_id, candidate.id)
                logger.warning(
                    "Failover triggered from (%s, %s): %s. Moving to next candidate.",
                    candidate.provider_id,
                    candidate.id,
                    str(exc),
                )

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
    ) -> AsyncGenerator[str, None]:
        """Route streaming completion with first-token pre-buffering and cascade retry."""
        candidates = self.resolve_candidates(requested_model)
        if not candidates:
            raise UpstreamProviderError(
                f"No active candidates available for model '{requested_model}'",
                503,
                "none",
                requested_model,
            )

        attempts = 0
        last_error: Optional[Exception] = None

        for candidate in candidates:
            if attempts >= MAX_FAILOVER_ATTEMPTS:
                break
            attempts += 1

            manifest = self.registry.get_manifest(candidate.provider_id)
            if not manifest:
                continue

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

                # First chunk succeeded! Yield it, then stream remaining chunks from this candidate
                async def stream_wrapper(initial: str, rest_gen):
                    yield initial
                    async for chunk in rest_gen:
                        yield chunk

                return stream_wrapper(first_chunk, stream_gen)

            except (UpstreamRateLimitError, UpstreamProviderError, StopAsyncIteration) as exc:
                last_error = exc
                self.set_cooldown(candidate.provider_id, candidate.id)
                logger.warning(
                    "Streaming failover triggered on pre-buffer from (%s, %s): %s",
                    candidate.provider_id,
                    candidate.id,
                    str(exc),
                )

        raise UpstreamProviderError(
            f"All free pool candidates exhausted for model '{requested_model}'. Last error: {last_error}",
            503,
            "pool",
            requested_model,
        )
