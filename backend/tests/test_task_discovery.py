"""Owned task-source transport, shared scheduling and shutdown boundaries."""
import asyncio
from copy import deepcopy
import json

import httpx
import pytest

from backend.app.core.discovery.orchestrator import DiscoveryOrchestrator
from backend.app.core.providers.models import DiscoveredModel
from backend.app.core.tasks.catalog import TASKS, SOURCE_PATHS
from backend.tests.task_fixtures import registry as make_registry, publish, source


class Chunks(httpx.AsyncByteStream):
    def __init__(self, chunks, entered=None, release=None):
        self.chunks = chunks
        self.entered = entered
        self.release = release
        self.closed = 0

    async def __aiter__(self):
        for chunk in self.chunks:
            if self.entered is not None:
                self.entered.set()
                await self.release.wait()
            yield chunk

    async def aclose(self):
        self.closed += 1


@pytest.mark.asyncio
async def test_owned_sources_ignore_ambient_client_headers_cookies_auth_and_proxy(monkeypatch):
    registry = make_registry(monkeypatch)
    requests = []

    def respond(request):
        requests.append(request)
        task = "embeddings" if request.url.path.endswith("embeddings/models") else request.url.params["output_modalities"]
        return httpx.Response(200, json=source(task))

    for variable in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        monkeypatch.setenv(variable, "http://127.0.0.1:1")
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond),
            headers={"Authorization": "ambient-secret", "X-Ambient": "must-not-send"},
            cookies={"session": "must-not-send"}, auth=("ambient", "secret")) as client:
        worker = DiscoveryOrchestrator(registry, client)
        await asyncio.gather(*worker.tasks.jobs())
        assert not client.is_closed  # Borrowed client remains with its owner.

    assert len(requests) == 4
    for request in requests:
        assert request.method == "GET"
        assert str(request.url) in {"https://openrouter.ai" + path for path in SOURCE_PATHS.values()}
        assert request.headers["Authorization"] == "Bearer synthetic-task-credential"
        assert "Cookie" not in request.headers and "X-Ambient" not in request.headers
        assert request.extensions["timeout"] == httpx.Timeout(15).as_dict()
    assert registry.tasks.eligible_rows("embeddings")
    assert registry.tasks.eligible_rows("decisions")
    assert not registry.tasks.eligible_rows("rerank")
    assert not registry.tasks.eligible_rows("speech")


@pytest.mark.asyncio
async def test_redirect_revokes_only_affected_task_without_following(monkeypatch):
    registry = make_registry(monkeypatch)
    old = publish(registry)
    decision = publish(registry, "decisions")
    seen = []

    def redirect(request):
        seen.append(str(request.url))
        return httpx.Response(302, headers={"Location": "https://attacker.invalid/catalog"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(redirect), follow_redirects=True) as client:
        await DiscoveryOrchestrator(registry, client).tasks.refresh("embeddings")
    assert seen == ["https://openrouter.ai/api/v1/embeddings/models"]
    assert not registry.tasks.current(old)
    assert registry.tasks.get("embeddings", old.public_id).reason == "source_unavailable"
    assert registry.tasks.eligible(decision)


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [
    b'{"data":[],"data":[]}',
    b'{"data":[{"id":"duplicate","id":"key"}]}',
    b'{"data":[],"extra":NaN}',
    b'{"data":[],"has_more":true}',
    b'{"data":[],"next_cursor":"private-next"}',
    b'{"data":[],"result_info":{"page":1,"total_pages":2}}',
    b'not-json-private-upstream',
])
async def test_duplicate_json_constants_and_incomplete_sources_revoke(monkeypatch, body, caplog):
    registry = make_registry(monkeypatch)
    publish(registry)
    stream = Chunks([body])
    async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, stream=stream))) as client:
        await DiscoveryOrchestrator(registry, client).tasks.refresh("embeddings")
    assert stream.closed
    assert not registry.tasks.eligible_rows("embeddings")
    assert registry.tasks.states["embeddings"] == "failed"
    assert "private-upstream" not in caplog.text and "private-next" not in caplog.text


