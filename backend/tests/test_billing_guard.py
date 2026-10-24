"""Billing incidents are independent of complete delivery; partial streams never replay."""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse

from backend.app.config import Settings
from backend.app.core.adapters.openai_client import OpenAIProviderClient
from backend.app.core.balancer.router import CascadeRouter
from backend.app.core.eligibility.billing import BillingGuard, classify_billing, retry_seconds
from backend.app.core.providers.models import DiscoveredModel, ProviderManifest
from backend.app.core.providers.registry import ProviderRegistry
from backend.app.core.telemetry.store import get_telemetry_store
from backend.app.main import create_app
from backend.tests.eligibility_fixtures import install_fixture_evidence, fixture_source
from scripts.probe_multi_provider import serve


def event(delta=None,finish=None,cost=None):
    value={"choices":[] if delta is None and finish is None else [{"delta":delta or {},"finish_reason":finish}]}
    if cost is not None:value["usage"]={"cost":cost}
    return 'data: '+json.dumps(value)+'\n\n'


async def registry_for(url="http://upstream.test/v1"):
    manifests=[ProviderManifest(id=p,name=p,base_url=url,models_endpoint=url+"/models",auth={"type":"none"}) for p in ("openrouter","other")]
    registry=install_fixture_evidence(ProviderRegistry(settings=Settings(_env_file=None,proxy_master_key=None),manifests=manifests))
    registry.dispatch_profile=lambda p:"openrouter_zero_price" if p.id=="openrouter" else None
    for provider in ("openrouter","other"):
        await registry.register_models([DiscoveredModel(id=m,canonical_name="shared",provider_id=provider) for m in ("a","b")])
    return registry


@pytest.mark.asyncio
@pytest.mark.parametrize("cost,latched",[("0",False),(None,False),("0.001",True),(True,True),("NaN",True)])
async def test_buffered_complete_delivers_and_only_blocks_future_scope(cost,latched):
    registry=await registry_for()
    seen=[]
    def handler(request):
        seen.append(request.url)
        response={"choices":[{"message":{"content":"ready","role":"assistant"}}],"usage":{"prompt_tokens":3}}
        if cost is not None:response["usage"]["cost"]=cost
        return httpx.Response(200,json=response)
    store=get_telemetry_store();await store.clear()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        router=CascadeRouter(registry,OpenAIProviderClient(client))
        data=await router.route_completion("shared",{"messages":[]},request_id="billing-complete")
        assert data["choices"][0]["message"]["content"]=="ready" and len(seen)==1
        assert bool(registry.billing.holds)==latched
        assert [t.success for t in await store.get_recent(10)]==[True]
        if latched:
            assert {m.provider_id for m in registry.get_eligible_models()}=={"other"}
            # Evidence re-publication cannot clear a cost latch.
            p=registry.get_manifest("openrouter")
            registry.eligibility.publish(p,{"a":{},"b":{}},registry.eligibility.scope(p))
            assert all(m.provider_id!="openrouter" for m in registry.get_eligible_models())


@pytest.mark.asyncio
@pytest.mark.parametrize("kind",["terminal","same_terminal","before","text","tools","reasoning"])
async def test_stream_cost_state_matrix(kind):
    registry=await registry_for()
    calls=[]
    if kind=="terminal":text=event({"content":"ready"})+event({},"stop")+event(cost="0.2")+'data: [DONE]\n\n'
    elif kind=="same_terminal":text=event({"content":"ready"},"length",cost="0.2")+'data: [DONE]\n\n'
    elif kind=="before":text=event({"role":"assistant"})+event(cost="0.2")
    else:
        delta={"content":"partial"} if kind=="text" else {"tool_calls":[{"index":0,"function":{"arguments":"{"}}]} if kind=="tools" else {"reasoning":"thinking"}
        text=event(delta)+event(cost="0.2")
    async def handler(request):
        body=json.loads(request.content);calls.append(body["model"])
        if len(calls)==1:return httpx.Response(200,content=text,headers={"Content-Type":"text/event-stream"})
        return httpx.Response(200,content=event({"content":"fallback"})+'data: [DONE]\n\n')
    store=get_telemetry_store();await store.clear()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        wrapper=await CascadeRouter(registry,OpenAIProviderClient(client)).route_stream_completion("shared",{"messages":[]},request_id="matrix")
        output="".join([value async for value in wrapper])
    traces=await store.get_recent(10)
    assert len(traces)==1 and traces[0].success==(kind in {"terminal","same_terminal","before"})
    assert bool(registry.billing.holds)
    if kind in {"terminal","same_terminal"}:
        assert output.count("data: [DONE]")==1 and '"error"' not in output and len(calls)==1
    elif kind=="before":
        assert 'fallback' in output and output.count("data: [DONE]")==1 and len(calls)==2
        assert [a.provider_id for a in traces[0].attempts]==["openrouter","other"]
    else:
        assert output.count('"error"')==1 and "unexpected_paid_cost" in output
        assert "[DONE]" not in output and len(calls)==1


