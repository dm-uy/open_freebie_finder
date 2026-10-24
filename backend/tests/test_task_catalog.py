"""Production task admission boundaries, independent snapshots and pure reads."""
from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest

from backend.app.config import Settings
from backend.app.core.providers.models import DiscoveredModel, ProviderManifest
from backend.app.core.providers.registry import ProviderRegistry
from backend.app.core.tasks.catalog import CatalogError, TaskCatalog, TASKS, policy


def profile():
    return ProviderManifest(id="openrouter", name="Fixture", base_url="https://openrouter.ai/api/v1",
        models_endpoint="https://openrouter.ai/api/v1/models",
        auth={"type": "bearer", "api_key_env": "FIXTURE_TASK_CATALOG_KEY"},
        eligibility_profile="openrouter_zero_price")


def item(task="embeddings", identifier="shared", **changes):
    result = {"id": identifier, "architecture": {"input_modalities": ["text"], "output_modalities": [task]},
              "pricing": {"prompt": "0", "completion": "0e-9", "request": 0}}
    result.update(changes)
    return result


@pytest.fixture
def catalog(monkeypatch):
    monkeypatch.setenv("FIXTURE_TASK_CATALOG_KEY", "catalog-private-sentinel")
    registry = ProviderRegistry(settings=Settings(_env_file=None), manifests=[profile()])
    return TaskCatalog(registry)


def publish(catalog, task="embeddings", **changes):
    assert catalog.publish(task, {"data": [item(task, **changes)]}, catalog.binding(task))
    return catalog.get(task, "openrouter::" + changes.get("identifier", "shared"))


def test_strict_prices_never_inherit_chat_exception(catalog):
    row = publish(catalog)
    assert row.state == "free" and catalog.eligible(row)
    for prices, state, reason in [
        ({"prompt": 0, "completion": 0}, "unknown", "price_scope_unknown"),
        ({"prompt": 0, "completion": 0, "request": 0, "input_cache_read": 0}, "unknown", "price_scope_unknown"),
        ({"prompt": 0, "completion": 0, "request": True}, "unknown", "invalid_evidence"),
        ({"prompt": 0, "completion": 0, "request": "NaN"}, "unknown", "invalid_evidence"),
        ({"prompt": 0, "completion": 0, "request": -1}, "unknown", "invalid_evidence"),
        ({"prompt": 0, "completion": 0, "request": "0.01"}, "paid", "paid"),
    ]:
        row = publish(catalog, pricing=prices)
        assert (row.state, row.reason) == (state, reason)
        assert not catalog.eligible_rows("embeddings")
    for task in ("rerank", "speech"):
        row = publish(catalog, task)
        assert (row.state, row.reason) == ("unknown", "unsupported_enforcement")
        assert not catalog.eligible(row)


def test_owned_policy_is_independent_and_loss_revokes(catalog, monkeypatch):
    first = policy("embeddings")
    first["max_price"]["request"] = "4"
    assert policy("embeddings")["max_price"]["request"] == "0"
    assert policy("speech") is None
    row = publish(catalog)
    monkeypatch.setattr("backend.app.core.tasks.catalog.policy", lambda task: None)
    assert not catalog.current(row) and not catalog.eligible(row)


def test_task_architecture_and_negative_capability_are_binding(catalog):
    for changes in ({"architecture": {"input_modalities": ["text"], "output_modalities": ["embeddings", "audio"]}},
                    {"architecture": {"input_modalities": ["image"], "output_modalities": ["embeddings"]}},
                    {"disabled": True}, {"capabilities": {"embeddings": False}}):
        row = publish(catalog, **changes)
        assert row.state == "unknown" and not catalog.eligible(row)


@pytest.mark.asyncio
async def test_task_refresh_never_replaces_chat_or_other_tasks(catalog):
    registry = catalog.registry
    chat = DiscoveredModel(id="chat", provider_id="openrouter", canonical_name="chat")
    await registry.register_models([chat], provider_id="openrouter")
    chat_models, chat_times = registry.get_models(), deepcopy(registry._snapshot_times)
    embedding = publish(catalog)
    decision = publish(catalog, "decisions")
    assert embedding.raw_id == decision.raw_id and embedding.task != decision.task
    catalog.clear("embeddings")
    assert not catalog.eligible(catalog.get("embeddings", embedding.public_id))
    assert catalog.eligible(decision)
    assert registry.get_models() == chat_models and registry._snapshot_times == chat_times
    assert catalog.publish("embeddings", {"data": []}, catalog.binding("embeddings"))
    assert catalog.get("embeddings", embedding.public_id) is None
    assert catalog.get("decisions", decision.public_id) is decision


