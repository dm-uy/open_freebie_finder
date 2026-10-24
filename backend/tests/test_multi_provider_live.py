from backend.tests.eligibility_fixtures import install_fixture_evidence
"""Actual HTTP sockets through normal discovery/lifespan and cross-provider routing."""
import asyncio
import json
import threading
from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse

from backend.app.config import Settings
from backend.app.core.providers.models import ProviderManifest
from backend.app.core.providers.registry import ProviderRegistry
from backend.app.main import create_app
from scripts.probe_multi_provider import serve


@pytest.mark.asyncio
async def test_real_discovery_cascade_sse_and_nonblocking_health(monkeypatch):
    from backend.app.api.v1 import chat
    settings=Settings(_env_file=None,proxy_master_key=None)
    monkeypatch.setattr(chat,"get_settings",lambda:settings)
    calls=[]
    first=FastAPI()
    second=FastAPI()
    slow=FastAPI()
    entered=threading.Event()
    release=threading.Event()

    @first.get("/v1/models")
    @second.get("/v1/models")
    async def models():
        return {"data":[{"id":"shared"}]}

    @slow.get("/v1/models")
    async def slow_models():
        entered.set()
        while not release.is_set():
            await asyncio.sleep(.01)
        return {"data":[]}

    @first.post("/v1/chat/completions")
    async def fail():
        calls.append("alpha")
        return JSONResponse(status_code=429,content={"error":"private upstream body"})

    @second.post("/v1/chat/completions")
    async def complete(request:__import__('fastapi').Request):
        calls.append("beta")
        body=await request.json()
        if body.get("stream"):
            async def chunks():
                yield 'data: {"model":"shared","choices":[{"delta":{"role":"assistant"}}]}\n\n'
                yield 'data: {"model":"shared","choices":[{"delta":{"content":"OK"}}]}\n\n'
                yield 'data: [DONE]\n\n'
            return StreamingResponse(chunks(),media_type="text/event-stream")
        return {"model":"shared","choices":[{"message":{"role":"assistant","content":"OK"}}]}

    # Ambient proxy settings must not intercept real catalog or inference calls.
    for key in ("HTTP_PROXY","HTTPS_PROXY","ALL_PROXY"):
        monkeypatch.setenv(key,"http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY","")
    try:
        with serve(first) as a,serve(second) as b,serve(slow) as c:
            manifests=[ProviderManifest(id=identifier,name=identifier,base_url=url+"/v1",models_endpoint=url+"/v1/models",auth={"type":"none"},free_access_confirmed=True,chat_model_allowlist=["shared"]) for identifier,url in [("alpha",a),("beta",b),("slow",c)]]
            registry=ProviderRegistry(settings=settings,manifests=manifests)
            install_fixture_evidence(registry)
            registry.aliases[("alpha","shared")]="shared/model"
            registry.aliases[("beta","shared")]="shared/model"
            app=create_app(provider_registry=registry)
            with serve(app) as url:
                async with httpx.AsyncClient(base_url=url,trust_env=False) as client:
                    async with asyncio.timeout(3):
                        while not entered.is_set() or len(registry.get_eligible_models())<2:
                            await asyncio.sleep(.01)
                    assert (await client.get("/health")).status_code==200
                    assert not release.is_set()
                    listed=(await client.get("/v1/models")).json()
                    assert listed["data"][1]["owned_by"]=="alpha,beta"
                    for streaming in (False,True):
                        if hasattr(app.state,"cascade_router"):
                            registry.resilience = __import__("backend.app.core.balancer.resilience",fromlist=["ResilienceController"]).ResilienceController(registry)
                            app.state.cascade_router.resilience = registry.resilience
                        response=await client.post("/v1/chat/completions",json={"model":"shared/model","messages":[],"stream":streaming},headers={"X-Request-ID":"t007-socket-trace"})
                        assert response.status_code==200 and response.headers["X-Request-ID"]=="t007-socket-trace"
                        if streaming:
                            assert response.text.count("data: [DONE]")==1 and '"content": "OK"' in response.text
                            assert "shared/model" in response.text
                        else:
                            assert response.json()["model"]=="shared/model"
                        assert calls[-2:]==["alpha","beta"]
                release.set()
            # No background discovery task survives shutdown of its own app.
            assert app.state.discovery.statuses["alpha"].outcome=="succeeded"
    finally:
        release.set()


