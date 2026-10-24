"""Pure, bounded catalog projections and safe task health peeks."""
import time

from backend.app.core.eligibility.evidence import endpoint_identity
from backend.app.core.eligibility.account import LEASE_SECONDS
from backend.app.core.tasks.catalog import TASKS


def health(registry, row):
    """Read controller state without reserving, expiring or creating a scope."""
    if not registry.tasks.current(row):
        return "unknown"
    manifest = registry.get_manifest("openrouter")
    controller = registry.resilience
    identity = ("openrouter", registry.credential(manifest))
    route = controller.routes.get((row.scope, ("task", row.task, row.raw_id)))
    quota = controller.quotas.get(row.scope)
    if (controller.auth.get(identity, False) or not registry.billing.available(row.scope)
            or not controller._available(route) or not controller._available(quota)):
        return "blocked"
    return "available"


def _chat_rows(registry):
    """Project stored proofs only; account assertion methods have side effects."""
    now = time.monotonic()
    result = []
    for model in registry.get_models()[:1000]:
        if any(registry.is_private_identifier(v) for v in (model.id, model.canonical_name, model.provider_id)):
            continue
        manifest = registry.get_manifest(model.provider_id)
        stored = registry.eligibility._bindings.get(model.provider_id)
        if manifest is None:
            continue
        binding = (registry.credential(manifest), endpoint_identity(manifest), manifest.eligibility_profile,
                   manifest.models_endpoint, manifest.auth.type, manifest.auth.custom_header_name, manifest.auth.api_key_env)
        current = stored == binding and registry.profile_skip(manifest) is None
        evidence = registry.eligibility.records.get((model.provider_id, model.id))
        state, basis, reason, stamp, until, assurance, scope = "unknown", "none", "unverified", None, now, "provider_enforced", None
        if evidence:
            stamp, until, scope = evidence.observed_utc, evidence.expires_at, evidence.scope
            if current and now < until:
                state, basis, reason = evidence.verdict.state, evidence.verdict.basis, evidence.verdict.reason
        candidate = registry.accounts.candidates.get((model.provider_id, model.id))
        if candidate:
            assurance = "user_asserted"
            stamp, until, scope = candidate.source_utc, min(candidate.source_until, (candidate.passed_at or 0) + LEASE_SECONDS), candidate.scope
            assertion = registry.accounts.assertions.get(model.provider_id)
            if (current and assertion == scope and model.provider_id not in registry.accounts.revoked
                    and tuple(registry.settings.free_account_confirmations) == registry.accounts.confirmations
                    and candidate.active and registry.accounts.healthy(candidate, now) and now < candidate.source_until
                    and model.provider_id not in registry.accounts.suspended):
                state, basis, reason = "free", "user_confirmed_account_probe", "account_asserted_available"
        availability = "unknown"
        if state == "free" and scope is not None:
            controller = registry.resilience
            identity = (manifest.id, registry.credential(manifest))
            availability = "blocked" if (not registry.billing.available(scope) or controller.auth.get(identity, False)
                or not controller._available(controller.quotas.get(scope))
                or not controller._available(controller.routes.get((scope, model.id)))) else "available"
        result.append({"id": model.canonical_name, "task": "chat", "provider_id": model.provider_id,
            "eligibility": state, "basis": basis, "reason": reason, "assurance": assurance,
            "observed_at": stamp, "expires_in_seconds": max(0, round(until - now, 3)),
            "health": availability, "capabilities": {}})
    return result


def inventory(registry, task):
    result = registry.tasks.inventory(task) if task != "chat" else {"object": "list", "data": [], "tasks": []}
    for row in result["data"]:
        item = registry.tasks.get(row["task"], row["id"])
        row["health"] = health(registry, item)
    if task in {"all", "chat"}:
        chat = _chat_rows(registry)
        result["data"].extend(chat)
        result["tasks"].insert(0, {"task": "chat", "inventory_state": "succeeded" if chat else "unverified",
            "eligible_count": sum(row["eligibility"] == "free" and row["health"] != "blocked" for row in chat),
            "live_delivery": "unverified"})
    result["data"].sort(key=lambda row: (row["task"], row["provider_id"], row["id"]))
    return result
