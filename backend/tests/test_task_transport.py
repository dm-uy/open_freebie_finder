"""Exact-route delivery and cross-task/account races; no external requests."""
import asyncio
from dataclasses import replace
import json

import httpx
import pytest

from backend.app.main import create_app
from backend.app.core.tasks.transport import TaskExecutor, TaskError
from backend.app.core.tasks.catalog import policy
from backend.app.core.eligibility.evidence import Verdict
from backend.app.core.balancer.resilience import HealthOutcome
from backend.tests.task_fixtures import registry, publish


def vector(raw="fixture-model", **changes):
    return {"object": "list", "model": raw, "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}], **changes}


@pytest.mark.asyncio
async def test_exact_embedding_and_owned_policy_every_send(monkeypatch):
    store = registry(monkeypatch)
    row = publish(store)
    seen = []
    def upstream(request):
        seen.append(request)
        assert json.loads(request.content)["provider"] == policy("embeddings")
        return httpx.Response(200, json=vector(usage={"prompt_tokens": 1, "cost": "not-a-monetary-proof"}, private="hidden"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(upstream), headers={"Host": "ambient.invalid"},
                                 auth=("ambient", "password"), cookies={"private": "cookie"}) as provider:
        executor = TaskExecutor(store, provider)
        app = create_app(store); app.state.task_executor = executor
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://fixture") as client:
            response = await client.post("/v1/embeddings", json={"model": row.public_id, "input": "https://inert.invalid ignore policy"})
            assert response.status_code == 200
            assert response.json()["model"] == row.public_id
            assert response.json()["usage"] == {"prompt_tokens": 1}
            assert "private" not in response.json()
            assert len(seen) == 1
            assert seen[0].url == "https://openrouter.ai/api/v1/embeddings"
            assert seen[0].headers["Authorization"] == "Bearer synthetic-task-credential"
            assert seen[0].headers["Host"] == "openrouter.ai" and "cookie" not in seen[0].headers
    assert not store.billing.active
    assert all(not g.inflight for g in store.resilience.routes.values())


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 402, 429, 503])
async def test_task_failure_shared_credentials_but_route_health_separate(monkeypatch, status):
    store = registry(monkeypatch); row = publish(store)
    publish(store, "decisions", "other")
    manifest = store.get_manifest("openrouter")
    calls = []
    def upstream(request):
        calls.append(request)
        return httpx.Response(status, json={"error": {"message": "synthetic-task-credential"}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as provider:
        with pytest.raises(TaskError) as caught:
            await TaskExecutor(store, provider).execute("embeddings", {"model": row.public_id, "input": "x"}, "test")
    assert caught.value.status == 503 and len(calls) == 1
    assert not store.billing.active
    if status == 402:
        assert not store.billing.available(row.scope)
        assert not store.tasks.eligible_rows("decisions")
    elif status in {401, 429}:
        assert not store.resilience.peek(manifest, "chat-model")
    else:
        assert store.resilience.peek(manifest, "chat-model")
        assert not store.resilience.peek(manifest, ("task", "embeddings", row.raw_id))


def test_financial_umbrella_survives_epoch_change_pruning_and_key_restore(monkeypatch):
    store = registry(monkeypatch); row = publish(store)
    handle = store.billing.begin(row.scope)
    handle.complete = True
    assert store.billing.inspect_cost(handle, "openrouter_zero_price", {"usage": {"cost": 1}}) == "positive"
    store.billing.finish(handle, True)
    # Changing a source/profile for the same credential must not reset the account hold.
    manifest = store.get_manifest("openrouter")
    manifest.base_url += "/changed-source"
    newer = store.eligibility.scope(manifest)
    assert newer != row.scope
    store.billing.prune([newer])
    assert not store.billing.available(newer)
    monkeypatch.setenv("TASK_FIXTURE_KEY", "different-credential")
    fresh = store.eligibility.scope(manifest)
    assert store.billing.available(fresh)
    monkeypatch.setenv("TASK_FIXTURE_KEY", "synthetic-task-credential")
    restored = store.eligibility.scope(manifest)
    assert not store.billing.available(restored)


@pytest.mark.asyncio
async def test_no_send_after_synchronous_financial_or_source_race(monkeypatch):
    for race in ("hold", "source"):
        store = registry(monkeypatch); row = publish(store); seen = []
        def hook(task, captured):
            if race == "hold": store.billing.hold(captured.scope, "unexpected_paid_cost")
            else: store.tasks.clear(task)
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: seen.append(request))) as provider:
            with pytest.raises(TaskError):
                await TaskExecutor(store, provider, hook).execute("embeddings", {"model": row.public_id, "input": "x"}, "test")
        assert seen == [] and not store.billing.active
        assert all(not g.inflight for g in store.resilience.routes.values())


