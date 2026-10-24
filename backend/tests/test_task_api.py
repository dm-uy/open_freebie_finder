"""Task views/auth preserve chat defaults and never perform provider I/O."""
import copy

import httpx
import pytest

from backend.app.main import create_app
from backend.tests.task_fixtures import registry, publish


@pytest.mark.asyncio
async def test_task_catalog_separation_auth_and_no_mutation(monkeypatch):
    store = registry(monkeypatch, "fixture-master")
    publish(store)
    publish(store, "speech")
    before = (dict(store.tasks.rows), copy.deepcopy(store.eligibility._epochs),
              copy.deepcopy(store.resilience.snapshot()), dict(store.billing.holds))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(store)), base_url="http://fixture") as client:
        chat = (await client.get("/v1/models")).json()
        assert [row["id"] for row in chat["data"]] == ["auto:free"]
        assert (await client.get("/v1/models?task=chat")).json()["data"] == chat["data"]
        assert [row["id"] for row in (await client.get("/v1/models?task=embeddings")).json()["data"]] == ["openrouter::fixture-model"]
        assert (await client.get("/v1/models?task=speech")).json()["data"] == []
        denied = await client.get("/api/admin/models/catalog?task=bad")
        assert denied.status_code == 401
        result = await client.get("/api/admin/models/catalog", headers={"Authorization": "Bearer fixture-master"})
        assert result.status_code == 200
        rows = result.json()["data"]
        assert {row["task"] for row in rows} == {"embeddings", "speech"}
        assert next(row for row in rows if row["task"] == "speech")["reason"] == "unsupported_enforcement"
        for suffix in ("task=all", "task=bad", "task=chat&task=speech", "unknown=fixture-master"):
            response = await client.get("/v1/models?" + suffix)
            assert response.status_code == 400
            assert "fixture-master" not in response.text
    assert before == (dict(store.tasks.rows), copy.deepcopy(store.eligibility._epochs),
                      copy.deepcopy(store.resilience.snapshot()), dict(store.billing.holds))


@pytest.mark.asyncio
@pytest.mark.parametrize("when", ["publication", "after-publication"])
async def test_final_public_catalog_id_cannot_be_a_configured_credential(monkeypatch, when):
    store = registry(monkeypatch)
    sentinel = "openrouter::fixture-model"
    if when == "publication":
        monkeypatch.setenv("TASK_FIXTURE_KEY", sentinel)
        publish(store)
    else:
        publish(store)
        # A different configured secret can rotate without the source key changing.
        store.settings.proxy_master_key = sentinel
    async with httpx.AsyncClient(transport=httpx.ASGITransport(create_app(store)), base_url="http://fixture") as client:
        public = await client.get("/v1/models?task=embeddings")
        admin = await client.get("/api/admin/models/catalog", headers={"Authorization": "Bearer " + sentinel})
    assert public.status_code == admin.status_code == 200
    assert sentinel not in public.text and sentinel not in admin.text
    assert public.json()["data"] == []