@pytest.mark.asyncio
async def test_decoded_source_bound_is_incremental_and_closes_response(monkeypatch):
    registry = make_registry(monkeypatch)
    publish(registry)
    # First JSON-looking byte plus two2MiB decoded chunks cross the bound.
    stream = Chunks([b"{", b" " * (2 * 1024 * 1024), b" " * (2 * 1024 * 1024)])
    async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, stream=stream))) as client:
        await DiscoveryOrchestrator(registry, client).tasks.refresh("embeddings")
    assert stream.closed
    assert registry.tasks.states["embeddings"] == "failed"
    assert not registry.tasks.eligible_rows("embeddings")


@pytest.mark.asyncio
async def test_key_changes_during_fetch_cannot_publish_old_snapshot(monkeypatch):
    registry = make_registry(monkeypatch)
    publish(registry)
    entered, release = asyncio.Event(), asyncio.Event()
    stream = Chunks([json.dumps(source("embeddings", raw="late-result")).encode()], entered, release)
    async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, stream=stream))) as client:
        worker = DiscoveryOrchestrator(registry, client)
        task = asyncio.create_task(worker.tasks.refresh("embeddings"))
        await asyncio.wait_for(entered.wait(), 1)
        monkeypatch.setenv("TASK_FIXTURE_KEY", "replacement-synthetic-key")
        release.set()
        await asyncio.wait_for(task, 1)
    assert stream.closed
    assert registry.tasks.get("embeddings", "openrouter::late-result") is None
    assert not registry.tasks.eligible_rows("embeddings")


@pytest.mark.asyncio
async def test_cancel_during_source_body_revokes_and_releases_shared_slot(monkeypatch):
    registry = make_registry(monkeypatch)
    publish(registry)
    entered, release = asyncio.Event(), asyncio.Event()
    stream = Chunks([b"{}"], entered, release)
    async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, stream=stream))) as client:
        worker = DiscoveryOrchestrator(registry, client)
        task = asyncio.create_task(worker.tasks.refresh("embeddings"))
        await asyncio.wait_for(entered.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert worker._semaphore._value == 4
        assert not client.is_closed
    assert stream.closed
    assert not registry.tasks.eligible_rows("embeddings")


@pytest.mark.asyncio
async def test_task_source_refresh_leaves_chat_snapshot_untouched(monkeypatch):
    registry = make_registry(monkeypatch)
    chat = DiscoveredModel(id="chat-only", provider_id="openrouter", canonical_name="chat-only")
    await registry.register_models([chat], provider_id="openrouter")
    before = (registry.get_models(), deepcopy(registry._snapshot_times))
    async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=source("embeddings")))) as client:
        await DiscoveryOrchestrator(registry, client).tasks.refresh("embeddings")
    assert (registry.get_models(), registry._snapshot_times) == before
    assert [row.raw_id for row in registry.tasks.eligible_rows("embeddings")] == ["fixture-model"]


@pytest.mark.asyncio
async def test_catalog_sources_share_four_slots_and_all_jobs_progress(monkeypatch):
    registry = make_registry(monkeypatch)
    active = 0
    maximum = 0
    seen = []
    entered = asyncio.Event()
    release = asyncio.Event()

    async def respond(request):
        nonlocal active, maximum
        assert request.method == "GET"  # No qualification/inference send.
        active += 1
        maximum = max(active, maximum)
        seen.append(str(request.url))
        if active == 4:
            entered.set()
        try:
            await release.wait()
            task = ("embeddings" if request.url.path.endswith("embeddings/models")
                    else request.url.params.get("output_modalities", "text"))
            return httpx.Response(200, json=source(task))
        finally:
            active -= 1

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        worker = DiscoveryOrchestrator(registry, client)
        task = asyncio.create_task(worker.run_cycle())
        await asyncio.wait_for(entered.wait(), 1)
        assert len(seen) == 4 and maximum == 4
        release.set()
        await asyncio.wait_for(task, 1)
    assert len(seen) == 5  # One chat source plus four task sources.
    assert maximum == 4 and active == 0
    assert all(registry.tasks.states[task] == "succeeded" for task in TASKS)
    assert registry.get_models()[0].id == "fixture-model"