def test_reads_are_pure_and_expiry_does_not_renew(catalog, monkeypatch):
    clock = [10.0]
    monkeypatch.setattr("backend.app.core.tasks.catalog.time.monotonic", lambda: clock[0])
    row = publish(catalog)
    registry = catalog.registry
    snapshots = (deepcopy(registry.eligibility._bindings), deepcopy(registry.eligibility._epochs),
                 deepcopy(registry.eligibility.records), dict(catalog.rows), dict(catalog.states))
    for _ in range(3):
        assert catalog.get("embeddings", row.public_id) is row
        assert catalog.current(row) and catalog.eligible(row)
        catalog.inventory()
    assert snapshots == (registry.eligibility._bindings, registry.eligibility._epochs,
                          registry.eligibility.records, catalog.rows, catalog.states)
    clock[0] = row.expires_at
    assert not catalog.current(row) and not catalog.eligible_rows("embeddings")
    assert catalog.diagnostic(row)["reason"] == "expired"
    assert row.expires_at == 130.0


def test_failure_revokes_without_extending_diagnostic_retention(catalog, monkeypatch):
    clock = [10.0]
    monkeypatch.setattr("backend.app.core.tasks.catalog.time.monotonic", lambda: clock[0])
    row = publish(catalog)
    clock[0] = 20
    catalog.clear("embeddings")
    held = catalog.get("embeddings", row.public_id)
    assert held.expires_at == row.expires_at and held.observed_at == row.observed_at
    assert held.state == "unknown" and held.reason == "source_unavailable"
    assert not catalog.current(row)
    clock[0] = row.expires_at
    catalog.clear("embeddings")
    assert not catalog.inventory("embeddings")["data"]


def test_old_fetch_cannot_publish_new_credential_or_changed_source(catalog, monkeypatch):
    old = catalog.binding("embeddings")
    row = publish(catalog)
    monkeypatch.setenv("FIXTURE_TASK_CATALOG_KEY", "different-catalog-sentinel")
    assert not catalog.current(row)
    assert not catalog.publish("embeddings", {"data": [item()]}, old)
    changed = catalog.binding("embeddings")
    assert changed != old
    assert catalog.publish("embeddings", {"data": [item(identifier="new")]}, changed)
    assert catalog.eligible_rows("embeddings")[0].raw_id == "new"
    catalog.registry.get_manifest("openrouter").models_endpoint += "?attacker=1"
    assert catalog.binding("embeddings") is None
    assert not catalog.eligible_rows("embeddings")


def test_epoch_change_revokes_even_if_key_restored(catalog, monkeypatch):
    row = publish(catalog)
    manifest = catalog.registry.get_manifest("openrouter")
    monkeypatch.setenv("FIXTURE_TASK_CATALOG_KEY", "changed-key")
    catalog.registry.eligibility.scope(manifest)
    monkeypatch.setenv("FIXTURE_TASK_CATALOG_KEY", "catalog-private-sentinel")
    catalog.registry.eligibility.scope(manifest)
    assert not catalog.current(row)


@pytest.mark.parametrize("data", [
    {"data": "bad"}, {"data": [None]}, {"data": [], "has_more": True},
    {"data": [], "next_cursor": "next"}, {"data": [], "result_info": {"total_pages": 2, "page": 1}},
    {"data": [item(identifier=str(n)) for n in range(1001)]},
])
def test_malformed_incomplete_and_overflow_fail_closed(catalog, data):
    row = publish(catalog)
    with pytest.raises(CatalogError):
        catalog.publish("embeddings", data, catalog.binding("embeddings"))
    assert not catalog.eligible_rows("embeddings")
    assert catalog.get("embeddings", row.public_id).state == "unknown"