@pytest.mark.parametrize("provider,status,data,expected",[
    ("openrouter",402,{},"insufficient_balance_or_budget"),
    ("openrouter",402,{"error":{"metadata":{"limit_source":"openrouter_in_flight_budget"}}},"billing_temporarily_unavailable"),
    ("openrouter",402,{"error":{"metadata":{"limit_source":[]}}},"billing_access_unverified"),
    ("openrouter",403,{"error":{"metadata":{"limit_source":"openrouter_key_limit"}}},"insufficient_balance_or_budget"),
    ("openrouter",403,{"error":{"message":"quota wallet"}},None),
    ("other",429,{"error":{"message":"quota balance"}},None),
    ("other",402,{},"billing_access_unverified"),
    ("mistral",402,{},"insufficient_balance_or_budget"),
])
def test_exact_billing_classification(provider,status,data,expected):
    assert classify_billing(provider,status,data)==expected


def test_recovery_permit_does_not_belong_to_concurrent_ordinary_success(monkeypatch):
    clock=[10.0];monkeypatch.setattr("time.monotonic",lambda:clock[0])
    guard=BillingGuard();scope=("fixture",)
    earlier=guard.begin(scope)
    guard.hold(scope,"insufficient_balance_or_budget")
    assert not guard.available(scope)
    clock[0]=70
    assert guard.available(scope) # listing never claims recovery
    recovery=guard.begin(scope)
    assert recovery and guard.begin(scope) is None
    guard.finish(earlier,True)
    assert not guard.available(scope)
    guard.finish(recovery,True)
    assert guard.available(scope)
    ready=guard.begin(scope);ready.complete=True
    incomplete=guard.begin(scope)
    guard.hold(scope,"unexpected_paid_cost")
    assert not ready.interrupted.is_set() and incomplete.interrupted.is_set()
    clock[0]+=10000
    assert not guard.available(scope)
    assert retry_seconds(None)==60 and retry_seconds("garbage")==60
    assert retry_seconds("0")==1 and retry_seconds("10000")==300
    assert 1 <= retry_seconds(format_datetime(datetime.now(timezone.utc)+timedelta(seconds=20))) <=20


