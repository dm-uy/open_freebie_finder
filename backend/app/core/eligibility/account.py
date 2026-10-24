"""Conditional account assertions and independently expiring route availability.

An assertion is operator policy, never an observed tariff. Nothing in this module
sends HTTP or makes pending candidates routable for qualification.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
import time

from backend.app.core.eligibility.evidence import Evidence, Verdict, endpoint_identity

PROFILES = {
    "groq": ("groq_account_probe", "api.groq.com", "/openai/v1", "GROQ_API_KEY"),
    "nvidia_nim": ("nvidia_account_probe", "integrate.api.nvidia.com", "/v1", "NVIDIA_API_KEY"),
    "mistral": ("mistral_account_probe", "api.mistral.ai", "/v1", "MISTRAL_API_KEY"),
    "huggingface": ("hf_account_probe", "router.huggingface.co", "/v1", "HUGGINGFACE_API_KEY"),
}
LEASE_SECONDS = 86400
RENEW_SECONDS = 43200
ACTIVE_LIMIT = 5


def account_profile(manifest):
    return manifest.eligibility_profile in {p[0] for p in PROFILES.values()}


def account_bound(manifest):
    entry = PROFILES.get(manifest.id)
    if not entry:
        return False
    profile, host, path, key = entry
    return (manifest.eligibility_profile == profile
            and endpoint_identity(manifest) == ("https", host, 443, path + "/chat/completions")
            and manifest.models_endpoint == f"https://{host}{path}/models"
            and manifest.auth.type == "bearer" and manifest.auth.api_key_env == key
            and manifest.auth.custom_header_name is None
            and manifest.discovery.type == "all_available"
            and manifest.discovery.catalog_format == "openai")


def safe_id(value, registry):
    return (isinstance(value, str) and 0 < len(value) <= 512 and value == value.strip()
            and not any(c.isspace() or ord(c) < 32 or ord(c) == 127 or c in '{}?\\#' for c in value)
            and not registry.is_private_identifier(value))


def candidate_tools(metadata):
    caps = metadata.get("capabilities", {})
    return isinstance(caps, dict) and caps.get("function_calling") is True


@dataclass(repr=False)
class Candidate:
    model_id: str
    metadata: dict
    scope: tuple
    observed_at: float
    source_until: float
    source_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    passed_at: float | None = None
    published_at: float = 0
    active: bool = False
    retry_at: float = 0
    reason: str = "pending"


class AccountEligibility:
    """Process-local assertions; observed changes revoke them until a new startup."""
    def __init__(self, registry):
        self.registry = registry
        self.confirmations = tuple(registry.settings.free_account_confirmations)
        self.loaded_at = datetime.now(timezone.utc).isoformat()
        self.assertions = {}
        self.revoked = set()
        self.candidates: dict[tuple[str, str], Candidate] = {}
        self.inflight: dict[str, asyncio.Task] = {}
        self.suspended = set()
        self.paused_until = {}
        registry.billing.hold_observers.append(self.on_hold)
        for manifest in registry.get_manifests():
            if manifest.id in self.confirmations:
                self.assertions[manifest.id] = registry.eligibility.scope(manifest)

    def on_hold(self, scope, hold):
        if hold.expires_at is not None:
            self.suspended.add(scope[0])
        self.cancel(scope[0])

    def cancel(self, provider):
        task = self.inflight.get(provider)
        if task and task is not asyncio.current_task():
            task.cancel()

    def changed(self, provider):
        if provider in self.assertions:
            self.revoked.add(provider)
        self.candidates = {k: v for k, v in self.candidates.items() if k[0] != provider}
        self.cancel(provider)

    def observe(self):
        if tuple(self.registry.settings.free_account_confirmations) != self.confirmations:
            for provider in self.assertions:
                self.changed(provider)
        for manifest in self.registry.get_manifests():
            self.registry.eligibility.scope(manifest)
        for provider in set(self.assertions) - {p.id for p in self.registry.get_manifests()}:
            self.changed(provider)
        # Once a balance hold has been observed, the worker may not perform recovery.
        for scope, hold in self.registry.billing.holds.items():
            if hold.expires_at is not None:
                self.suspended.add(scope[0])

    def assertion_reason(self, manifest):
        scope = self.registry.eligibility.scope(manifest)
        if tuple(self.registry.settings.free_account_confirmations) != self.confirmations:
            self.changed(manifest.id)
        if manifest.id in self.revoked:
            return "credential_revoked"
        if manifest.id not in self.assertions:
            return "assertion_required"
        if not self.registry.credential(manifest):
            return "credential_missing"
        if not account_bound(manifest) or self.assertions[manifest.id] != scope:
            self.changed(manifest.id)
            return "credential_revoked"
        if self.registry.profile_skip(manifest):
            return "source_unavailable"
        return None

    def invalidate_source(self, provider):
        for (p, _), candidate in self.candidates.items():
            if p == provider:
                candidate.source_until = 0
        self.cancel(provider)

    def publish(self, manifest, observations, scope):
        if self.registry.eligibility.scope(manifest) != scope:
            return False
        now = time.monotonic()
        retained = {}
        for model, metadata in observations.items():
            key = manifest.id, model
            old = self.candidates.get(key)
            if old and old.scope == scope and old.metadata == metadata:
                old.observed_at = now
                old.source_utc = datetime.now(timezone.utc).isoformat()
                old.source_until = now + self.registry.settings.eligibility_ttl_seconds
                retained[key] = old
            else:
                if old:
                    self.cancel(manifest.id)
                retained[key] = Candidate(model, metadata, scope, now,
                    now + self.registry.settings.eligibility_ttl_seconds)
        removed = set(k for k in self.candidates if k[0] == manifest.id) - retained.keys()
        if removed:
            self.cancel(manifest.id)
        self.candidates = {k: v for k, v in self.candidates.items() if k[0] != manifest.id} | retained
        # Restore a cached healthy pass after source recovery only into vacancies.
        active = [c for (p, _), c in self.candidates.items()
                  if p == manifest.id and c.active and self.healthy(c, now)]
        for (p, _), c in retained.items():
            if p == manifest.id and not c.active and self.healthy(c, now) and len(active) < ACTIVE_LIMIT:
                c.active = True
                c.published_at = now
                active.append(c)
        return True

    @staticmethod
    def healthy(candidate, now):
        return candidate.passed_at is not None and now < candidate.passed_at + LEASE_SECONDS

    def current(self, manifest, candidate):
        return (not self.assertion_reason(manifest)
                and self.candidates.get((manifest.id, candidate.model_id)) is candidate
                and candidate.scope == self.registry.eligibility.scope(manifest)
                and time.monotonic() < candidate.source_until)

    def get(self, manifest, model_id):
        now = time.monotonic()
        reason = self.assertion_reason(manifest)
        c = self.candidates.get((manifest.id, model_id))
        if c is None:
            return None
        reason = reason or ("source_unavailable" if now >= c.source_until else
                            "expired" if c.passed_at is not None and not self.healthy(c, now) else
                            None if c.active and self.healthy(c, now) else c.reason)
        verdict = Verdict(reason=reason or "account_asserted_available", assurance="user_asserted")
        if reason is None:
            verdict = Verdict("free", "user_confirmed_account_probe", "account_asserted_available",
                              candidate_tools(c.metadata), "user_asserted")
        return Evidence(c.scope, verdict, c.observed_at,
            min(c.source_until, c.passed_at + LEASE_SECONDS) if c.passed_at is not None else c.source_until,
            c.source_utc, manifest.eligibility_profile)

    def pass_pair(self, manifest, candidate):
        if not self.current(manifest, candidate) or not self.registry.billing.available(candidate.scope):
            return False
        now = time.monotonic()
        others = [c for (p, _), c in self.candidates.items()
                  if p == manifest.id and c is not candidate and c.active and self.healthy(c, now)]
        if len(others) >= ACTIVE_LIMIT:
            min(others, key=lambda c: c.published_at).active = False
        candidate.passed_at = candidate.published_at = now
        candidate.active = True
        candidate.retry_at = now + RENEW_SECONDS
        candidate.reason = "available"
        return True

    def fail_pair(self, manifest, candidate, status=None, retry_after=None, diagnostics=None):
        from backend.app.core.eligibility.billing import retry_seconds
        candidate.active = False
        candidate.passed_at = None
        candidate.reason = "probe_inconclusive"
        delay = 60
        if (manifest.id == "nvidia_nim" and status == 404 and isinstance(diagnostics, dict)
                and diagnostics.get("error_contract") == "function_not_found_for_account"):
            # An advertised function can be unavailable to this credential.
            # Reuse the bounded route-negative cache, never a provider-wide hold.
            delay = 3600
            candidate.reason = "incompatible"
        elif status in {400, 403}:
            delay = 3600
            candidate.reason = "incompatible"
        elif status == 429:
            delay = retry_seconds(retry_after)
            self.paused_until[manifest.id] = time.monotonic() + delay
            candidate.reason = "retryable"
        elif status == 401:
            self.suspended.add(manifest.id)
            for (p, _), c in self.candidates.items():
                if p == manifest.id:
                    c.active = False
                    c.passed_at = None
                    c.reason = "credential_revoked"
        candidate.retry_at = time.monotonic() + delay
        self.observe()

    def diagnostics(self, manifest):
        self.observe()
        rows = [c for (p, _), c in self.candidates.items() if p == manifest.id]
        records = [self.get(manifest, c.model_id) for c in rows]
        return {"assurance": "user_asserted", "assertion_loaded_at": self.loaded_at,
            "source_age_seconds": max((max(0, time.monotonic() - c.observed_at) for c in rows), default=None),
            "source_expires_in_seconds": min((max(0, c.source_until-time.monotonic()) for c in rows), default=None),
            "states": {state: sum(bool(r and r.verdict.state == state) for r in records) for state in ("free", "paid", "unknown")},
            "reasons": {reason: sum(bool(r and r.verdict.reason == reason) for r in records)
                        for reason in sorted({r.verdict.reason for r in records if r})},
            "bases": sorted({r.verdict.basis for r in records if r}),
            "source_ids": [manifest.eligibility_profile],
            "assertion_reason": self.assertion_reason(manifest), "automatic_probes_suspended": manifest.id in self.suspended,
            "available_routes": sum(bool((r := self.get(manifest, c.model_id)) and r.verdict.state == "free"
                                         and self.registry.billing.available(c.scope)) for c in rows),
            "probe_age_seconds": min((max(0, time.monotonic() - c.passed_at) for c in rows if c.passed_at is not None), default=None),
            "lease_remaining_seconds": min((max(0, c.passed_at + LEASE_SECONDS - time.monotonic()) for c in rows if c.active and c.passed_at is not None), default=None)}


def parse_account_catalog(registry, manifest, data):
    """Exact documented catalog rows; no prices or manual IDs certify an account."""
    from backend.app.core.discovery.orchestrator import CatalogFailure
    from backend.app.core.providers.models import DiscoveredModel
    if not account_bound(manifest) or not isinstance(data, dict) or not isinstance(data.get('data'), list):
        raise CatalogFailure('invalid_catalog')
    if any(data.get(k) for k in ('has_more', 'next_cursor', 'next')):
        raise CatalogFailure('incomplete_catalog')
    info = data.get('result_info', {})
    if isinstance(info, dict) and info.get('total_pages', 1) != 1:
        raise CatalogFailure('incomplete_catalog')
    if len(data['data']) > 1000:
        raise CatalogFailure('catalog_too_large')
    observed = {}
    routes = {}
    for item in data['data']:
        if not isinstance(item, dict):
            raise CatalogFailure('invalid_catalog')
        model = item.get('id')
        if not safe_id(model, registry):
            continue
        if model in observed:
            if observed[model] != item:
                raise CatalogFailure('conflicting_catalog')
            continue
        observed[model] = item
        if item.get('disabled') or ('active' in item and item['active'] is not True):
            continue
        caps = item.get('capabilities', {})
        if not isinstance(caps, dict) or caps.get('completion_chat') is False:
            continue
        if manifest.id == 'mistral' and caps.get('completion_chat') is not True:
            continue
        architecture = item.get('architecture', {})
        if not isinstance(architecture, dict):
            continue
        if 'output_modalities' in architecture and architecture['output_modalities'] != ['text']:
            continue
        if 'input_modalities' in architecture and (not isinstance(architecture['input_modalities'], list) or 'text' not in architecture['input_modalities']):
            continue
        rows = item.get('providers', []) if manifest.id == 'huggingface' else [None]
        if not isinstance(rows, list):
            raise CatalogFailure('invalid_catalog')
        seen_rows = {}
        for row in rows:
            identifier = model
            metadata = {k: item[k] for k in ('pricing', 'capabilities', 'architecture', 'disabled', 'active') if k in item}
            if manifest.id == 'nvidia_nim':
                from backend.app.core.discovery.nvidia import SOURCE_REVISION
                if item.get('nvidia_catalog_source') != SOURCE_REVISION:
                    continue
                metadata['nvidia_catalog_source'] = SOURCE_REVISION
            if manifest.id == 'huggingface':
                if ':' in model or not isinstance(row, dict):
                    raise CatalogFailure('invalid_route')
                provider = row.get('provider')
                if not isinstance(provider, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', provider) or provider in {'auto','fastest','cheapest','preferred'}:
                    raise CatalogFailure('invalid_route')
                if provider in seen_rows:
                    if seen_rows[provider] != row:
                        raise CatalogFailure('conflicting_catalog')
                    continue
                seen_rows[provider] = row
                if row.get('status') != 'live':
                    continue
                identifier = model + ':' + provider
                if not safe_id(identifier, registry):
                    continue
                metadata['route_provider'] = provider
                metadata['base_model_id'] = model
                metadata['capabilities'] = {'completion_chat': True, 'function_calling': row.get('supports_tools') is True}
                metadata['route_pricing'] = row.get('pricing')
                metadata['is_free_observed'] = row.get('is_free')
            try:
                context = int((row or {}).get('context_length', item.get('max_context_length', item.get('context_window', item.get('context_length',4096)))))
                if context <= 0: context = 4096
            except (ValueError, TypeError, OverflowError):
                context = 4096
            routes[identifier] = DiscoveredModel(id=identifier, provider_id=manifest.id,
                canonical_name=registry.canonical_name(manifest, model), context_window=context, metadata=metadata)
            if len(routes) > 1000:
                raise CatalogFailure('catalog_too_large')
    return len(observed), list(routes.values())
