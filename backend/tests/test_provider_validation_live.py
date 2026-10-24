"""Real loopback HTTP delivery checks; no external provider evidence is implied."""
import asyncio
import copy
import socket
import threading
import time
from contextlib import asynccontextmanager, contextmanager

import httpx
import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from backend.app.api.admin import providers as endpoint
from backend.app.config import Settings
from backend.app.core.providers.registry import ProviderRegistry
from backend.app.core.providers.validation import ProviderValidationService
from backend.app.core.telemetry.store import get_telemetry_store
from backend.app.main import create_app


@contextmanager
def serve(app):
    """Own an ephemeral socket/server thread and stop only those resources."""
    sock = socket.socket()
    server = None
    thread = None
    try:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_config=None, access_log=False, log_level="critical"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        deadline = time.monotonic() + 5
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started, "Fixture HTTP server did not start."
        yield f"http://127.0.0.1:{port}"
    finally:
        if server:
            server.should_exit = True
        if thread:
            thread.join(timeout=5)
            assert not thread.is_alive(), "Fixture HTTP server did not stop."
        sock.close()


@asynccontextmanager
async def no_external_discovery(app):
    yield


@pytest.mark.asyncio
async def test_real_socket_success_rate_limit_and_proxy_isolation(monkeypatch):
    settings = Settings(_env_file=None, proxy_master_key="fixture-master")
    registry = ProviderRegistry()
    upstream = FastAPI()
    received = []
    status = {"completion": 200}

    @upstream.get("/v1/models")
    async def models():
        received.append("GET")
        return {"data": [{"id": "fixture-model"}]}

    @upstream.post("/v1/chat/completions")
    async def completion():
        received.append("POST")
        if status["completion"] != 200:
            return JSONResponse(status_code=status["completion"], content={"error": "private upstream error"})
        return {"choices": [{"message": {"role": "assistant", "content": "OK"}}]}

    # Invalid ambient proxies must not intercept validation HTTP requests.
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        monkeypatch.setenv(name, "http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY", "")
    monkeypatch.setattr(endpoint, "get_settings", lambda: settings)
    monkeypatch.setattr(endpoint, "ProviderValidationService", lambda: ProviderValidationService(registry, settings))
    app = create_app()
    app.router.lifespan_context = no_external_discovery
    store = get_telemetry_store()
    before = copy.deepcopy((registry.get_models(), registry.get_manifests(), settings.model_dump(), await store.get_stats()))

    with serve(upstream) as upstream_url, serve(app) as app_url:
        body = {"manifest": {
            "id": "socket_fixture", "name": "Socket fixture", "base_url": upstream_url + "/v1",
            "models_endpoint": upstream_url + "/v1/models", "auth": {"type": "none"},
        }}
        async with httpx.AsyncClient(base_url=app_url, trust_env=False) as client:
            for expected in (True, False):
                response = await client.post("/api/admin/providers/validate", json=body, headers={"Authorization": "Bearer fixture-master"})
                assert response.status_code == 200
                report = response.json()
                assert report["valid"] == expected
                assert [c["name"] for c in report["checks"]] == ["configuration", "catalog", "completion"]
                if not expected:
                    assert report["checks"][2]["code"] == "rate_limited"
                    assert report["checks"][2]["http_status"] == 429
                    assert "private upstream error" not in response.text
                status["completion"] = 429
    assert received == ["GET", "POST", "GET", "POST"]
    assert before == (registry.get_models(), registry.get_manifests(), settings.model_dump(), await store.get_stats())


@pytest.mark.asyncio
async def test_health_progress_while_validation_waits(monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    upstream = FastAPI()

    @upstream.get("/v1/models")
    async def models():
        entered.set()
        while not release.is_set():
            await asyncio.sleep(0.01)
        return {"data": [{"id": "fixture-model"}]}

    @upstream.post("/v1/chat/completions")
    async def completion():
        return {"choices": [{"message": {"role": "assistant", "content": None}}]}

    settings = Settings(_env_file=None, proxy_master_key=None)
    registry = ProviderRegistry()
    monkeypatch.setattr(endpoint, "get_settings", lambda: settings)
    monkeypatch.setattr(endpoint, "ProviderValidationService", lambda: ProviderValidationService(registry, settings))
    app = create_app()
    app.router.lifespan_context = no_external_discovery
    try:
        with serve(upstream) as upstream_url, serve(app) as app_url:
            async with httpx.AsyncClient(base_url=app_url, trust_env=False) as client:
                pending = asyncio.create_task(client.post("/api/admin/providers/validate", json={"manifest": {
                    "id": "slow", "name": "Slow fixture", "base_url": upstream_url + "/v1",
                    "models_endpoint": upstream_url + "/v1/models", "auth": {"type": "none"},
                }}))
                try:
                    async with asyncio.timeout(2):
                        while not entered.is_set():
                            await asyncio.sleep(0.01)
                        response = await client.get("/health")
                    assert response.status_code == 200 and not pending.done()
                finally:
                    release.set()
                    result = await pending
                assert result.json()["valid"]
    finally:
        release.set()
