"""Corrective T-007 evidence contracts against production classification paths."""
import asyncio
import builtins
import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from backend.app.config import Settings
from backend.app.core.discovery.orchestrator import DiscoveryOrchestrator
from backend.app.core.eligibility.evidence import source_verdict
from backend.app.core.providers.models import ProviderManifest, DiscoveredModel
from backend.app.core.providers.registry import ProviderRegistry


def profile(**changes):
    return ProviderManifest.model_validate(dict(id="openrouter", name="OR",
        base_url="https://openrouter.ai/api/v1", models_endpoint="https://openrouter.ai/api/v1/models",
        auth={"type":"bearer", "api_key_env":"FIXTURE_DYNAMIC_KEY"},
        eligibility_profile="openrouter_zero_price", discovery={"type":"openrouter_free"}, **changes))


def item(identifier="never-seeded", **changes):
    value = {"id":identifier, "pricing":{"prompt":"0e-5", "completion":0, "request":"0.00"},
             "architecture":{"input_modalities":["text"], "output_modalities":["text"]},
             "supported_parameters":["tools", "tool_choice"]}
    value.update(changes)
    return value


@pytest.fixture
def registry(monkeypatch):
    monkeypatch.setenv("FIXTURE_DYNAMIC_KEY", "safe-dynamic-key")
    return ProviderRegistry(settings=Settings(_env_file=None), manifests=[profile()])


@pytest.mark.asyncio
async def test_unknown_flags_localhost_and_manual_never_certify(monkeypatch):
    models=[]
    manifests=[]
    for identifier in ("groq", "nvidia_nim", "local_ollama", "mistral", "huggingface"):
        manifests.append(ProviderManifest(id=identifier, name="Fixture", base_url="http://localhost/v1",
            models_endpoint="http://localhost/v1/models", auth={"type":"none"}, free_access_confirmed=True,
            chat_model_allowlist=["visible"], discovery={"type":"manual", "static_models":["visible"]}))
        models.append(DiscoveredModel(id="visible", canonical_name="visible", provider_id=identifier, is_free=True))
    registry=ProviderRegistry(settings=Settings(_env_file=None), manifests=manifests)
    await registry.register_models(models)
    assert not registry.get_eligible_models()
    await DiscoveryOrchestrator(registry).run_cycle()
    assert not registry.get_eligible_models()
    assert len(registry.get_models())==5
    assert registry.eligibility.diagnostics(manifests[0])["reasons"]=={"account_evidence_unavailable":1}


@pytest.mark.asyncio
async def test_add_expire_revoke_and_failed_refresh_are_independent(registry,monkeypatch):
    clock=[10.0]
    monkeypatch.setattr("time.monotonic", lambda:clock[0])
    data=[{"data":[item()]}]
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=data[0]))) as client:
        worker=DiscoveryOrchestrator(registry,client)
        await worker.run_cycle()
        assert [m.id for m in registry.get_eligible_models()]==["never-seeded"]
        catalog_time=dict(registry._snapshot_times)
        clock[0]=20
        await worker.refresh_evidence()
        assert registry._snapshot_times==catalog_time
        data[0]={"data":[item(pricing={"prompt":0,"completion":1,"request":0})]}
        await worker.refresh_evidence()
        assert registry.get_eligible_models()==[]
        assert registry.eligibility.diagnostics(profile())["states"]["paid"]==1
        data[0]={"data":[item()]}
        await worker.refresh_evidence()
        assert registry.get_eligible_models()
        clock[0]=140
        assert registry.get_eligible_models()==[] # exact TTL, no grace
        await worker.refresh_evidence()
        assert registry.get_eligible_models()
        data[0]={"data":"bad"}
        await worker.refresh_evidence()
        assert registry.get_eligible_models()==[]
        assert registry.get_models() # raw visibility != certification