@pytest.mark.asyncio
async def test_concurrent_pending_io_interrupted_completed_response_preserved():
    registry=await registry_for()
    ready=asyncio.Event();closed=[]
    class Pending(httpx.AsyncByteStream):
        async def __aiter__(self):
            ready.set();await asyncio.Event().wait();yield b"unused"
        async def aclose(self):closed.append(True)
    count=0
    def handler(request):
        nonlocal count
        count+=1
        if count==1:return httpx.Response(200,stream=Pending())
        return httpx.Response(200,json={"choices":[{"message":{"content":"complete"}}],"usage":{"cost":1}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        router=CascadeRouter(registry,OpenAIProviderClient(client))
        pending=asyncio.create_task(router.route_completion("shared",{"messages":[]}))
        await ready.wait()
        completed=await router.route_completion("shared",{"messages":[]})
        fallback=await pending
        assert completed["choices"][0]["message"]["content"]=="complete"
        assert fallback and closed and count==3 # pending goes to other provider, not a sibling model
        assert not registry.billing.active


@pytest.mark.asyncio
@pytest.mark.parametrize("streaming",[False,True])
async def test_balance_error_skips_sibling_models(streaming):
    registry=await registry_for();calls=[]
    def handler(request):
        calls.append(json.loads(request.content)["model"])
        if len(calls)==1:
            return httpx.Response(200,content='data: {"error":{"code":402}}\n\n') if streaming else httpx.Response(402,json={"error":{"code":402}})
        return httpx.Response(200,content=event({"content":"ok"})+'data: [DONE]\n\n') if streaming else httpx.Response(200,json={"choices":[{"message":{"content":"ok"}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        router=CascadeRouter(registry,OpenAIProviderClient(client))
        if streaming:
            wrapper=await router.route_stream_completion("shared",{"messages":[]})
            assert "[DONE]" in "".join([v async for v in wrapper])
        else:assert await router.route_completion("shared",{"messages":[]})
    assert len(calls)==2 and calls==["a","a"] # second is other credential, not first scope's b
    assert len(registry.billing.holds)==1


@pytest.mark.asyncio
@pytest.mark.parametrize("kind",["buffered","terminal","before","tools","reasoning","text","invalid_terminal"])
async def test_real_socket_delivery_state_and_next_request_blocking(monkeypatch,kind):
    from backend.app.api.v1 import chat
    first=FastAPI();second=FastAPI();calls=[]
    @first.get("/v1/models")
    @second.get("/v1/models")
    async def models():return {"data":[{"id":"dynamically-listed"}]}
    @first.post("/v1/chat/completions")
    async def first_complete(request:Request):
        calls.append("first")
        if kind=="buffered":return {"choices":[{"message":{"content":"ready"}}],"usage":{"cost":"0.1"}}
        if kind in {"terminal","invalid_terminal"}:
            wire=event({"content":"ready"})+event({},"stop")+event(cost="NaN" if kind=="invalid_terminal" else "0.1")+'data: [DONE]\n\n'
        elif kind=="before":wire=event({"role":"assistant"})+event(cost="0.1")
        else:
            delta={"content":"partial"} if kind=="text" else {"tool_calls":[{"index":0,"function":{"name":"f","arguments":"{"}}]} if kind=="tools" else {"reasoning_details":[{"text":"partial"}]}
            wire=event(delta)+event(cost="0.1")
        return StreamingResponse(iter([wire]),media_type="text/event-stream")
    @second.post("/v1/chat/completions")
    async def second_complete(request:Request):
        calls.append("second")
        body=await request.json()
        if not body.get("stream"):return {"choices":[{"message":{"content":"fallback"}}]}
        return StreamingResponse(iter([event({"content":"fallback"})+'data: [DONE]\n\n']),media_type="text/event-stream")
    settings=Settings(_env_file=None,proxy_master_key=None)
    monkeypatch.setattr(chat,"get_settings",lambda:settings)
    with serve(first) as a,serve(second) as b:
        manifests=[ProviderManifest(id=p,name=p,base_url=url+"/v1",models_endpoint=url+"/v1/models",auth={"type":"none"}) for p,url in [("openrouter",a),("other",b)]]
        registry=ProviderRegistry(settings=settings,manifests=manifests,evidence_source=fixture_source)
        registry.dispatch_profile=lambda p:"openrouter_zero_price" if p.id=="openrouter" else None
        app=create_app(provider_registry=registry)
        store=get_telemetry_store();await store.clear()
        with serve(app) as base:
            async with httpx.AsyncClient(base_url=base,trust_env=False) as client:
                async with asyncio.timeout(3):
                    while len(registry.get_eligible_models())<2:await asyncio.sleep(.01)
                response=await client.post("/v1/chat/completions",json={"model":"auto:free","messages":[],"stream":kind!="buffered"},headers={"X-Request-ID":"socket-state"})
                assert response.status_code==200
                if kind=="buffered":assert response.json()["choices"][0]["message"]["content"]=="ready"
                elif kind in {"terminal","invalid_terminal"}:assert response.text.count("[DONE]")==1 and '"error"' not in response.text
                elif kind=="before":assert "fallback" in response.text and response.text.count("[DONE]")==1
                else:assert '"error"' in response.text and "[DONE]" not in response.text
                async with asyncio.timeout(3):
                    while not any(t.request_id=="socket-state" for t in await store.get_recent(10)):await asyncio.sleep(.01)
                traces=[t for t in await store.get_recent(10) if t.request_id=="socket-state"]
                assert len(traces)==1 and traces[0].success==(kind in {"buffered","terminal","invalid_terminal","before"})
                assert (await client.get("/v1/models")).json()["data"][1]["owned_by"]=="other"
                again=await client.post("/v1/chat/completions",json={"model":"auto:free","messages":[]})
                assert again.status_code==200 and calls[-1]=="second"
                assert calls.count("first")==1


@pytest.mark.asyncio
@pytest.mark.parametrize("tail", ["timeout", "transport", "generation_error"])
async def test_terminal_completion_survives_bounded_final_usage_transport_loss(tail):
    registry=await registry_for()
    class Stream(httpx.AsyncByteStream):
        closed=False
        async def __aiter__(self):
            yield (event({"content":"ready"}, "stop", cost="0.1")).encode()
            if tail=="timeout":await asyncio.Event().wait()
            elif tail=="transport":raise httpx.ReadError("private transport diagnostic")
            else:yield b'data: {"error":{"code":500,"message":"private failure"}}\n\n'
        async def aclose(self):self.closed=True
    stream=Stream()
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,stream=stream))) as client:
        wrapper=await CascadeRouter(registry,OpenAIProviderClient(client)).route_stream_completion("shared",{"messages":[]},timeout=.02)
        wire="".join([v async for v in wrapper])
        assert "ready" in wire and stream.closed
        if tail=="generation_error":assert '"error"' in wire and "[DONE]" not in wire
        else:assert wire.count("[DONE]")==1 and '"error"' not in wire


@pytest.mark.asyncio
@pytest.mark.parametrize("message",[{}, {"content":7}, {"tool_calls":[{}]}, {"content":"ok", "tool_calls":[{}]}, {"content":7,"tool_calls":[{"id":"x","type":"function","function":{"name":"f","arguments":"{}"}}]}])
async def test_invalid_buffered_answer_does_not_gain_complete_exception(message):
    registry=await registry_for();seen=[]
    def handler(request):
        seen.append(True)
        value={"choices":[{"message":message}],"usage":{"cost":"0.1"}} if len(seen)==1 else {"choices":[{"message":{"content":"fallback"}}]}
        return httpx.Response(200,json=value)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        data=await CascadeRouter(registry,OpenAIProviderClient(client)).route_completion("shared",{"messages":[]})
    assert len(seen)==2 and data["choices"][0]["message"]["content"]=="fallback"
    assert registry.billing.holds


def test_failed_recovery_renews_fixed_hold(monkeypatch):
    clock=[10.0];monkeypatch.setattr("time.monotonic",lambda:clock[0])
    guard=BillingGuard();scope=("fixture",)
    guard.hold(scope,"insufficient_balance_or_budget")
    clock[0]=70
    handle=guard.begin(scope)
    guard.finish(handle,False)
    assert not guard.available(scope)
    clock[0]=129.99;assert not guard.available(scope)
    clock[0]=130;assert guard.available(scope)


@pytest.mark.asyncio
@pytest.mark.parametrize("after_output", [False,True])
@pytest.mark.parametrize("bad", [{"choices":"bad"}, {"choices":[{"delta":{"content":123}}]}, {"choices":[{"delta":{},"finish_reason":[]}]}])
async def test_malformed_stream_still_latches_reported_operator_cost(after_output,bad):
    registry=await registry_for();calls=[]
    def handler(request):
        calls.append(True)
        if len(calls)>1:return httpx.Response(200,content=event({"content":"fallback"})+'data: [DONE]\n\n')
        wire=(event({"content":"partial"}) if after_output else '')+'data: '+json.dumps({**bad,"usage":{"cost":"0.1"}})+'\n\n'
        return httpx.Response(200,content=wire)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        wrapper=await CascadeRouter(registry,OpenAIProviderClient(client)).route_stream_completion("shared",{"messages":[]})
        wire="".join([v async for v in wrapper])
    assert registry.billing.holds
    assert len(calls)==(1 if after_output else 2)
    assert ('"error"' in wire)==after_output


@pytest.mark.asyncio
async def test_same_event_generation_error_and_positive_cost_preserves_billing_error():
    registry=await registry_for()
    wire=event({"content":"partial"})+'data: '+json.dumps({"error":{"code":500,"message":"private"},"usage":{"cost":"0.1"}})+'\n\n'
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=wire))) as client:
        wrapper=await CascadeRouter(registry,OpenAIProviderClient(client)).route_stream_completion("shared",{"messages":[]})
        output="".join([value async for value in wrapper])
    assert '"type": "billing_guard_error"' in output and "unexpected_paid_cost" in output
    assert "[DONE]" not in output and registry.billing.holds


@pytest.mark.asyncio
async def test_guard_cancellation_owns_response_returned_by_cancellation_resistant_send():
    from backend.app.core.eligibility.billing import BillingInterrupted
    guard=BillingGuard();handle=guard.begin(("fixture",))
    entered=asyncio.Event();response=httpx.Response(200,stream=httpx.ByteStream(b"ready"))
    async def send():
        entered.set()
        try:await asyncio.Event().wait()
        except asyncio.CancelledError:return response
    task=asyncio.create_task(handle.wait_io(send()))
    await entered.wait()
    guard.hold(handle.scope,"unexpected_paid_cost")
    with pytest.raises(BillingInterrupted):await task
    assert response.is_closed
