"""Memory-only, credential-bound evidence; no catalog or operator attestation implies free."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import time
from typing import Callable, Literal
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Verdict:
    state: Literal["free", "paid", "unknown"] = "unknown"
    basis: str = "none"
    reason: str = "unsupported_eligibility"
    tools: bool = False
    assurance: str = "provider_enforced"


@dataclass(frozen=True, repr=False)
class Evidence:
    scope: tuple
    verdict: Verdict
    observed_at: float
    expires_at: float
    observed_utc: str
    source_id: str
    covered_profile: str = "text_chat_v1"
    source_revision: str | None = None


def decimal(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("Invalid monetary value.")
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0:
            raise ValueError
        return result
    except (InvalidOperation, ValueError):
        raise ValueError("Invalid monetary value.") from None


def endpoint_identity(manifest):
    url = urlsplit(manifest.base_url)
    try:
        port = url.port
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment:
            return None
        if any(c.isspace() for c in manifest.base_url) or "{" in manifest.base_url:
            return None
        path = url.path.rstrip("/")
        if not path.endswith("/chat/completions"):
            path += "/chat/completions"
        return (url.scheme.lower(), url.hostname.lower(), port or (443 if url.scheme == "https" else 80), path)
    except ValueError:
        return None


def openrouter_bound(manifest):
    return (manifest.eligibility_profile == "openrouter_zero_price"
            and endpoint_identity(manifest) == ("https", "openrouter.ai", 443, "/api/v1/chat/completions")
            and manifest.models_endpoint == "https://openrouter.ai/api/v1/models"
            and manifest.auth.type == "bearer")


def source_verdict(manifest, item):
    if not openrouter_bound(manifest):
        reason = ("enforcement_unverified" if manifest.id == "nvidia_nim" else
                  "account_evidence_unavailable" if manifest.id in {"groq", "mistral", "huggingface"} else
                  "unsupported_eligibility")
        return Verdict(reason=reason)
    architecture = item.get("architecture")
    if not isinstance(architecture, dict) or any(not isinstance(architecture.get(k), list) or "text" not in architecture[k]
                                               for k in ("input_modalities", "output_modalities")):
        return Verdict(reason="invalid_evidence")
    # Merely advertising text alongside audio/image does not prove that this
    # closed text-chat profile can suppress the other output or its charges.
    # In particular, music endpoints advertise zero token prices plus text+audio.
    if architecture["output_modalities"] != ["text"]:
        return Verdict(reason="unsupported_output_modality")
    capabilities = item.get("capabilities")
    if item.get("disabled") or (isinstance(capabilities, dict) and capabilities.get("completion_chat") is False):
        return Verdict(reason="invalid_evidence")
    prices = item.get("pricing")
    if not isinstance(prices, dict) or not {"prompt", "completion"} <= prices.keys():
        return Verdict(reason="price_scope_unknown")
    # Catalog prices use dollars per token/request. Unknown components are never
    # silently ignored; nontext image/audio fees are outside the covered profile.
    known = {"prompt", "completion", "request", "image", "web_search", "internal_reasoning",
             "input_cache_read", "input_cache_write", "audio", "input_audio_cache"}
    if prices.keys() - known:
        return Verdict(reason="price_scope_unknown")
    try:
        applicable = [decimal(v) for k, v in prices.items() if k not in {"image", "audio", "input_audio_cache"}]
    except ValueError:
        return Verdict(reason="invalid_evidence")
    if any(value > 0 for value in applicable):
        return Verdict("paid", "catalog_effective_price", "paid")
    supported = item.get("supported_parameters", [])
    tools = isinstance(supported, list) and {"tools", "tool_choice"} <= set(v for v in supported if isinstance(v, str))
    if "request" not in prices:
        return Verdict("free", "catalog_zero_tokens_with_request_ceiling", "free_enforced", tools)
    return Verdict("free", "catalog_effective_price", "free_verified", tools)


class EligibilityStore:
    """No persisted credentials/fingerprints; epochs track observed resolver changes."""
    def __init__(self, registry, source: Callable | None = None):
        self.registry = registry
        self.source = source or source_verdict
        self.records: dict[tuple[str, str], Evidence] = {}
        self._bindings = {}
        self._epochs = {}

    def scope(self, manifest):
        # Never serialize this binding or provide its repr to a logger.
        binding = (self.registry.credential(manifest), endpoint_identity(manifest), manifest.eligibility_profile,
                   manifest.models_endpoint, manifest.auth.type, manifest.auth.custom_header_name, manifest.auth.api_key_env)
        if self._bindings.get(manifest.id) != binding:
            self._bindings[manifest.id] = binding
            self._epochs[manifest.id] = self._epochs.get(manifest.id, 0) + 1
            self.clear(manifest.id)
            if hasattr(self.registry, "accounts"):
                self.registry.accounts.changed(manifest.id)
        return (manifest.id, binding[1], self._epochs.get(manifest.id, 0), manifest.eligibility_profile)

    def clear(self, provider_id):
        if hasattr(self.registry, "accounts"):
            self.registry.accounts.invalidate_source(provider_id)
        self.records = {k: v for k, v in self.records.items() if k[0] != provider_id}

    def prune(self):
        ids = {p.id for p in self.registry.get_manifests()}
        self.records = {k:v for k,v in self.records.items() if k[0] in ids}
        for key in set(self._bindings) - ids:
            self._bindings.pop(key, None)
            self._epochs.pop(key, None)

    def publish(self, manifest, observations, expected_scope):
        if self.scope(manifest) != expected_scope:
            return False
        from backend.app.core.eligibility.account import account_profile
        if account_profile(manifest) and self.source is source_verdict:
            return self.registry.accounts.publish(manifest, observations, expected_scope)
        now = time.monotonic()
        stamp = datetime.now(timezone.utc).isoformat()
        pending = {}
        for model_id, item in list(observations.items())[:1000]:
            verdict = self.source(manifest, item)
            pending[(manifest.id, model_id)] = Evidence(expected_scope, verdict, now,
                now + self.registry.settings.eligibility_ttl_seconds, stamp,
                "openrouter_zero_price" if openrouter_bound(manifest) else "unsupported_eligibility")
        self.clear(manifest.id)
        self.records.update(pending)
        return True

    def get(self, manifest, model_id):
        from backend.app.core.eligibility.account import account_profile
        if account_profile(manifest) and self.source is source_verdict:
            return self.registry.accounts.get(manifest, model_id)
        scope = self.scope(manifest)
        record = self.records.get((manifest.id, model_id))
        if record is None or record.scope != scope or time.monotonic() >= record.expires_at:
            return None
        return record

    def diagnostics(self, manifest):
        from backend.app.core.eligibility.account import account_profile
        if account_profile(manifest) and self.source is source_verdict:
            return self.registry.accounts.diagnostics(manifest)
        self.scope(manifest)
        counts = {"free": 0, "paid": 0, "unknown": 0}
        reasons = {}
        for (provider, model), record in self.records.items():
            if provider != manifest.id:
                continue
            expired = time.monotonic() >= record.expires_at
            counts["unknown" if expired else record.verdict.state] += 1
            reason = "expired" if expired else record.verdict.reason
            reasons[reason] = reasons.get(reason, 0) + 1
        matching = [r for (p, _), r in self.records.items() if p == manifest.id]
        return {"states": counts, "reasons": reasons,
            "bases": sorted({r.verdict.basis for r in matching}),
            "source_ids": sorted({r.source_id for r in matching}),
            "observed_at": min((r.observed_utc for r in matching),default=None),
            "expires_in_seconds": min((max(0,round(r.expires_at-time.monotonic(),3)) for r in matching),default=None)}
