"""Declarative Provider Registry and In-Memory Model Cache."""
import asyncio
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional
import yaml
from backend.app.config import get_settings
from backend.app.core.providers.models import DiscoveredModel, ProviderManifest


class ProviderRegistry:
    """Manages provider manifests and thread-safe in-memory model cache."""

    def __init__(self, manifests_path: Optional[Path] = None) -> None:
        if manifests_path is None:
            # Default to providers.yaml in the same directory
            self.manifests_path = Path(__file__).parent / "providers.yaml"
        else:
            self.manifests_path = Path(manifests_path)

        self._manifests: dict[str, ProviderManifest] = {}
        self._models_cache: list[DiscoveredModel] = []
        self._lock = asyncio.Lock()
        self.load_manifests()

    def load_manifests(self) -> None:
        """Read providers.yaml and validate all provider manifests."""
        if not self.manifests_path.exists():
            raise FileNotFoundError(f"Provider manifests file not found: {self.manifests_path}")

        with open(self.manifests_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        settings = get_settings()
        raw_providers = data.get("providers", []) if isinstance(data, dict) else []

        loaded: dict[str, ProviderManifest] = {}
        for entry in raw_providers:
            # Resolve template variables if present (e.g. {account_id} for Cloudflare)
            if "{account_id}" in entry.get("base_url", "") or "{account_id}" in entry.get("models_endpoint", ""):
                acc_id = settings.cloudflare_account_id or os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
                if acc_id:
                    entry["base_url"] = entry["base_url"].replace("{account_id}", acc_id)
                    entry["models_endpoint"] = entry["models_endpoint"].replace("{account_id}", acc_id)
                else:
                    # Keep URL template, but flag disabled until account_id is configured
                    entry["is_enabled"] = False

            manifest = ProviderManifest(**entry)
            loaded[manifest.id] = manifest

        self._manifests = loaded

    def get_manifests(self) -> list[ProviderManifest]:
        """Return all loaded provider manifests."""
        return list(self._manifests.values())

    def get_manifest(self, provider_id: str) -> Optional[ProviderManifest]:
        """Look up a provider manifest by its ID."""
        return self._manifests.get(provider_id.lower())

    def get_active_providers(self) -> list[ProviderManifest]:
        """Return enabled providers with configured credentials or auth type 'none'."""
        active: list[ProviderManifest] = []
        settings = get_settings()

        for manifest in self._manifests.values():
            if not manifest.is_enabled:
                continue

            # Check authentication requirements
            if manifest.auth.type == "none":
                active.append(manifest)
            elif manifest.auth.api_key_env:
                env_key = manifest.auth.api_key_env
                # Look up key in environment or settings
                val = os.getenv(env_key) or getattr(settings, env_key.lower(), None)
                if val:
                    active.append(manifest)

        return active

    async def register_models(
        self,
        models: list[DiscoveredModel],
        provider_id: Optional[str] = None,
    ) -> None:
        """Update the in-memory cache of discovered models under asyncio.Lock.

        If provider_id is specified (or inferred from models), existing cached entries
        for that provider are replaced (allowing purging of deprecated models).
        """
        async with self._lock:
            target_providers = {m.provider_id for m in models}
            if provider_id:
                target_providers.add(provider_id)
            preserved = [m for m in self._models_cache if m.provider_id not in target_providers]
            self._models_cache = preserved + models

    def get_models(self) -> list[DiscoveredModel]:
        """Return a snapshot of discovered models directly from memory (< 2ms, zero I/O)."""
        return list(self._models_cache)

    def get_model_candidates(self, canonical_name: str) -> list[DiscoveredModel]:
        """Return candidate models matching the canonical name across active providers."""
        target = canonical_name.strip().lower()
        active_ids = {p.id for p in self.get_active_providers()}
        return [
            m for m in self._models_cache
            if m.canonical_name.lower() == target and (not active_ids or m.provider_id in active_ids)
        ]


@lru_cache
def get_registry() -> ProviderRegistry:
    """Return cached application ProviderRegistry singleton."""
    return ProviderRegistry()
