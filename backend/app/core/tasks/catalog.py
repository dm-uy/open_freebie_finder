"""Task-specific immutable source snapshots; visibility never implies admission.

Only publication mutates evidence. Public reads deliberately avoid the chat
EligibilityStore's scope resolver, whose epoch maintenance has side effects.
"""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import time
import unicodedata

from backend.app.core.eligibility.evidence import Verdict, decimal, endpoint_identity, openrouter_bound, source_verdict

TASKS = ("embeddings", "rerank", "decisions", "speech")
SOURCE_PATHS = {task: ("/api/v1/embeddings/models" if task == "embeddings"
                       else "/api/v1/models?output_modalities=" + task) for task in TASKS}
DISPATCH_PATHS = {"embeddings": "/api/v1/embeddings", "rerank": "/api/v1/rerank",
                  "decisions": "/api/alpha/decisions", "speech": "/api/v1/audio/speech"}
PROFILE_REVISION = "task_strict_v1"
MAX_ROWS = 1000


class CatalogError(ValueError):
    """A bounded source could not be used as a complete task inventory."""
    def __init__(self, code="invalid_catalog"):
        self.code = code
        super().__init__("Task catalog unavailable.")


def policy(task):
    """Return fresh owned routing controls; no chat omitted-fee exception."""
    if task not in {"embeddings", "decisions"}:
        return None
    return {"max_price": {"prompt": "0", "completion": "0", "request": "0"},
            "require_parameters": True}


def _identifier(value, limit=512):
    return (isinstance(value, str) and 1 <= len(value) <= limit and bool(value.strip())
            and not any(unicodedata.category(c).startswith("C") for c in value))


@dataclass(frozen=True, repr=False)
class TaskRow:
    task: str
    raw_id: str
    scope: tuple
    binding: tuple
    verdict: Verdict
    observed_at: float
    expires_at: float
    observed_utc: str
    source_revision: str
    # Immutable key/value pairs; a caller cannot widen a snapshot by mutation.
    _capabilities: tuple = ()

    @property
    def public_id(self):
        return "openrouter::" + self.raw_id

    @property
    def state(self):
        return self.verdict.state

    @property
    def reason(self):
        return self.verdict.reason

    @property
    def basis(self):
        return self.verdict.basis

    @property
    def capabilities(self):
        return {key: list(value) if isinstance(value, tuple) else value
                for key, value in self._capabilities}