@pytest.mark.asyncio
async def test_epoch_binding_changes_during_fetch_and_read_away_back(registry,monkeypatch):
    old=registry.get_manifest("openrouter")
    async def handler(request):
        monkeypatch.setenv("FIXTURE_DYNAMIC_KEY","new-key")
        return httpx.Response(200,json={"data":[item()]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await DiscoveryOrchestrator(registry,client).run_cycle()
    assert registry.get_eligible_models()==[]
    scope=registry.eligibility.scope(old)
    registry.eligibility.publish(old,{"never-seeded":item()},scope)
    await registry.register_models([DiscoveredModel(id="never-seeded",canonical_name="model",provider_id="openrouter",is_free=True)])
    assert registry.get_eligible_models()
    monkeypatch.delenv("FIXTURE_DYNAMIC_KEY")
    assert not registry.get_eligible_models()
    monkeypatch.setenv("FIXTURE_DYNAMIC_KEY","new-key")
    assert not registry.get_eligible_models()


@pytest.mark.parametrize("prices,state",[
    ({"prompt":0,"completion":0},"free"),
    ({"prompt":False,"completion":0,"request":0},"unknown"),
    ({"prompt":"NaN","completion":0,"request":0},"unknown"),
    ({"prompt":-1,"completion":0,"request":0},"unknown"),
    ({"prompt":0,"completion":0,"request":"1e-10"},"paid"),
    ({"prompt":0,"completion":0,"request":0,"input_cache_read":1},"paid"),
    ({"prompt":0,"completion":0,"request":0,"surprise_fee":0},"unknown"),
    ({"prompt":"0e-100","completion":0,"request":0},"free"),
])
def test_prices_and_endpoint_binding(prices,state):
    assert source_verdict(profile(),item(pricing=prices)).state==state
    changed=profile();changed.base_url="https://some-other-provider.test/v1"
    assert source_verdict(changed,item(pricing=prices)).state=="unknown"
    changed=profile();changed.eligibility_profile="unsupported"
    assert source_verdict(changed,item()).state=="unknown"


def test_settings_bounds(monkeypatch):
    for value in (True, "60",9,301):
        with pytest.raises(ValidationError): Settings(_env_file=None,eligibility_refresh_seconds=value)
    with pytest.raises(ValidationError): Settings(_env_file=None,eligibility_refresh_seconds=70,eligibility_ttl_seconds=120)
    monkeypatch.setenv("ELIGIBILITY_REFRESH_SECONDS","100")
    monkeypatch.setenv("ELIGIBILITY_TTL_SECONDS","200")
    assert Settings(_env_file=None).eligibility_refresh_seconds==100


@pytest.mark.asyncio
async def test_bounded_records_and_no_io_reads(registry,monkeypatch):
    data={"data":[item(str(i)) for i in range(1100)]}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=data))) as client:
        await DiscoveryOrchestrator(registry,client).run_cycle()
    assert len(registry.get_models())==len(registry.eligibility.records)==1000
    def fail(*args,**kwargs): pytest.fail("Admission performed I/O")
    monkeypatch.setattr(builtins,"open",fail)
    monkeypatch.setattr(Path,"open",fail)
    monkeypatch.setattr(httpx.AsyncHTTPTransport,"handle_async_request",fail)
    assert len(registry.get_eligible_models())==1000


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["catalog_endpoint", "auth_type", "header_name", "credential_source"])
async def test_source_and_auth_binding_mutations_revoke_before_dispatch(registry, mutation):
    p=registry.get_manifest("openrouter")
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={"data":[item()]}))) as client:
        await DiscoveryOrchestrator(registry,client).run_cycle()
    assert registry.get_eligible_models()
    if mutation=="catalog_endpoint":p.models_endpoint="https://other.test/models"
    elif mutation=="auth_type":p.auth.type="header"
    elif mutation=="header_name":p.auth.custom_header_name="X-Changed"
    else:p.auth.api_key_env="OTHER_DYNAMIC_KEY"
    assert not registry.get_eligible_models()


@pytest.mark.asyncio
@pytest.mark.parametrize("reverse",[False,True])
async def test_contradictory_duplicate_ids_never_first_wins(registry,reverse):
    entries=[item(),item(pricing={"prompt":0,"completion":1,"request":0})]
    if reverse:entries.reverse()
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={"data":entries}))) as client:
        await DiscoveryOrchestrator(registry,client).run_cycle()
    assert not registry.get_eligible_models()


@pytest.mark.asyncio
async def test_contradictory_duplicate_after_retention_cap_rejects_retained_proof(registry):
    entries=[item(str(i)) for i in range(1001)]+[item("0",pricing={"prompt":1,"completion":1,"request":0})]
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={"data":entries}))) as client:
        await DiscoveryOrchestrator(registry,client).run_cycle()
    assert "0" not in {m.id for m in registry.get_eligible_models()}


