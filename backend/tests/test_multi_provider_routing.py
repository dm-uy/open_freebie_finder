from backend.tests.eligibility_fixtures import install_fixture_evidence
"""T-007 canonical identity, provider diversity, safe diagnostics and zero-I/O listing."""
import asyncio
import builtins
import json
import logging
import statistics
import time
from pathlib import Path

import httpx
import pytest

from backend.app.api.v1 import chat
from backend.app.config import Settings
from backend.app.core.adapters.openai_client import OpenAIProviderClient, UpstreamProviderError
from backend.app.core.balancer.router import AmbiguousModelError, CascadeRouter
from backend.app.core.providers.models import DiscoveredModel, ProviderManifest
from backend.app.core.providers.registry import ProviderRegistry
from backend.app.core.telemetry.store import get_telemetry_store
from backend.app.main import create_app


@pytest.fixture
async def registry(monkeypatch):
    settings=Settings(_env_file=None,proxy_master_key=None)
    registry=ProviderRegistry(settings=settings)
    install_fixture_evidence(registry)
    registry._manifests={key:ProviderManifest(id=key,name=key,base_url=f"http://{key}.test/v1",models_endpoint=f"http://{key}.test/v1/models",auth={"type":"none"},free_access_confirmed=True,chat_model_allowlist=["raw-a","raw-b","different"]+[f"a{i}" for i in range(8)]) for key in ("alpha","beta","gamma")}
    monkeypatch.setattr(chat,"get_settings",lambda:settings)
    await registry.register_models([
        DiscoveredModel(id="raw-a",canonical_name="shared/model",provider_id="alpha"),
        DiscoveredModel(id="raw-b",canonical_name="shared/model",provider_id="beta"),
        DiscoveredModel(id="different",canonical_name="other/model",provider_id="gamma"),
    ])
    return registry


@pytest.mark.asyncio
async def test_raw_identity_tiers_and_negative_names(registry):
    router=CascadeRouter(registry)
    assert [m.provider_id for m in router.resolve_candidates("raw-a")]==["alpha","beta","gamma"]
    router.set_cooldown("alpha","raw-a")
    assert [m.provider_id for m in router.resolve_candidates("raw-a")]==["beta","gamma"]
    assert registry.canonical_name(registry.get_manifest("alpha"),"model-instruct-v2") != registry.canonical_name(registry.get_manifest("alpha"),"model-instruct-v1")
    assert registry.canonical_name(registry.get_manifest("alpha"),"model-q4") != registry.canonical_name(registry.get_manifest("alpha"),"model-q8")
    registry.aliases[("alpha","verified-raw")]="verified/model"
    assert registry.canonical_name(registry.get_manifest("alpha"),"verified-raw")=="verified/model"


@pytest.mark.asyncio
async def test_ambiguous_raw_and_canonical_precedence(registry):
    await registry.register_models([DiscoveredModel(id="raw-a",canonical_name="other/model",provider_id="beta")])
    router=CascadeRouter(registry)
    with pytest.raises(AmbiguousModelError):
        router.resolve_candidates("raw-a")
    app=create_app(provider_registry=registry)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        response=await client.post("/v1/chat/completions",json={"model":"raw-a","messages":[]})
        assert response.status_code==400 and response.headers["X-Request-ID"]
    assert router.resolve_candidates("shared/model")[0].provider_id=="alpha"


@pytest.mark.asyncio
async def test_diversity_and_explicit_priority(registry):
    await registry.register_models([DiscoveredModel(id=f"a{i}",canonical_name=f"model{i}",provider_id="alpha") for i in range(8)])
    router=CascadeRouter(registry)
    assert [m.provider_id for m in router.resolve_candidates("auto:free")][:3]==["alpha","beta","gamma"]
    registry.settings.routing_provider_priority=["gamma","beta"]
    assert [m.provider_id for m in router.resolve_candidates("auto:free")][:3]==["gamma","beta","alpha"]
    attempts=[]
    def handler(request):
        attempts.append(request.url.host)
        return httpx.Response(429) if request.url.host=="alpha.test" else httpx.Response(200,json={"choices":[{"message":{"role":"assistant","content":"ok"}}]})
    registry.settings.routing_provider_priority=[]
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        router=CascadeRouter(registry,OpenAIProviderClient(client))
        result=await router.route_completion("auto:free",{"messages":[]})
        assert attempts==["alpha.test","beta.test"] and result["model"]=="auto:free"