@pytest.mark.asyncio
async def test_periodic_tariff_refresh_revokes_without_catalog_renewal_and_keeps_health_live(monkeypatch):
    """Actual lifespan worker; accelerated internal clock interval, real HTTP reads."""
    from backend.app.api.v1 import chat
    from backend.tests.eligibility_fixtures import fixture_source
    settings=Settings(_env_file=None,proxy_master_key=None)
    # Test-only acceleration after validating the production defaults.
    settings.eligibility_refresh_seconds=.05
    monkeypatch.setattr(chat,"get_settings",lambda:settings)
    first=FastAPI();second=FastAPI()
    slow=threading.Event();entered=threading.Event();release=threading.Event()
    calls=[]
    @first.get("/v1/models")
    async def changing_source():
        if slow.is_set():
            entered.set()
            while not release.is_set():await asyncio.sleep(.01)
        return {"data":[{"id":"novel-dynamic-id","pricing":{"prompt":0,"completion":1 if slow.is_set() else 0,"request":0}}]}
    @second.get("/v1/models")
    async def free_source():
        return {"data":[{"id":"other-novel-id","pricing":{"prompt":0,"completion":0,"request":0}}]}
    @first.post("/v1/chat/completions")
    async def rate_limit():
        calls.append("first")
        return JSONResponse(status_code=429,content={"error":{"code":429}})
    @second.post("/v1/chat/completions")
    async def available(request:__import__('fastapi').Request):
        calls.append("second")
        body=await request.json()
        if body.get("stream"):
            return StreamingResponse(iter(['data: {"choices":[{"delta":{"content":"fallback"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n']),media_type="text/event-stream")
        return {"choices":[{"message":{"content":"fallback"}}]}
    try:
        with serve(first) as a,serve(second) as b:
            manifests=[ProviderManifest(id=p,name=p,base_url=url+"/v1",models_endpoint=url+"/v1/models",auth={"type":"none"}) for p,url in [("first",a),("second",b)]]
            registry=ProviderRegistry(settings=settings,manifests=manifests,evidence_source=fixture_source)
            app=create_app(provider_registry=registry)
            with serve(app) as base:
                async with httpx.AsyncClient(base_url=base,trust_env=False) as client:
                    async with asyncio.timeout(3):
                        while len(registry.get_eligible_models())<2:await asyncio.sleep(.01)
                    stamps=dict(registry._snapshot_times)
                    for streaming in (False,True):
                        if hasattr(app.state,"cascade_router"):
                            registry.resilience = __import__("backend.app.core.balancer.resilience",fromlist=["ResilienceController"]).ResilienceController(registry)
                            app.state.cascade_router.resilience = registry.resilience
                        response=await client.post("/v1/chat/completions",json={"model":"auto:free","messages":[],"stream":streaming})
                        assert response.status_code==200 and calls[-2:]==["first","second"]
                    slow.set()
                    async with asyncio.timeout(3):
                        while not entered.is_set():await asyncio.sleep(.01)
                    assert (await client.get("/health")).status_code==200
                    assert (await client.get("/v1/models")).status_code==200
                    assert not release.is_set()
                    release.set()
                    async with asyncio.timeout(3):
                        while any(m.provider_id=="first" for m in registry.get_eligible_models()):await asyncio.sleep(.01)
                    assert registry._snapshot_times==stamps
                    assert registry.eligibility.diagnostics(registry.get_manifest("first"))["states"]["paid"]==1
                    for streaming in (False,True):
                        before=len(calls)
                        response=await client.post("/v1/chat/completions",json={"model":"auto:free","messages":[],"stream":streaming})
                        assert response.status_code==200 and calls[before:]==["second"]
                        if streaming:assert response.text.count("[DONE]")==1
    finally:release.set()