class TaskCatalog:
    def __init__(self, registry):
        self.registry = registry
        self.rows = {}
        self.states = {task: "unverified" for task in TASKS}

    def binding(self, task):
        """Pure captured source/credential/profile/policy identity; never serialize."""
        manifest = self.registry.get_manifest("openrouter")
        if task not in TASKS or manifest is None or self.registry.eligibility.source is not source_verdict:
            return None
        if not openrouter_bound(manifest) or self.registry.profile_skip(manifest):
            return None
        key = self.registry.credential(manifest)
        if not isinstance(key, str) or not key or not key.isascii() or any(c in key for c in "\r\n"):
            return None
        return (task, manifest.id, key, manifest.base_url, manifest.models_endpoint,
                manifest.eligibility_profile, manifest.auth.type, manifest.auth.api_key_env,
                manifest.auth.custom_header_name, SOURCE_PATHS[task], DISPATCH_PATHS[task],
                PROFILE_REVISION, json.dumps(policy(task), sort_keys=True))

    def _safe_identifier(self, value, limit=512):
        return _identifier(value, limit) and not self.registry.is_private_identifier(value)

    def _safe_model_id(self, value):
        return (self._safe_identifier(value)
                and not self.registry.is_private_identifier("openrouter::" + value)
                and not self.registry.is_private_identifier("openrouter"))

    def _verdict(self, task, item):
        architecture = item.get("architecture")
        if not isinstance(architecture, dict):
            return Verdict(reason="invalid_evidence")
        inputs, outputs = architecture.get("input_modalities"), architecture.get("output_modalities")
        if (not isinstance(inputs, list) or not all(isinstance(v, str) for v in inputs)
                or "text" not in inputs or outputs != [task]):
            return Verdict(reason="invalid_evidence")
        capabilities = item.get("capabilities")
        if item.get("disabled") or (isinstance(capabilities, dict) and capabilities.get(task) is False):
            return Verdict(reason="invalid_evidence")
        if task in {"rerank", "speech"} or policy(task) is None:
            return Verdict(reason="unsupported_enforcement")
        prices = item.get("pricing")
        required = {"prompt", "completion", "request"}
        if not isinstance(prices, dict) or set(prices) != required:
            return Verdict(reason="price_scope_unknown")
        try:
            values = [decimal(value) for value in prices.values()
                      if not isinstance(value, str) or len(value) <= 128]
            if len(values) != 3:
                raise ValueError
        except (ValueError, OverflowError):
            return Verdict(reason="invalid_evidence")
        if any(value > 0 for value in values):
            return Verdict("paid", "catalog_effective_price", "paid")
        return Verdict("free", "catalog_effective_price", "free_verified")

    def _capabilities(self, task, item):
        # No source mapping currently establishes supported dimensions/formats.
        # Do not manufacture them from examples or optional input parameters.
        result = [("revision", None)]
        if task == "speech":
            voices = item.get("supported_voices")
            if isinstance(voices, list) and len(voices) <= 1000:
                safe = sorted({voice for voice in voices if self._safe_identifier(voice, 128)})
                result.append(("voices", tuple(safe)))
        return tuple(result)

    def publish(self, task, data, expected_binding):
        """Atomically replace exactly one task after validating the whole source."""
        if task not in TASKS:
            raise CatalogError("unsupported_profile")
        if expected_binding is None or self.binding(task) != expected_binding:
            return False
        try:
            if not isinstance(data, dict) or not isinstance(data.get("data"), list):
                raise CatalogError()
            if any(data.get(key) for key in ("has_more", "next_cursor", "next", "next_page", "pagination", "next_offset", "cursor")):
                raise CatalogError("incomplete_catalog")
            info = data.get("result_info")
            if isinstance(info, dict):
                try:
                    if int(info.get("total_pages", 1)) > int(info.get("page", 1)):
                        raise CatalogError("incomplete_catalog")
                except (ValueError, TypeError, OverflowError):
                    raise CatalogError() from None
            entries = data["data"]
            for name in ("total", "total_count"):
                if name in data:
                    if type(data[name]) is not int or data[name] < 0:
                        raise CatalogError()
                    if data[name] > len(entries):
                        raise CatalogError("incomplete_catalog")
            if len(entries) > MAX_ROWS:
                raise CatalogError("response_too_large")
            manifest = self.registry.get_manifest("openrouter")
            scope = self.registry.eligibility.scope(manifest)
            now = time.monotonic()
            stamp = datetime.now(timezone.utc).isoformat()
            pending, observed = {}, {}
            for item in entries:
                if not isinstance(item, dict):
                    raise CatalogError()
                raw_id = item.get("id")
                if not self._safe_model_id(raw_id):
                    continue
                if raw_id in observed:
                    if observed[raw_id] != item:
                        pending.pop((task, raw_id), None)
                    continue
                observed[raw_id] = item
                verdict = self._verdict(task, item)
                capabilities = self._capabilities(task, item)
                # Hash normalized public interpretation, never arbitrary provider
                # descriptions or response data that may echo a supplied key.
                normalized = {"id": raw_id, "task": task, "state": verdict.state,
                              "reason": verdict.reason, "capabilities": capabilities}
                revision = hashlib.sha256(json.dumps(normalized, sort_keys=True,
                    separators=(",", ":")).encode()).hexdigest()
                pending[(task, raw_id)] = TaskRow(task, raw_id, scope, expected_binding,
                    verdict, now, now + self.registry.settings.eligibility_ttl_seconds,
                    stamp, revision, capabilities)
            # The key/profile may have changed through a resolver hook during parsing.
            if self.binding(task) != expected_binding:
                return False
            self.rows = {key: row for key, row in self.rows.items() if key[0] != task}
            self.rows.update(pending)
            self.states[task] = "succeeded"
            return True
        except CatalogError:
            self.clear(task)
            raise

    def clear(self, task, reason="source_unavailable"):
        if task not in TASKS:
            return
        allowed = {"source_unavailable", "unsupported_profile", "source_changed"}
        reason = reason if reason in allowed else "source_unavailable"
        now = time.monotonic()
        self.rows = {key: (replace(row, verdict=Verdict(reason=reason)) if key[0] == task else row)
                     for key, row in self.rows.items()
                     if key[0] != task or now < row.expires_at}
        self.states[task] = "failed"

    def _current_at(self, row, now):
        if not isinstance(row, TaskRow) or self.rows.get((row.task, row.raw_id)) is not row:
            return False
        manifest = self.registry.get_manifest("openrouter")
        if manifest is None or self.binding(row.task) != row.binding or now >= row.expires_at:
            return False
        epoch = self.registry.eligibility._epochs.get(manifest.id, 0)
        scope = (manifest.id, endpoint_identity(manifest), epoch, manifest.eligibility_profile)
        return row.scope == scope and self._safe_model_id(row.raw_id)

    def current(self, row):
        return self._current_at(row, time.monotonic())

    def _eligible_at(self, row, now):
        return (self._current_at(row, now) and row.state == "free" and policy(row.task) is not None
                and self.registry.billing.available(row.scope))

    def eligible(self, row):
        return self._eligible_at(row, time.monotonic())

    def get(self, task, public_id):
        if task not in TASKS or not isinstance(public_id, str) or not public_id.startswith("openrouter::"):
            return None
        prefix, raw_id = public_id.split("::", 1)
        if prefix != "openrouter" or not self._safe_model_id(raw_id):
            return None
        return self.rows.get((task, raw_id))

    def eligible_rows(self, task):
        return [row for (kind, _), row in sorted(self.rows.items()) if kind == task and self.eligible(row)]

    def diagnostic(self, row, health="unknown", *, now=None):
        if not self._safe_model_id(row.raw_id):
            raise CatalogError()
        now = time.monotonic() if now is None else now
        current = self._current_at(row, now)
        reason = row.reason if current else ("expired" if now >= row.expires_at else "source_unavailable")
        capabilities = row.capabilities
        if "voices" in capabilities:
            capabilities["voices"] = [voice for voice in capabilities["voices"] if self._safe_identifier(voice, 128)]
        return {"id": row.public_id, "task": row.task, "provider_id": "openrouter",
                "eligibility": row.state if current else "unknown", "basis": row.basis if current else "none",
                "reason": reason, "assurance": row.verdict.assurance,
                "observed_at": row.observed_utc, "expires_in_seconds": max(0, round(row.expires_at - now, 3)),
                "health": health if health in {"available", "blocked", "unknown"} else "unknown",
                "capabilities": capabilities}

    def inventory(self, task="all"):
        kinds = TASKS if task == "all" else (task,)
        now = time.monotonic()
        snapshot = sorted(self.rows.items())
        data = [self.diagnostic(row, now=now) for (kind, _), row in snapshot
                if kind in kinds and self._safe_model_id(row.raw_id)
                and not (row.reason == "source_unavailable" and now >= row.expires_at)]
        return {"object": "list", "data": data, "tasks": [
            {"task": kind, "inventory_state": self.states.get(kind, "unverified"),
             "eligible_count": sum(self._eligible_at(row, now) for (which, _), row in snapshot if which == kind),
             "live_delivery": "unverified"} for kind in kinds]}