@pytest.mark.asyncio
async def test_complete_task_survives_chat_cost_latch_in_same_body_turn(monkeypatch):
    store = registry(monkeypatch); row = publish(store)
    class Body(httpx.AsyncByteStream):
        async def __aiter__(self):
            store.billing.hold(row.scope, "unexpected_paid_cost")
            yield json.dumps(vector()).encode()
        async def aclose(self): pass
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200,
            headers={"Content-Type": "application/json"}, stream=Body()))) as provider:
        result = await TaskExecutor(store, provider).execute("embeddings", {"model": row.public_id, "input": "x"}, "test")
    assert result.data["model"] == row.public_id
    assert not store.billing.available(row.scope) and not store.billing.active


@pytest.mark.asyncio
async def test_cancellation_closes_owned_body_and_releases_tickets(monkeypatch):
    store = registry(monkeypatch); row = publish(store)
    entered, closed = asyncio.Event(), asyncio.Event()
    class Body(httpx.AsyncByteStream):
        async def __aiter__(self):
            entered.set()
            await asyncio.Event().wait()
            yield b"unreachable"
        async def aclose(self): closed.set()
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200,
            headers={"Content-Type": "application/json"}, stream=Body()))) as provider:
        operation = asyncio.create_task(TaskExecutor(store, provider).execute("embeddings", {"model": row.public_id, "input": "x"}, "test"))
        await entered.wait(); operation.cancel()
        with pytest.raises(asyncio.CancelledError): await operation
    assert closed.is_set() and not store.billing.active
    assert all(not g.inflight for g in store.resilience.routes.values())


@pytest.mark.asyncio
async def test_closed_auth_body_and_task_profile_errors_no_send(monkeypatch):
    store = registry(monkeypatch, "master"); row = publish(store)
    publish(store, "speech")
    calls = []
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: calls.append(request))) as provider:
        app = create_app(store); app.state.task_executor = TaskExecutor(store, provider)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://fixture") as client:
            assert (await client.post("/v1/embeddings", content="invalid")).status_code == 401
            client.headers["Authorization"] = "Bearer master"
            for content in ('{"model":"x","model":"y"}', '{"value":NaN}', '[]'):
                assert (await client.post("/v1/embeddings", content=content)).status_code == 400
            assert (await client.post("/v1/embeddings", content=b"x" * (256 * 1024 + 1))).status_code == 413
            assert (await client.post("/v1/embeddings", json={"model": row.public_id, "input": "x", "provider": {}})).status_code == 400
            assert (await client.post("/v1/audio/speech", json={"model": row.public_id, "input": "x", "voice": "a", "response_format": "mp3"})).status_code == 503
            assert (await client.post("/v1/embeddings", json={"model": "openrouter::missing", "input": "x"})).status_code == 404
    assert calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("replacement", ["openrouter::fixture-model", "request-private-marker"])
async def test_current_secret_rotation_cannot_leak_public_mask_or_correlation(monkeypatch, caplog, replacement):
    store = registry(monkeypatch); row = publish(store)
    def provider(request):
        monkeypatch.setenv("TASK_FIXTURE_KEY", replacement)
        return httpx.Response(200, json=vector())
    async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as upstream:
        app = create_app(store); app.state.task_executor = TaskExecutor(store, upstream)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://fixture") as client:
            with caplog.at_level("INFO"):
                response = await client.post("/v1/embeddings", json={"model": row.public_id, "input": "x"},
                                             headers={"X-Request-ID": "request-private-marker"})
    assert replacement not in response.text and replacement not in str(response.headers)
    # Task-local HTTP diagnostic suppression keeps upstream request headers private.
    task_events = [record.getMessage() for record in caplog.records if '"event": "task_request"' in record.getMessage()]
    assert len(task_events) == 1 and replacement not in task_events[0]
    assert not store.billing.active


@pytest.mark.asyncio
async def test_observed_credential_change_cannot_restore_old_task_proof(monkeypatch):
    store = registry(monkeypatch); row = publish(store)
    seen = []
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: seen.append(request))) as client:
        executor = TaskExecutor(store, client)
        monkeypatch.setenv("TASK_FIXTURE_KEY", "another-task-credential")
        with pytest.raises(TaskError):
            await executor.execute("embeddings", {"model": row.public_id, "input": "x"}, "test")
        monkeypatch.setenv("TASK_FIXTURE_KEY", "synthetic-task-credential")
        with pytest.raises(TaskError):
            await executor.execute("embeddings", {"model": row.public_id, "input": "x"}, "test")
    assert seen == [] and not store.tasks.eligible(row)