@pytest.mark.asyncio
async def test_owned_lifespan_cancellation_closes_all_task_sources(monkeypatch):
    registry = make_registry(monkeypatch)
    entered = asyncio.Event()
    release = asyncio.Event()
    streams = []

    async def respond(request):
        stream = Chunks([b"{}"], entered, release)
        streams.append(stream)
        return httpx.Response(200, stream=stream)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        worker = DiscoveryOrchestrator(registry, client)
        stop = asyncio.Event()
        owned = asyncio.create_task(worker.run(stop))
        await asyncio.wait_for(entered.wait(), 1)
        stop.set()
        owned.cancel()
        with pytest.raises(asyncio.CancelledError):
            await owned
        assert worker._semaphore._value == 4
    assert streams and all(stream.closed for stream in streams)
    assert not registry.tasks.eligible_rows("embeddings")


@pytest.mark.asyncio
async def test_unowned_profile_never_fetches_even_with_fixture_key(monkeypatch):
    registry = make_registry(monkeypatch)
    registry.eligibility.source = lambda manifest, item: None
    seen = []
    async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: seen.append(request) or httpx.Response(200, json=source("embeddings")))) as client:
        await DiscoveryOrchestrator(registry, client).tasks.refresh("embeddings")
    assert not seen


@pytest.mark.asyncio
async def test_source_bound_applies_after_content_decompression(monkeypatch):
    import gzip
    registry = make_registry(monkeypatch)
    publish(registry)
    stream = Chunks([gzip.compress(b" " * (4 * 1024 * 1024 + 1))])
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
            200, headers={"Content-Encoding": "gzip"}, stream=stream))) as client:
        await DiscoveryOrchestrator(registry, client).tasks.refresh("embeddings")
    assert stream.closed
    assert not registry.tasks.eligible_rows("embeddings")
    assert registry.tasks.states["embeddings"] == "failed"


@pytest.mark.asyncio
async def test_task_source_owns_private_client_with_ambient_network_disabled(monkeypatch):
    registry = make_registry(monkeypatch)
    original_client = httpx.AsyncClient
    created = []

    def factory(**kwargs):
        assert kwargs == {"trust_env": False, "follow_redirects": False}
        client = original_client(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=source("embeddings"))), **kwargs)
        created.append(client)
        return client

    monkeypatch.setattr("backend.app.core.tasks.discovery.httpx.AsyncClient", factory)
    await DiscoveryOrchestrator(registry).tasks.refresh("embeddings")
    assert len(created) == 1 and created[0].is_closed
    assert registry.tasks.eligible_rows("embeddings")


@pytest.mark.asyncio
async def test_source_deadline_failure_closes_io_and_revokes(monkeypatch):
    from types import SimpleNamespace
    registry = make_registry(monkeypatch)
    publish(registry)
    stream = Chunks([b"{}"], asyncio.Event(), asyncio.Event())
    # Keep the production deadline code path but advance its local clock budget.
    timeout = asyncio.timeout
    monkeypatch.setattr("backend.app.core.tasks.discovery.asyncio", SimpleNamespace(
        timeout=lambda seconds: timeout(.01), CancelledError=asyncio.CancelledError))
    async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, stream=stream))) as client:
        worker = DiscoveryOrchestrator(registry, client)
        await worker.tasks.refresh("embeddings")
        assert worker._semaphore._value == 4
    assert stream.closed
    assert registry.tasks.states["embeddings"] == "failed"
    assert not registry.tasks.eligible_rows("embeddings")
