"""Explicit trusted synthetic evidence for pre-existing controlled routing scenarios.

This is test setup only, never a production manifest attestation mechanism.
"""
from backend.app.core.eligibility.evidence import Verdict, decimal


def fixture_source(manifest, item):
    pricing = item.get("pricing")
    if manifest.discovery.type == "openrouter_free" and pricing is None:
        return Verdict(reason="price_scope_unknown")
    if pricing is not None:
        try:
            if any(decimal(pricing[k]) > 0 for k in ("prompt", "completion")):
                return Verdict("paid", "catalog_effective_price", "paid")
        except (ValueError, KeyError, TypeError):
            return Verdict(reason="invalid_evidence")
    if item.get("capabilities", {}).get("completion_chat") is False:
        return Verdict(reason="invalid_evidence")
    return Verdict("free", "account_free_only", "free_verified", True)


def install_fixture_evidence(registry):
    registry.eligibility.source = fixture_source
    original = registry.register_models

    async def register(models, provider_id=None):
        await original(models, provider_id)
        for provider in {m.provider_id for m in models}:
            manifest = registry.get_manifest(provider)
            if manifest:
                registry.eligibility.publish(manifest, {m.id:{"pricing":{"prompt":0,"completion":0,"request":0}, **m.metadata} for m in models if m.provider_id == provider},
                    registry.eligibility.scope(manifest))
                for model in models:
                    record = registry.eligibility.get(manifest, model.id)
                    if model.provider_id == provider:
                        model.is_free = bool(record and record.verdict.state == "free")
    registry.register_models = register
    return registry