def test_conflicting_duplicates_cannot_certify_first_wins(catalog):
    first = item()
    bad = item(pricing={"prompt": 1, "completion": 0, "request": 0})
    assert catalog.publish("embeddings", {"data": [first, first, bad, first]}, catalog.binding("embeddings"))
    assert not catalog.eligible_rows("embeddings")


def test_secrets_controls_and_untrusted_metadata_do_not_escape(catalog):
    data = [item(identifier="catalog-private-sentinel/model"), item(identifier="model\nforged"),
            item("speech", supported_voices=["safe-voice", "catalog-private-sentinel", "bad\rvoice"],
                 description="private description", arbitrary="private metadata")]
    assert catalog.publish("speech", {"data": data}, catalog.binding("speech"))
    result = catalog.inventory()
    text = str(result)
    assert "catalog-private-sentinel" not in text and "description" not in text and "metadata" not in text
    assert len(result["data"]) == 1
    assert result["data"][0]["capabilities"]["voices"] == ["safe-voice"]
    assert set(result["data"][0]) == {"id", "task", "provider_id", "eligibility", "basis", "reason", "assurance",
                                      "observed_at", "expires_in_seconds", "health", "capabilities"}


def test_snapshot_cannot_be_widened_via_capability_alias(catalog):
    row = publish(catalog, "speech", supported_voices=["safe-voice"])
    row.capabilities["voices"].append("injected")
    assert row.capabilities["voices"] == ["safe-voice"]
    with pytest.raises(FrozenInstanceError):
        row.raw_id = "changed"


def test_financial_guard_is_shared_and_never_grants_eligibility(catalog):
    row = publish(catalog)
    assert catalog.eligible(row)
    catalog.registry.billing.hold(row.scope, "unexpected_paid_cost")
    assert not catalog.eligible(row)
    catalog.clear("embeddings")
    assert catalog.registry.billing.holds[row.scope].expires_at is None


def test_unbound_or_missing_profile_cannot_produce_binding(catalog, monkeypatch):
    manifest = catalog.registry.get_manifest("openrouter")
    monkeypatch.delenv("FIXTURE_TASK_CATALOG_KEY")
    assert catalog.binding("embeddings") is None
    monkeypatch.setenv("FIXTURE_TASK_CATALOG_KEY", "restored-key")
    manifest.base_url = "https://other.invalid/api/v1"
    assert catalog.binding("embeddings") is None
    assert catalog.binding("not-a-task") is None
    assert catalog.get("embeddings", "auto:free") is None


def test_guarded_inventory_count_matches_public_admission(catalog):
    row = publish(catalog)
    assert catalog.inventory("embeddings")["tasks"][0]["eligible_count"] == 1
    catalog.registry.billing.hold(row.scope, "unexpected_paid_cost")
    result = catalog.inventory("embeddings")
    assert result["data"][0]["eligibility"] == "free"
    assert result["tasks"][0]["eligible_count"] == 0


def test_newly_configured_secret_never_leaks_from_old_voice_metadata(catalog, monkeypatch):
    row = publish(catalog, "speech", supported_voices=["later-secret"])
    monkeypatch.setenv("FIXTURE_TASK_CATALOG_KEY", "later-secret")
    assert catalog.diagnostic(row)["capabilities"]["voices"] == []
    assert "later-secret" not in str(catalog.inventory())


@pytest.mark.parametrize("extra", [{"next_offset": 1000}, {"total_count": 2}, {"total": "unknown"}])
def test_additional_incomplete_page_signals_revoke_catalog(catalog, extra):
    row = publish(catalog)
    with pytest.raises(CatalogError):
        catalog.publish("embeddings", {"data": [item()], **extra}, catalog.binding("embeddings"))
    assert not catalog.eligible(row)


def test_failed_source_diagnostics_do_not_outlive_original_ttl(catalog, monkeypatch):
    row = publish(catalog)
    catalog.clear("embeddings")
    assert len(catalog.inventory("embeddings")["data"]) == 1
    monkeypatch.setattr("backend.app.core.tasks.catalog.time.monotonic", lambda: row.expires_at)
    assert catalog.inventory("embeddings")["data"] == []
