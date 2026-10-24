"""Compatibility facade; production lifecycle uses the shared orchestrator only."""
import httpx
from backend.app.core.discovery.orchestrator import DiscoveryOrchestrator
from backend.app.core.providers.registry import ProviderRegistry


class OpenRouterDiscoveryService:
    def __init__(self, registry: ProviderRegistry, http_client: httpx.AsyncClient | None = None):
        self.registry = registry
        self._discovery = DiscoveryOrchestrator(registry, http_client)

    async def discover_free_models(self):
        manifest = self.registry.get_manifest("openrouter")
        return await self._discovery.discover_provider(manifest) if manifest else []
