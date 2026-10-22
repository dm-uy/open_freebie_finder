"""Dynamic OpenRouter Free Models Discovery Service."""
import logging
import os
from typing import Optional
import httpx
from backend.app.config import get_settings
from backend.app.core.providers.models import DiscoveredModel
from backend.app.core.providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)


class OpenRouterDiscoveryService:
    """Discovers zero-cost models from OpenRouter dynamically."""

    def __init__(
        self,
        registry: ProviderRegistry,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.registry = registry
        self._external_client = http_client

    async def discover_free_models(self) -> list[DiscoveredModel]:
        """Fetch models from OpenRouter and extract active zero-cost models."""
        manifest = self.registry.get_manifest("openrouter")
        endpoint = manifest.models_endpoint if manifest else "https://openrouter.ai/api/v1/models"

        settings = get_settings()
        api_key = os.getenv("OPENROUTER_API_KEY") or settings.openrouter_api_key

        headers = {
            "Accept": "application/json",
            "User-Agent": "open-freebie-finder/0.1.0 (https://github.com/dm-uy/open_freebie_finder)",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            if self._external_client:
                response = await self._external_client.get(endpoint, headers=headers, timeout=15.0)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.get(endpoint, headers=headers, timeout=15.0)

            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as exc:
            logger.warning(
                "OpenRouter discovery query failed gracefully (retaining existing cache): %s",
                str(exc),
            )
            return []

        raw_models = data.get("data", []) if isinstance(data, dict) else []
        free_models: list[DiscoveredModel] = []

        for item in raw_models:
            if not isinstance(item, dict):
                continue

            pricing = item.get("pricing", {})
            if not isinstance(pricing, dict):
                continue

            prompt_cost = str(pricing.get("prompt", "")).strip()
            completion_cost = str(pricing.get("completion", "")).strip()

            # Strictly require both prompt and completion pricing to be zero
            is_zero_cost = prompt_cost in ("0", "0.0", "0.00") and completion_cost in ("0", "0.0", "0.00")
            if not is_zero_cost:
                continue

            raw_id = item.get("id")
            if not raw_id or not isinstance(raw_id, str):
                continue

            # Canonical name normalization: strip trailing :free
            canonical_name = raw_id
            if canonical_name.endswith(":free"):
                canonical_name = canonical_name[:-5]

            # Context window extraction with safe float/int parsing and fallback
            raw_context = item.get("context_length")
            try:
                if raw_context is not None:
                    context_window = int(float(raw_context))
                    if context_window <= 0:
                        context_window = 4096
                else:
                    context_window = 4096
            except (ValueError, TypeError, OverflowError):
                context_window = 4096

            free_models.append(
                DiscoveredModel(
                    id=raw_id,
                    canonical_name=canonical_name,
                    provider_id="openrouter",
                    context_window=context_window,
                    is_free=True,
                    metadata={
                        "description": item.get("description", ""),
                        "pricing": pricing,
                        "architecture": item.get("architecture", {}),
                    },
                )
            )

        # On successful response parsing, update the registry (purges old models even if free_models is empty)
        await self.registry.register_models(free_models, provider_id="openrouter")

        return free_models
