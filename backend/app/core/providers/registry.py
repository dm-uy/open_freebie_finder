"""Declarative provider registry, exact identities and in-memory admission snapshots."""
import asyncio
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic import ValidationError

from backend.app.config import Settings, get_settings
from backend.app.core.providers.models import DiscoveredModel, ProviderManifest

# Delivery policy is evaluated before enabled flags and credentials.
PROFILE_SKIPS = {"cerebras": "excluded", "github_models": "retired", "cloudflare": "unsupported_profile"}


class ProviderRegistry:
    def __init__(self, manifests_path: Optional[Path] = None, *, settings: Settings | None = None,
                 aliases_path: Path | None = None, manifests: list[ProviderManifest] | None = None,
                 evidence_source=None) -> None:
        self.settings = settings if settings is not None else get_settings()
        self.manifests_path = Path(manifests_path) if manifests_path else Path(__file__).parent / "providers.yaml"
        self._manifests: dict[str, ProviderManifest] = {}
        self.invalid_profiles: set[str] = set()
        self._models_cache: list[DiscoveredModel] = []
        self._snapshot_times: dict[str, float] = {}
        self._lock = asyncio.Lock()
        from backend.app.core.eligibility.evidence import EligibilityStore
        self.eligibility = EligibilityStore(self, evidence_source)
        from backend.app.core.eligibility.billing import BillingGuard
        self.billing = BillingGuard(self)
        from backend.app.core.balancer.resilience import ResilienceController
        self.resilience = ResilienceController(self)
        if manifests is None:
            self.load_manifests()
        else:
            self._manifests = {manifest.id: manifest for manifest in manifests}
        self.aliases: dict[tuple[str, str], str] = {}
        self._load_aliases(aliases_path or Path(__file__).parent / "model_aliases.yaml")
        from backend.app.core.eligibility.account import AccountEligibility
        self.accounts = AccountEligibility(self)
        from backend.app.core.tasks.catalog import TaskCatalog
        self.tasks = TaskCatalog(self)
        if set(self.settings.routing_provider_priority) - self._manifests.keys():
            raise ValueError("Invalid routing priority configuration.")

    def load_manifests(self) -> None:
        if not self.manifests_path.exists():
            raise FileNotFoundError("Provider manifests file not found.")
        try:
            with self.manifests_path.open(encoding="utf-8") as source:
                data = yaml.safe_load(source)
        except yaml.YAMLError:
            raise ValueError("Invalid provider manifest configuration.") from None
        loaded = {}
        self.invalid_profiles.clear()
        entries = data.get("providers", []) if isinstance(data, dict) else []
        if not isinstance(entries, list):
            entries = [None]
        for index, original in enumerate(entries):
            try:
                entry = dict(original)
                if "{account_id}" in entry.get("base_url", "") or "{account_id}" in entry.get("models_endpoint", ""):
                    account_id = self.settings.cloudflare_account_id or os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
                    if account_id:
                        entry["base_url"] = entry["base_url"].replace("{account_id}", account_id)
                        entry["models_endpoint"] = entry["models_endpoint"].replace("{account_id}", account_id)
                    else:
                        entry["is_enabled"] = False
                manifest = ProviderManifest(**entry)
                if manifest.id in loaded:
                    loaded.pop(manifest.id)
                    self.invalid_profiles.add(manifest.id)
                elif manifest.id not in self.invalid_profiles:
                    loaded[manifest.id] = manifest
            except (ValidationError, ValueError, TypeError, AttributeError):
                # Avoid retaining invalid input, even in dictionary keys/diagnostics.
                self.invalid_profiles.add(f"invalid_provider_{index}")

        self._manifests = loaded

    def _load_aliases(self, path: Path) -> None:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("aliases"), list):
                raise ValueError
            for entry in data["aliases"]:
                if not isinstance(entry, dict):
                    raise ValueError
                for field in ("provider_id", "raw_id", "canonical_name", "source"):
                    value = entry.get(field)
                    if not isinstance(value, str) or not value.strip() or (field != "source" and len(value) > 512):
                        raise ValueError
                pair = entry["provider_id"], entry["raw_id"]
                if pair in self.aliases:
                    raise ValueError
                self.aliases[pair] = entry["canonical_name"]
        except (OSError, ValueError, yaml.YAMLError):
            raise ValueError("Invalid model alias configuration.") from None

    def get_manifests(self) -> list[ProviderManifest]:
        return list(self._manifests.values())

    def get_manifest(self, provider_id: str) -> Optional[ProviderManifest]:
        return self._manifests.get(provider_id.lower())

    def credential(self, manifest: ProviderManifest) -> str | None:
        if manifest.auth.type == "none" or not manifest.auth.api_key_env:
            return None
        name = manifest.auth.api_key_env
        value = os.getenv(name) or getattr(self.settings, name.lower(), None)
        return value if isinstance(value, str) else None

    def secrets(self) -> list[str]:
        values = [self.settings.proxy_master_key] + [self.credential(p) for p in self._manifests.values()]
        return [value for value in values if value]

    def is_private_identifier(self, value: str) -> bool:
        return any(secret in value for secret in self.secrets())

    def profile_skip(self, manifest: ProviderManifest) -> str | None:
        if manifest.id in PROFILE_SKIPS:
            return PROFILE_SKIPS[manifest.id]
        if manifest.discovery.catalog_format != "openai":
            return "unsupported_profile"
        if not manifest.is_enabled:
            return "disabled"
        if any(char in value for value in (manifest.base_url, manifest.models_endpoint) for char in "{}"):
            return "unresolved_template"
        if manifest.auth.type != "none":
            name = manifest.auth.api_key_env
            if name:
                value = os.getenv(name) or getattr(self.settings, name.lower(), None)
                if value is not None and not isinstance(value, str):
                    return "invalid_configuration"
            if not self.credential(manifest):
                return "missing_credentials"
        return None

    def get_active_providers(self) -> list[ProviderManifest]:
        return [p for p in self._manifests.values() if self.profile_skip(p) is None]

    def canonical_name(self, manifest: ProviderManifest, raw_id: str) -> str:
        if manifest.id == "openrouter":
            return raw_id.removesuffix(":free")
        return self.aliases.get((manifest.id, raw_id), f"provider:{manifest.id}/{raw_id}")

    def dispatch_profile(self, manifest):
        from backend.app.core.eligibility.evidence import openrouter_bound
        from backend.app.core.eligibility.account import account_bound
        return "openrouter_zero_price" if openrouter_bound(manifest) else manifest.eligibility_profile if account_bound(manifest) else None

    def _evidence_policy_supported(self, manifest, evidence):
        from backend.app.core.eligibility.request import zero_price_policy_active
        if evidence.verdict.basis == "catalog_zero_tokens_with_request_ceiling":
            from backend.app.core.eligibility.evidence import openrouter_bound
            return openrouter_bound(manifest) and zero_price_policy_active(self.dispatch_profile(manifest))
        return True

    def request_supported(self, manifest, model_id, payload):
        from backend.app.core.eligibility.request import uses_tools
        record = self.eligibility.get(manifest, model_id)
        return bool(record and self._evidence_policy_supported(manifest, record) and (not uses_tools(payload) or record.verdict.tools))

    def admits(self, manifest: ProviderManifest, model: DiscoveredModel) -> bool:
        self.eligibility.scope(manifest)
        from backend.app.core.eligibility.account import account_profile
        conditional = account_profile(manifest)
        if (not conditional and not model.is_free) or self.profile_skip(manifest) is not None:
            return False
        evidence = self.eligibility.get(manifest, model.id)
        if evidence is None or evidence.verdict.state != "free" or not self._evidence_policy_supported(manifest, evidence) or not self.billing.available(evidence.scope):
            return False
        if not conditional and manifest.chat_model_allowlist and model.id not in manifest.chat_model_allowlist:
            return False
        return not any(self.is_private_identifier(value) for value in (model.id, model.canonical_name, model.provider_id))

    async def register_models(self, models: list[DiscoveredModel], provider_id: Optional[str] = None) -> None:
        async with self._lock:
            targets = {model.provider_id for model in models}
            if provider_id:
                targets.add(provider_id)
            self._models_cache = [m for m in self._models_cache if m.provider_id not in targets] + list(models[:1000])
            for target in targets:
                self._snapshot_times[target] = time.monotonic()

    def get_models(self) -> list[DiscoveredModel]:
        """Raw cached snapshot for compatibility/admin counts; no I/O."""
        return list(self._models_cache)

    def get_eligible_models(self) -> list[DiscoveredModel]:
        """Recheck current policy, secrets and monotonic freshness, entirely in memory."""
        now = time.monotonic()
        result = []
        for model in self._models_cache:
            manifest = self.get_manifest(model.provider_id)
            success_at = self._snapshot_times.get(model.provider_id)
            if manifest is None or success_at is None:
                continue
            if now - success_at > 2 * self.settings.discovery_interval_seconds:
                continue
            if self.admits(manifest, model):
                result.append(model)
        return result

    def get_model_candidates(self, canonical_name: str) -> list[DiscoveredModel]:
        target = canonical_name.strip().lower()
        return [m for m in self.get_eligible_models() if m.canonical_name.lower() == target]


@lru_cache
def get_registry() -> ProviderRegistry:
    return ProviderRegistry()