@pytest.mark.asyncio
@pytest.mark.parametrize("streaming",[False,True])
async def test_budget_vs_exhaustion_and_secret_error_hygiene(registry,streaming,caplog):
    caplog.set_level(logging.DEBUG)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(503,text="PROMPT SECRET KEY BODY"))) as client:
        router=CascadeRouter(registry,OpenAIProviderClient(client),max_attempts=1)
        method=router.route_stream_completion if streaming else router.route_completion
        with pytest.raises(UpstreamProviderError,match="budget reached") as error:
            await method("auto:free",{"messages":[{"role":"user","content":"PROMPT SECRET"}]})
        assert "SECRET" not in str(error.value)+caplog.text
        router=CascadeRouter(registry,OpenAIProviderClient(client),max_attempts=10)
        method=router.route_stream_completion if streaming else router.route_completion
        with pytest.raises(UpstreamProviderError,match="All free pool candidates exhausted"):
            await method("auto:free",{"messages":[]})


@pytest.mark.asyncio
async def test_invalid_success_json_cascades(registry):
    def handler(request):
        return httpx.Response(200,text="secret malformed response") if request.url.host=="alpha.test" else httpx.Response(200,json={"choices":[{"message":{"role":"assistant","content":"ok"}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result=await CascadeRouter(registry,OpenAIProviderClient(client)).route_completion("raw-a",{"messages":[]})
        assert result["model"]=="raw-a"


@pytest.mark.asyncio
async def test_false_free_and_key_alias_rechecks(registry,monkeypatch):
    registry._models_cache[0].is_free=False
    assert all(m.id!="raw-a" for m in registry.get_eligible_models())
    registry.settings.proxy_master_key="raw-b"
    assert all(m.id!="raw-b" for m in registry.get_eligible_models())
    assert CascadeRouter(registry).resolve_candidates("raw-b")==[]


@pytest.mark.asyncio
async def test_model_listing_memory_only_and_timings(registry,monkeypatch):
    app=create_app(provider_registry=registry)
    timings=[]
    # Prewarm all configuration/transport setup before instrumenting request-time I/O.
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        assert (await client.get("/v1/models")).status_code==200
        def no_io(*args,**kwargs):
            pytest.fail("Model listing performed filesystem/network I/O")
        with monkeypatch.context() as guard:
            guard.setattr(builtins,"open",no_io)
            guard.setattr(Path,"open",no_io)
            guard.setattr(httpx.AsyncHTTPTransport,"handle_async_request",no_io)
            for _ in range(30):
                start=time.perf_counter()
                response=await client.get("/v1/models")
                timings.append((time.perf_counter()-start)*1000)
                assert response.status_code==200
            registry.get_manifest("alpha").is_enabled=False
            response=await client.get("/v1/models")
            assert "alpha" not in ",".join(item["owned_by"] for item in response.json()["data"])
    values=sorted(timings)
    print(json.dumps({"listing_samples":len(values),"fixture_models":3,"median_ms":round(statistics.median(values),3),"p95_ms":round(values[int(len(values)*.95)-1],3)}))


@pytest.mark.asyncio
@pytest.mark.parametrize("streaming",[False,True])
async def test_endpoint_failure_envelopes_do_not_echo_upstream(registry,monkeypatch,streaming,caplog):
    app=create_app(provider_registry=registry)
    upstream=httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(500,text="SECRET upstream body")))
    app.state.cascade_router=CascadeRouter(registry,OpenAIProviderClient(upstream))
    caplog.set_level(logging.DEBUG)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
            response=await client.post("/v1/chat/completions",json={"model":"auto:free","messages":[],"stream":streaming})
            assert response.status_code==503 and "SECRET" not in response.text+caplog.text
    finally:
        await upstream.aclose()

@pytest.mark.asyncio
@pytest.mark.parametrize("streaming",[False,True])
@pytest.mark.parametrize("change",["disable","allowlist","new_secret"])
async def test_revocation_during_first_attempt_prevents_next_dispatch(registry,streaming,change):
    attempted=[]
    async def handler(request):
        attempted.append(request.url.host)
        if request.url.host=="alpha.test":
            target=registry.get_manifest("beta")
            if change=="disable":
                target.is_enabled=False
            elif change=="allowlist":
                target.chat_model_allowlist=["not-raw-b"]
            else:
                registry.settings.proxy_master_key="raw-b"
            await asyncio.sleep(0)
            return httpx.Response(429)
        return httpx.Response(503)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        router=CascadeRouter(registry,OpenAIProviderClient(client))
        method=router.route_stream_completion if streaming else router.route_completion
        with pytest.raises(UpstreamProviderError):
            await method("auto:free",{"messages":[]})
        assert attempted==["alpha.test","gamma.test"]


@pytest.mark.asyncio
async def test_closing_stream_wrapper_closes_provider_generator(registry):
    closed=[]
    class Client:
        async def stream_complete(self,**kwargs):
            try:
                yield 'data: {"choices":[{"delta":{"content":"first"}}]}\n\n'
                yield 'data: [DONE]\n\n'
            finally:
                closed.append(True)
    wrapper=await CascadeRouter(registry,Client()).route_stream_completion("raw-a",{"messages":[]})
    await wrapper.__anext__()
    await wrapper.aclose()
    assert closed==[True]

@pytest.mark.asyncio
async def test_case_sensitive_raw_ids_do_not_merge_identities(registry):
    registry.get_manifest("alpha").chat_model_allowlist=["Model","model"]
    registry._models_cache.clear()
    await registry.register_models([
        DiscoveredModel(id="Model",canonical_name="provider:alpha/Model",provider_id="alpha"),
        DiscoveredModel(id="model",canonical_name="provider:alpha/model",provider_id="alpha"),
    ])
    router=CascadeRouter(registry)
    assert router.resolve_candidates("Model")[0].canonical_name=="provider:alpha/Model"
    assert router.resolve_candidates("model")[0].canonical_name=="provider:alpha/model"
    with pytest.raises(AmbiguousModelError):
        router.resolve_candidates("MODEL")

@pytest.mark.asyncio
async def test_unstarted_wrapper_close_owns_prebuffered_upstream(registry):
    closed=[]
    class Client:
        async def stream_complete(self,**kwargs):
            try:
                yield 'data: {"choices":[{"delta":{"content":"first"}}]}\n\n'
                await asyncio.sleep(100)
            finally:
                closed.append(True)
    wrapper=await CascadeRouter(registry,Client()).route_stream_completion("raw-a",{"messages":[]})
    await wrapper.aclose()
    assert closed==[True]


@pytest.mark.asyncio
async def test_cancel_during_telemetry_closes_upstream_before_handoff(registry,monkeypatch):
    ready=asyncio.Event()
    closed=[]
    class Client:
        async def stream_complete(self,**kwargs):
            try:
                yield 'data: {"choices":[{"delta":{"content":"first"}}]}\n\n'
            finally:
                closed.append(True)
    router=CascadeRouter(registry,Client())
    async def record(trace):
        ready.set()
        await asyncio.Event().wait()
    monkeypatch.setattr(router,"_record_trace_safely",record)
    async def consume():
        wrapper = await router.route_stream_completion("raw-a", {"messages":[]})
        async for _ in wrapper:
            pass
    task=asyncio.create_task(consume())
    await ready.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed==[True]

@pytest.mark.asyncio
@pytest.mark.parametrize("fail_on",["http.response.start","http.response.body"])
async def test_asgi_downstream_send_disconnect_closes_owned_upstream(registry,fail_on):
    from starlette.requests import ClientDisconnect
    closed=[]
    class Client:
        async def stream_complete(self,**kwargs):
            try:
                yield 'data: {"choices":[{"delta":{"content":"first"}}]}\n\n'
                await asyncio.sleep(100)
            finally:
                closed.append(True)
    wrapper=await CascadeRouter(registry,Client()).route_stream_completion("raw-a",{"messages":[]})
    response=chat._OwnedStreamingResponse(wrapper,media_type="text/event-stream")
    async def receive():
        await asyncio.Event().wait()
    async def send(message):
        if message["type"]==fail_on:
            raise OSError("client disconnected")
    with pytest.raises(ClientDisconnect):
        await response({"type":"http","asgi":{"spec_version":"2.4"}},receive,send)
    assert closed==[True]
