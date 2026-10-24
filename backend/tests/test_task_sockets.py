"""Actual loopback application/lifespan delivery, not external free-model proof."""
import asyncio
import json
import threading
from contextlib import asynccontextmanager
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse, StreamingResponse

from backend.app.main import create_app
from backend.app.core.tasks.protocol import validate_capabilities
from backend.app.core.tasks.transport import TaskExecutor, TaskError
from backend.tests.task_fixtures import registry, publish, source
from scripts.probe_multi_provider import serve


class FixtureExecutor(TaskExecutor):
    """Only test code simulates a future verified rerank/speech profile.

    Production admission is separately tested to reject these profiles. No
    environment flag or user request can activate this fixture class.
    """
    def _preflight(self, task, payload):
        if task not in {"rerank", "speech"}:
            return super()._preflight(task, payload)
        row = self.registry.tasks.get(task, payload["model"])
        if row is None or not self.registry.tasks.current(row) or not self.registry.billing.available(row.scope):
            raise TaskError()
        validate_capabilities(task, payload, {"voices": ["fixture"], "formats": ["pcm", "mp3"]})
        return row


@pytest.mark.asyncio
async def test_real_lifespan_task_catalogs_and_four_protocols(monkeypatch):
    store = registry(monkeypatch)
    upstream = FastAPI()
    seen = []
    @upstream.get("/{path:path}")
    async def models(path: str, request: Request):
        task = "embeddings" if path.endswith("embeddings/models") else request.query_params.get("output_modalities", "chat")
        data = source(task)
        if task == "speech": data["data"][0]["supported_voices"] = ["fixture"]
        return data

    @upstream.post("/{path:path}")
    async def infer(path: str, request: Request):
        value = await request.json(); seen.append((path, value))
        if path.endswith("embeddings"):
            return {"model": value["model"], "object": "list", "data": [{"object": "embedding", "index": 0, "embedding": [0.2, 0.3]}]}
        if path.endswith("rerank"):
            return {"model": value["model"], "results": [{"index": 1, "relevance_score": 0.9}, {"index": 0, "relevance_score": 0.1}]}
        if path.endswith("decisions"):
            return {"model": value["model"], "answers": {"ok": {"type": "noul", "noul": 0.9}},
                    "usage": {"cost": "not-a-proven-task-mapping", "input_tokens": 5}}
        return Response(b"\x00\x01\x02\x03", media_type="audio/pcm")

    original = httpx.AsyncClient
    with serve(upstream) as url:
        class Forward(httpx.AsyncBaseTransport):
            def __init__(self): self.transport = httpx.AsyncHTTPTransport(trust_env=False)
            async def handle_async_request(self, request):
                assert request.url.host == "openrouter.ai"
                target = httpx.Request(request.method, url + request.url.raw_path.decode(),
                    headers=dict(request.headers), content=await request.aread(), extensions=request.extensions)
                return await self.transport.handle_async_request(target)
            async def aclose(self): await self.transport.aclose()
        def client_factory(*args, **kwargs):
            kwargs.setdefault("transport", Forward())
            return original(*args, **kwargs)
        monkeypatch.setattr(httpx, "AsyncClient", client_factory)
        app = create_app(store)
        app.state.task_executor = FixtureExecutor(store)
        with serve(app) as proxy:
            async with original(base_url=proxy, trust_env=False) as client:
                async with asyncio.timeout(5):
                    while len(store.tasks.rows) < 4:
                        await asyncio.sleep(0.01)
                assert (await client.get("/health")).status_code == 200
                default = (await client.get("/v1/models")).json()["data"]
                assert all(not row["id"].startswith("openrouter::") for row in default)
                assert (await client.get("/v1/models?task=speech")).json()["data"] == []
                payloads = {
                    "embeddings": {"input": "x"},
                    "rerank": {"query": "x", "documents": ["a", "b"]},
                    "decisions": {"state": "x", "questions": {"ok": {"type": "noul", "instructions": "Is it OK?", "criteria": {"false": "No", "true": "Yes"}}}},
                    "audio/speech": {"input": "x", "voice": "fixture", "response_format": "pcm"},
                }
                for task, payload in payloads.items():
                    response = await client.post("/v1/" + task, json={"model": "openrouter::fixture-model", **payload},
                                                 headers={"X-Request-ID": "socket-" + task.replace("/", "-")})
                    assert response.status_code == 200, response.text
                    if task == "audio/speech":
                        assert response.content == b"\x00\x01\x02\x03"
                        assert response.headers["Content-Type"].startswith("audio/pcm")
                    else:
                        assert response.json()["model"] == "openrouter::fixture-model"
                        assert "cost" not in response.json().get("usage", {})
                assert len(seen) == 4
                assert {path for path, _ in seen} == {"api/v1/embeddings", "api/v1/rerank", "api/alpha/decisions", "api/v1/audio/speech"}
        assert not store.billing.active
        assert all(not gate.inflight for gate in store.resilience.routes.values())


