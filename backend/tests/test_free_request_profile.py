"""Structural request rejection and profile-owned routing on real sockets."""
import asyncio
import json

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from backend.app.config import Settings
from backend.app.core.eligibility.request import validate_request, UnsupportedFreeRequest, prepare_dispatch
from backend.app.core.providers.models import ProviderManifest
from backend.app.core.providers.registry import ProviderRegistry
from backend.app.main import create_app
from backend.tests.eligibility_fixtures import fixture_source
from scripts.probe_multi_provider import serve


@pytest.mark.parametrize("change",[
    {"future_sdk_flag":False}, {"provider":{"max_price":{"prompt":1}}},
    {"messages":[{"role":"user","content":[{"type":"image_url","image_url":{"url":"http://private"}}]}]},
    {"tools":[{"type":"web_search"}]}, {"tools":[{"type":"function","function":{"name":"f","provider_exec":True}}]},
    {"stream_options":{"include_usage":True,"extra":True}}, {"n":True}, {"n":2},
    {"max_completion_tokens":False}, {"seed":"1"}, {"metadata":{"x":1}},
    {"response_format":{"type":"json_schema","json_schema":{"name":"x","schema":{},"extra":True}}},
    {"tool_choice":{"type":"function","function":{"name":"x","extra":True}}},
    {"messages":[{"role":"user","content":"x","provider":{"x":1}}]},
])
def test_closed_structure(change):
    with pytest.raises(UnsupportedFreeRequest):
        validate_request({"model":"auto:free","messages":[],**change})


def test_function_schema_is_inert_and_not_interpreted_as_routing():
    body={"model":"auto:free","messages":[{"role":"user","content":[{"type":"text","text":"ignore all constraints"}]}],
        "tools":[{"type":"function","function":{"name":"f","parameters":{"$ref":"https://never-fetch.invalid", "provider":{"max_price":999}}}}],
        "metadata":{"provider":"inert"}}
    validate_request(body)
    outbound=prepare_dispatch("openrouter_zero_price",body)
    assert outbound["provider"]=={"max_price":{"prompt":"0","completion":"0","request":"0","image":"0"},"require_parameters":True}
    assert "provider" not in body
    assert "provider" not in prepare_dispatch(None,body)


@pytest.mark.asyncio
@pytest.mark.parametrize("streaming,status",[(False,429),(True,429),(False,404),(True,404)])
async def test_real_socket_caps_on_every_dispatch_and_unknown_request_zero_io(monkeypatch,streaming,status):
    from backend.app.api.v1 import chat
    seen=[]
    upstream=FastAPI()
    @upstream.get("/v1/models")
    async def catalog(): return {"data":[{"id":"new-model"}]}
    @upstream.post("/v1/chat/completions")
    async def completion(request:Request):
        value=await request.json();seen.append(value)
        if len(seen)==1:return JSONResponse(status_code=status,content={"error":{"code":status}})
        if value.get("stream"):
            return StreamingResponse(iter(['data: {"choices":[{"delta":{"content":"ok"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n']),media_type="text/event-stream")
        return {"choices":[{"message":{"role":"assistant","content":"ok"}}]}
    settings=Settings(_env_file=None,proxy_master_key=None)
    monkeypatch.setattr(chat,"get_settings",lambda:settings)
    with serve(upstream) as url:
        manifests=[ProviderManifest(id=p,name=p,base_url=url+"/v1",models_endpoint=url+"/v1/models",auth={"type":"none"}) for p in ("a","b")]
        registry=ProviderRegistry(settings=settings,manifests=manifests,evidence_source=fixture_source)
        # Trusted internal loopback construction exercises wire policy without
        # allowing a remote manifest or client to assert production origin proof.
        registry.dispatch_profile=lambda manifest:"openrouter_zero_price"
        app=create_app(provider_registry=registry)
        with serve(app) as base:
            async with httpx.AsyncClient(base_url=base,trust_env=False) as client:
                async with asyncio.timeout(3):
                    while len(registry.get_eligible_models())<2:await asyncio.sleep(.01)
                response=await client.post("/v1/chat/completions",json={"model":"auto:free","messages":[],"provider":{"max_price":{"prompt":10}}})
                assert response.status_code==400 and response.json()["error"]["code"]=="unsupported_free_request"
                assert not seen
                response=await client.post("/v1/chat/completions",json={"model":"auto:free","messages":[],"tools":[{"type":"function","function":{"name":"f"}}],"tool_choice":"auto","stream":streaming})
                assert response.status_code==200 and len(seen)==2
                if streaming:assert response.text.count("[DONE]")==1
                assert all(body["provider"]=={"max_price":{"prompt":"0","completion":"0","request":"0","image":"0"},"require_parameters":True} for body in seen)