@pytest.mark.asyncio
@pytest.mark.parametrize("failure",["trickle","oversize","cancel"])
async def test_evidence_refresh_failure_clears_proof_and_closes_owned_stream(registry,monkeypatch,failure):
    from backend.app.core.discovery import orchestrator as module
    entered=asyncio.Event()
    class Stream(httpx.AsyncByteStream):
        closed=False
        async def __aiter__(self):
            entered.set()
            if failure=="oversize":yield b"x"*100
            else:
                while True:
                    await asyncio.sleep(.01)
                    yield b" "
        async def aclose(self):self.closed=True
    stream=Stream();changed=[False]
    def handler(request):
        return httpx.Response(200,stream=stream) if changed[0] else httpx.Response(200,json={"data":[item()]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        worker=DiscoveryOrchestrator(registry,client)
        await worker.run_cycle()
        assert registry.get_eligible_models()
        changed[0]=True
        monkeypatch.setattr(module,"PROVIDER_TIMEOUT",.04)
        monkeypatch.setattr(module,"MAX_CATALOG_BYTES",64)
        task=asyncio.create_task(worker.refresh_evidence())
        if failure=="cancel":
            await entered.wait();task.cancel()
            with pytest.raises(asyncio.CancelledError):await task
        else:await task
        assert not registry.get_eligible_models() and stream.closed


@pytest.mark.parametrize("request_price,state,basis", [
    ("absent","free","catalog_zero_tokens_with_request_ceiling"),
    (0,"free","catalog_effective_price"),
    ("0e-5","free","catalog_effective_price"),
    (1,"paid","catalog_effective_price"),
    (None,"unknown","none"), (False,"unknown","none"),
    ("NaN","unknown","none"), ("Infinity","unknown","none"),
    (-1,"unknown","none"), ("invalid","unknown","none"),
])
def test_request_price_omission_is_distinct_from_observed_zero(request_price,state,basis):
    from copy import deepcopy
    prices={"prompt":"0","completion":"0"}
    if request_price!="absent":prices["request"]=request_price
    observation=item(pricing=prices)
    before=deepcopy(observation)
    verdict=source_verdict(profile(),observation)
    assert verdict.state==state and verdict.basis==basis
    assert observation==before
    if request_price=="absent":assert verdict.reason=="free_enforced" and "request" not in observation["pricing"]


@pytest.mark.parametrize("change", [
    {"pricing":{"completion":0}}, {"pricing":{"prompt":0}},
    {"pricing":{"prompt":True,"completion":0}},
    {"pricing":{"prompt":0,"completion":0,"input_cache_read":1}},
    {"pricing":{"prompt":0,"completion":0,"new_charge":0}},
    {"pricing":{"prompt":0,"completion":0,"overrides":[]}},
    {"architecture":{"input_modalities":["image"],"output_modalities":["text"]}},
])
def test_missing_request_exception_never_widens_other_source_predicates(change):
    assert source_verdict(profile(),item(**change)).state!="free"


@pytest.mark.asyncio
@pytest.mark.parametrize("loss",["dispatch_profile","owned_policy","owned_definition","source_endpoint","auth"])
async def test_enforced_basis_rechecks_owned_policy_on_listing_and_dispatch(registry,monkeypatch,loss):
    data={"data":[item(pricing={"prompt":0,"completion":0})]}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=data))) as client:
        await DiscoveryOrchestrator(registry,client).run_cycle()
    p=registry.get_manifest("openrouter")
    assert registry.get_eligible_models()
    assert registry.request_supported(p,"never-seeded",{"messages":[]})
    if loss=="dispatch_profile":monkeypatch.setattr(registry,"dispatch_profile",lambda p:None)
    elif loss=="owned_policy":monkeypatch.setattr("backend.app.core.eligibility.request.zero_price_policy_active",lambda p:False)
    elif loss=="owned_definition":monkeypatch.setattr("backend.app.core.eligibility.request.zero_price_policy",lambda p:{"max_price":{"prompt":0,"completion":0},"require_parameters":True})
    elif loss=="source_endpoint":p.models_endpoint="https://other.test/models"
    else:p.auth.type="header"
    assert not registry.get_eligible_models()
    assert not registry.request_supported(p,"never-seeded",{"messages":[]})


@pytest.mark.parametrize("outputs", [["text","audio"],["text","image"],["text","video"],["audio","text"]])
def test_mixed_output_zero_token_prices_do_not_certify_text_chat(outputs):
    from backend.app.core.eligibility.evidence import source_verdict
    manifest=ProviderManifest(id="openrouter",name="OpenRouter",base_url="https://openrouter.ai/api/v1",
        models_endpoint="https://openrouter.ai/api/v1/models",auth={"type":"bearer","api_key_env":"OPENROUTER_API_KEY"},eligibility_profile="openrouter_zero_price")
    item={"id":"new-mixed-model","architecture":{"input_modalities":["text"],"output_modalities":outputs},
          "pricing":{"prompt":"0","completion":"0"}}
    verdict=source_verdict(manifest,item)
    assert verdict.state=="unknown" and verdict.reason=="unsupported_output_modality"
    item["architecture"]["output_modalities"]=["text"]
    assert source_verdict(manifest,item).state=="free"