@pytest.mark.asyncio
@pytest.mark.parametrize("body,mime", [(b"{}", "application/json"), (b"<html>err</html>", "audio/pcm"), (b"x", "audio/pcm"), (b"", "audio/pcm")])
async def test_bad_audio_is_complete_redacted_error_never_partial(monkeypatch, body, mime):
    store = registry(monkeypatch); row = publish(store, "speech")
    calls = []
    def provider(request):
        calls.append(request)
        return httpx.Response(200, content=body, headers={"Content-Type": mime})
    async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as transport:
        app = create_app(store); app.state.task_executor = FixtureExecutor(store, transport)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://fixture") as client:
            response = await client.post("/v1/audio/speech", json={"model": row.public_id, "input": "x", "voice": "fixture", "response_format": "pcm"})
    assert response.status_code == 502 and response.headers["Content-Type"].startswith("application/json")
    assert len(calls) == 1 and not store.billing.active


class LoopbackTransport(httpx.AsyncBaseTransport):
    """Only fixtures replace the owned upstream host with an ephemeral socket."""
    def __init__(self, origin):
        self.origin, self.transport = origin, httpx.AsyncHTTPTransport(trust_env=False,
            limits=httpx.Limits(max_keepalive_connections=0))
    async def handle_async_request(self, request):
        assert request.url.host == "openrouter.ai"
        local = httpx.Request(request.method, self.origin + request.url.raw_path.decode(),
            headers=dict(request.headers), content=await request.aread(), extensions=request.extensions)
        return await self.transport.handle_async_request(local)
    async def aclose(self): await self.transport.aclose()


@asynccontextmanager
async def no_external_sources(app):
    yield


@pytest.mark.asyncio
@pytest.mark.parametrize("mode,expected", [("mp3", 200), ("pcm", 200), ("mime", 502),
    ("json", 502), ("empty", 502), ("oversize", 502), ("truncated", 503)])
async def test_real_socket_audio_framing_and_bounded_failure(monkeypatch, mode, expected):
    store = registry(monkeypatch); row = publish(store, "speech")
    upstream = FastAPI()
    @upstream.post("/{path:path}")
    async def audio(path):
        if mode == "mp3": return Response(b"\xff\xfb\x90\x00", media_type="audio/mpeg")
        if mode == "mime": return Response(b"{}", media_type="application/json")
        if mode == "json": return Response(b'{"error":true}', media_type="audio/pcm")
        if mode == "empty": return Response(b"", media_type="audio/pcm")
        if mode == "oversize":
            async def body():
                for _ in range(9): yield b"a" * (1024 * 1024)
            return StreamingResponse(body(), media_type="audio/pcm")
        if mode == "truncated": return Response(b"aa", media_type="audio/pcm", headers={"Content-Length": "100"})
        return Response(b"aa", media_type="audio/pcm")
    with serve(upstream) as origin:
        async with httpx.AsyncClient(transport=LoopbackTransport(origin)) as provider:
            app = create_app(store); app.router.lifespan_context = no_external_sources
            app.state.task_executor = FixtureExecutor(store, provider)
            with serve(app) as proxy:
                async with httpx.AsyncClient(trust_env=False, timeout=4) as client:
                    response = await client.post(proxy + "/v1/audio/speech", json={"model": row.public_id,
                        "input": "x", "voice": "fixture", "response_format": "mp3" if mode == "mp3" else "pcm"})
    assert response.status_code == expected
    assert response.headers["Content-Type"].startswith("audio/" if expected == 200 else "application/json")
    assert not store.billing.active and all(not gate.inflight for gate in store.resilience.routes.values())


@pytest.mark.asyncio
async def test_actual_client_disconnect_closes_upstream_before_completion(monkeypatch):
    store = registry(monkeypatch); row = publish(store, "speech")
    entered, closed = threading.Event(), threading.Event()
    upstream = FastAPI()
    @upstream.post("/{path:path}")
    async def audio(path):
        async def body():
            try:
                entered.set()
                yield b"aa"
                await asyncio.Event().wait()
            finally: closed.set()
        return StreamingResponse(body(), media_type="audio/pcm")
    with serve(upstream) as origin:
        async with httpx.AsyncClient(transport=LoopbackTransport(origin)) as provider:
            app = create_app(store); app.router.lifespan_context = no_external_sources
            app.state.task_executor = FixtureExecutor(store, provider)
            with serve(app) as proxy:
                async with httpx.AsyncClient(trust_env=False) as client:
                    pending = asyncio.create_task(client.post(proxy + "/v1/audio/speech", json={"model": row.public_id,
                        "input": "x", "voice": "fixture", "response_format": "pcm"}))
                    assert await asyncio.to_thread(entered.wait, 2)
                    pending.cancel()
                    with pytest.raises(asyncio.CancelledError): await pending
                    assert await asyncio.to_thread(closed.wait, 2)
                    async with asyncio.timeout(2):
                        while store.billing.active: await asyncio.sleep(.01)
    assert all(not gate.inflight for gate in store.resilience.routes.values())