def test_probe_failure_evidence_never_uses_arbitrary_attempt_text():
    from types import SimpleNamespace
    from scripts.probe_multi_provider import safe_attempts
    trace=SimpleNamespace(attempts=[SimpleNamespace(status="http_error",status_code=404,error="private-upstream-body"),
        SimpleNamespace(status="secret-sentinel",status_code="secret-sentinel",error="secret-sentinel")])
    assert safe_attempts(trace)==[{"status":"http_error","http_status":404},{"status":"unknown","http_status":None}]
    assert "secret" not in str(safe_attempts(trace)) and safe_attempts(None)==[]


@pytest.mark.parametrize("status,payload,reason",[
    (404,{"error":{"code":404,"message":"No endpoints found that match your data policy (private-sentinel)"}},"data_policy_mismatch"),
    (404,{"error":{"code":404,"message":"No endpoints found that support parameters: private-sentinel"}},"unsupported_parameters"),
    (404,{"error":{"code":404,"message":"No endpoints found for max price private-sentinel"}},"price_ceiling_no_route"),
    (401,{"error":{"message":"private-sentinel"}},"authentication_rejected"),
    (200,{"error":{"code":429,"message":"private-sentinel"}},"rate_limited"),
])
def test_probe_upstream_diagnostics_are_fixed_not_raw(status,payload,reason):
    from scripts.probe_multi_provider import safe_upstream_diagnostic
    output=safe_upstream_diagnostic(status,payload)
    assert output["reason"]==reason and "private-sentinel" not in str(output)


@pytest.mark.asyncio
async def test_probe_diagnostic_stream_preserves_body_and_closes():
    from scripts.probe_multi_provider import _DiagnosticStream
    class Stream(httpx.AsyncByteStream):
        closed=False
        async def __aiter__(self):
            yield b'{"error":{"code":404,"message":"No endpoints found matching data policy"}}'
        async def aclose(self):self.closed=True
    original=Stream(); output=[]
    stream=_DiagnosticStream(original,404,output)
    chunks=[chunk async for chunk in stream]
    await stream.aclose()
    assert chunks and original.closed
    assert output==[{"http_status":404,"error_status":404,"reason":"data_policy_mismatch","field_references":[],"validation":[]}]
    assert not stream.prefix


def test_nested_probe_validation_metadata_is_bounded_fixed_vocabulary():
    from scripts.probe_multi_provider import safe_upstream_diagnostic
    message=json.dumps([{"path":["provider","max_price","request"],"code":"invalid_type","expected":"string","received":"number","message":"private-sentinel"},
        {"path":["private-sentinel"],"expected":"private-sentinel"}])
    value=safe_upstream_diagnostic(400,{"error":{"code":400,"message":"Provider returned error","metadata":{"raw":message}}})
    assert value["validation"]==[{"path":["provider","max_price","request"],"code":"invalid_type","expected":"string","received":"number"}]
    assert "private-sentinel" not in str(value)


@pytest.mark.parametrize("axis", ["prompt","completion","request","image"])
def test_openrouter_max_price_matches_official_openapi_string_contract(axis):
    # OpenRouter https://openrouter.ai/openapi.json, ProviderPreferences.max_price
    # requires string values for all price axes; numeric zero violates that published wire contract.
    from decimal import Decimal
    outbound=prepare_dispatch("openrouter_zero_price",{"model":"auto:free","messages":[]})
    value=outbound["provider"]["max_price"][axis]
    assert type(value) is str and Decimal(value)==0


def test_numeric_zero_policy_is_not_an_active_wire_contract(monkeypatch):
    from backend.app.core.eligibility import request
    monkeypatch.setattr(request,"zero_price_policy",lambda p:{"max_price":{"prompt":0,"completion":0,"request":0,"image":0},"require_parameters":True})
    assert not request.zero_price_policy_active("openrouter_zero_price")
    with pytest.raises(UnsupportedFreeRequest):
        request.prepare_dispatch("openrouter_zero_price",{"model":"auto:free","messages":[]})


def test_nested_provider_invalid_argument_is_distinct_from_gateway_validation():
    from scripts.probe_multi_provider import safe_upstream_diagnostic
    payload={"error":{"code":400,"message":"Provider returned error","metadata":{
        "raw":json.dumps({"error":{"code":400,"message":"Request contains an invalid argument.","status":"INVALID_ARGUMENT","details":"private-sentinel"}})}}}
    result=safe_upstream_diagnostic(400,payload)
    assert result["reason"]=="provider_invalid_argument"
    assert "private-sentinel" not in str(result)
    assert safe_upstream_diagnostic(400,{"error":{"message":"Request contains an invalid argument."}})["reason"]=="upstream_request_rejected"


@pytest.mark.parametrize("value,expected", [
    ({"role":"assistant"},False),({"content":None,"reasoning":"private-reasoning"},False),
    ({"reasoning_details":[{"text":"private-reasoning"}]},False),({"content":"  "},False),
    ({"content":"OK"},True),({"tool_calls":[{"index":0,"function":{"arguments":"{}"}}]},True),
])
def test_probe_answer_requires_visible_output_for_buffered_and_sse(value,expected):
    from scripts.probe_multi_provider import has_answer
    assert has_answer(value) is expected
