from backend.tests.eligibility_fixtures import install_fixture_evidence
"""T-007 discovery/admission tests against controlled documented catalog families."""
import asyncio
import json
import logging
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from pydantic import ValidationError

from backend.app.config import Settings
from backend.app.core.discovery import orchestrator as module
from backend.app.core.discovery.orchestrator import DiscoveryOrchestrator
from backend.app.core.providers.models import DiscoveredModel, ProviderManifest
from backend.app.core.providers.registry import ProviderRegistry


def provider(identifier="fixture", **changes):
    return ProviderManifest.model_validate({"id": identifier, "name": "Fixture",
        "base_url": f"http://{identifier}.test/v1", "models_endpoint": f"http://{identifier}.test/v1/models",
        "auth": {"type": "none"}, "free_access_confirmed": True,
        "chat_model_allowlist": ["a","b","safe","old","new","keep","z","shared"], **changes})


@pytest.fixture
def registry(monkeypatch):
    settings = Settings(_env_file=None, proxy_master_key=None)
    registry = ProviderRegistry(settings=settings)
    install_fixture_evidence(registry)
    registry._manifests = {"fixture": provider()}
    return registry


def catalog(ids=("a", "b")):
    return {"object": "list", "data": [{"id": value} for value in ids]}


@pytest.mark.asyncio
async def test_all_profiles_and_new_custom_manifest_participate(monkeypatch):
    settings = Settings(_env_file=None)
    registry = ProviderRegistry(settings=settings)
    install_fixture_evidence(registry)
    seen = []
    for manifest in registry.get_manifests():
        if manifest.auth.api_key_env:
            monkeypatch.setenv(manifest.auth.api_key_env, "fixture-provider-key")
    registry._manifests["custom"] = provider("custom")
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: (seen.append(r.url.host) or httpx.Response(200, json=catalog()))))
    try:
        discovery = DiscoveryOrchestrator(registry, client)
        statuses = await discovery.run_cycle()
        assert len(seen) == 8  # seven viable bundled profiles plus the custom manifest
        assert statuses["cloudflare"]["outcome"] == "unsupported_profile"
        assert statuses["cerebras"]["outcome"] == "excluded"
        assert statuses["github_models"]["outcome"] == "retired"
        assert all(statuses[key]["outcome"] == "succeeded" for key in ("openrouter", "groq", "nvidia_nim", "google_gemini", "mistral", "huggingface", "local_ollama", "custom"))
        assert not any("azure" in host or "cerebras" in host or "cloudflare" in host for host in seen)
    finally:
        await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("identifier,outcome", [("cloudflare","unsupported_profile"), ("cerebras","excluded"), ("github_models","retired")])
@pytest.mark.parametrize("manual", [False, True])
async def test_delivery_skips_cannot_be_bypassed(registry, identifier, outcome, manual):
    p = provider(identifier, is_enabled=True, free_access_confirmed=True, chat_model_allowlist=["a"],
                 discovery={"type": "manual", "static_models": ["a"]} if manual else {"type": "all_available"})
    registry._manifests = {identifier: p}
    await registry.register_models([DiscoveredModel(id="a", canonical_name="a", provider_id=identifier)])
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: pytest.fail("Skipped profile performed I/O"))) as client:
        worker = DiscoveryOrchestrator(registry, client)
        await worker.run_cycle()
        assert worker.statuses[identifier].outcome == outcome
        assert registry.get_eligible_models() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("change,code", [
    ({"is_enabled": False}, "disabled"),
    ({"auth": {"type": "bearer", "api_key_env": "UNCONFIGURED_TEST_KEY"}}, "missing_credentials"),
    ({"models_endpoint": "http://fixture.test/{account_id}/models"}, "unresolved_template"),
    ({"base_url": "http://fixture.test/{account_id}/v1"}, "unresolved_template"),
    ({"discovery": {"catalog_format": "unknown"}}, "unsupported_profile"),
    ({"models_endpoint": "http://user:pass@fixture.test/models"}, "invalid_configuration"),
    ({"discovery": {"type": "regex", "filter_expression": "a{4294967296}"}}, "invalid_configuration"),
    ({"discovery": {"type": "regex", "filter_expression": "["}}, "invalid_configuration"),
    ({"discovery": {"type": "manual", "static_models": []}}, "invalid_configuration"),
])
async def test_preflight_zero_io(registry, change, code, monkeypatch):
    monkeypatch.delenv("UNCONFIGURED_TEST_KEY", raising=False)
    registry._manifests["fixture"] = provider(**change)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: pytest.fail("Invalid profile performed I/O"))) as client:
        worker = DiscoveryOrchestrator(registry, client)
        await worker.run_cycle()
        assert worker.statuses["fixture"].code == code


@pytest.mark.asyncio
async def test_snapshot_replacement_empty_failure_and_freshness(registry, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("backend.app.core.providers.registry.time.monotonic", lambda: clock[0])
    registry.settings.discovery_interval_seconds = 10
    response = [httpx.Response(200, json=catalog())]
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: response[0])) as client:
        worker = DiscoveryOrchestrator(registry, client)
        await worker.run_cycle()
        assert len(registry.get_eligible_models()) == 2
        other = provider("other")
        registry._manifests[other.id] = other
        await registry.register_models([DiscoveredModel(id="safe", canonical_name="safe", provider_id="other")])
        response[0] = httpx.Response(503)
        await worker.discover_provider(registry.get_manifest("fixture"))
        assert len(registry.get_eligible_models()) == 1
        assert worker.statuses["fixture"].last_success_time is not None
        clock[0] += 21
        assert registry.get_eligible_models() == []
        response[0] = httpx.Response(200, json=catalog(["new"]))
        await worker.discover_provider(registry.get_manifest("fixture"))
        assert [m.id for m in registry.get_eligible_models()] == ["new"]
        response[0] = httpx.Response(200, json=catalog([]))
        await worker.discover_provider(registry.get_manifest("fixture"))
        assert registry.get_eligible_models() == []
        assert [m.id for m in registry.get_models()] == ["safe"]


@pytest.mark.asyncio
async def test_admission_and_revocation_without_refresh(registry, monkeypatch):
    monkeypatch.setenv("TEST_CLOUD_KEY", "cloud-key")
    cloud = provider(auth={"type":"bearer", "api_key_env":"TEST_CLOUD_KEY"},free_access_confirmed=False,chat_model_allowlist=[])
    registry._manifests["fixture"] = cloud
    trusted_source = registry.eligibility.source
    from backend.app.core.eligibility.evidence import Verdict
    registry.eligibility.source = lambda p, item: Verdict()
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=catalog()))) as client:
        worker = DiscoveryOrchestrator(registry, client)
        await worker.run_cycle()
        assert worker.statuses["fixture"].catalog_count == 2 and registry.get_eligible_models() == []
        # Legacy flags/lists never manufacture evidence. Only the explicit
        # controlled fixture source can publish a current certificate.
        cloud.free_access_confirmed = True
        cloud.chat_model_allowlist = ["a"]
        assert registry.get_eligible_models() == []
        registry.eligibility.source = trusted_source
        await worker.run_cycle()
        assert [m.id for m in registry.get_eligible_models()] == ["a"]
        cloud.chat_model_allowlist.clear()
        assert [m.id for m in registry.get_eligible_models()] == ["a", "b"]
        cloud.free_access_confirmed = False
        assert len(registry.get_eligible_models()) == 2
        monkeypatch.delenv("TEST_CLOUD_KEY")
        assert registry.get_eligible_models() == []



@pytest.mark.asyncio
async def test_paid_non_chat_and_secret_ids_aliases_excluded(registry, monkeypatch, caplog):
    monkeypatch.setenv("TEST_CLOUD_KEY", "secret-sentinel")
    cloud = provider(auth={"type":"bearer", "api_key_env":"TEST_CLOUD_KEY"}, free_access_confirmed=True,
                     chat_model_allowlist=["safe", "secret-sentinel", "alias", "embed", "audio"])
    registry._manifests = {"fixture": cloud}
    registry.aliases[("fixture", "alias")] = "secret-sentinel"
    data = {"data": [{"id":"safe"}, {"id":"secret-sentinel"}, {"id":"alias"},
                     {"id":"embed", "capabilities":{"completion_chat":False}},
                     {"id":"audio", "architecture":{"output_modalities":["audio"]}}]}
    caplog.set_level(logging.DEBUG)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=data))) as client:
        worker = DiscoveryOrchestrator(registry, client)
        await worker.run_cycle()
        assert [m.id for m in registry.get_eligible_models()] == ["safe"]
        assert "secret-sentinel" not in caplog.text
        # A newly resolved key can revoke an identifier from an existing snapshot.
        monkeypatch.setenv("TEST_CLOUD_KEY", "safe")
        assert registry.get_eligible_models() == []


@pytest.mark.asyncio
async def test_free_rule_custom_fields_context_regex_and_manual(registry):
    cases = [
        (provider("openrouter", discovery={"type":"openrouter_free"}, chat_model_allowlist=[]), {"data":[
            {"id":"a:free", "pricing":{"prompt":"0", "completion":0}, "context_length":"8192"},
            {"id":"paid", "pricing":{"prompt":"0", "completion":"0.1"}}, {"id":"unknown"}]}, ["a:free"]),
        (provider(discovery={"type":"regex", "filter_expression":"^keep", "model_id_field":"custom.id"}),
         {"data":[{"custom.id":"keep", "context_length":"nan"}, {"custom.id":"drop"}]}, ["keep"]),
        (provider(discovery={"type":"manual", "static_models":["z","a","z"]}), None, ["z","a"]),
    ]
    for p, data, expected in cases:
        registry._manifests = {p.id:p}
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=data))) as client:
            worker = DiscoveryOrchestrator(registry, client)
            models = await worker.discover_provider(p)
            assert [m.id for m in models] == expected
            if p.id == "openrouter":
                assert models[0].canonical_name == "a" and models[0].context_window == 8192
            elif p.discovery.type == "regex":
                assert models[0].context_window == 4096
            else:
                assert worker.statuses[p.id].code == "manual_catalog"


@pytest.mark.asyncio
@pytest.mark.parametrize("data,code", [
    ([],"invalid_catalog"), ({"data":{}},"invalid_catalog"),
    ({"data":[],"has_more":True},"incomplete_catalog"),
    ({"data":[],"next_cursor":"secret"},"incomplete_catalog"),
    ({"data":[],"result_info":{"page":1,"total_pages":2}},"incomplete_catalog"),
])
async def test_invalid_or_partial_catalog_keeps_snapshot(registry, data, code):
    await registry.register_models([DiscoveredModel(id="old", canonical_name="old", provider_id="fixture")])
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200,json=data))) as client:
        worker = DiscoveryOrchestrator(registry, client)
        await worker.run_cycle()
        assert worker.statuses["fixture"].code == code
        assert registry.get_eligible_models() == []
        assert [m.id for m in registry.get_models()] == ["old"]


@pytest.mark.asyncio
@pytest.mark.parametrize("status,code", [(401,"upstream_auth_error"),(403,"upstream_auth_error"),(429,"rate_limited"),(503,"upstream_unavailable"),(302,"upstream_http_error"),(400,"upstream_http_error")])
async def test_catalog_http_failures(registry, status, code, caplog):
    caplog.set_level(logging.DEBUG)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(status,text="SECRET BODY",headers={"Location":"http://other.test"}))) as client:
        worker = DiscoveryOrchestrator(registry, client)
        await worker.run_cycle()
        assert worker.statuses["fixture"].code == code
        assert "SECRET" not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,code", [("size","response_too_large"),("json","invalid_catalog"),("connection","connection_error"),("timeout","timeout")])
async def test_catalog_resource_failures(registry, monkeypatch, kind, code):
    monkeypatch.setattr(module,"MAX_CATALOG_BYTES",32)
    def handler(request):
        if kind == "connection":
            raise httpx.ConnectError("secret failure")
        if kind == "timeout":
            raise httpx.ReadTimeout("secret failure")
        return httpx.Response(200,content=b"x"*(33 if kind == "size" else 1))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        worker=DiscoveryOrchestrator(registry,client)
        await worker.run_cycle()
        assert worker.statuses["fixture"].code==code


@pytest.mark.asyncio
async def test_concurrency_and_no_overlapping_cycles(registry):
    registry._manifests = {f"fixture{i}":provider(f"fixture{i}") for i in range(9)}
    inflight = 0
    maximum = 0
    calls = 0
    async def handler(request):
        nonlocal inflight,maximum,calls
        inflight += 1
        calls += 1
        maximum=max(maximum,inflight)
        try:
            await asyncio.sleep(0.01)
            return httpx.Response(200,json=catalog())
        finally:
            inflight -= 1
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        worker=DiscoveryOrchestrator(registry,client)
        await asyncio.gather(worker.run_cycle(),worker.run_cycle())
        assert maximum == 4 and calls == 18 and inflight == 0
        assert len(worker.statuses)==9


@pytest.mark.asyncio
async def test_trickle_deadline_closes_stream_and_other_provider_progresses(registry,monkeypatch):
    monkeypatch.setattr(module,"PROVIDER_TIMEOUT",0.04)
    registry._manifests["other"]=provider("other")
    class Stream(httpx.AsyncByteStream):
        closed=False
        async def __aiter__(self):
            while True:
                await asyncio.sleep(0.01)
                yield b" "
        async def aclose(self):
            self.closed=True
    stream=Stream()
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200,stream=stream) if r.url.host=="fixture.test" else httpx.Response(200,json=catalog()))) as client:
        worker=DiscoveryOrchestrator(registry,client)
        await worker.run_cycle()
        assert worker.statuses["fixture"].code=="timeout" and stream.closed
        assert worker.statuses["other"].outcome=="succeeded"


def test_configuration_bounds_and_alias_rejection(tmp_path,registry):
    for invalid in (0,11,True,"3"):
        with pytest.raises(ValidationError):
            Settings(_env_file=None,max_failover_attempts=invalid)
    for value in (1,10):
        assert Settings(_env_file=None,max_failover_attempts=value).max_failover_attempts==value
    with pytest.raises(ValidationError):
        Settings(_env_file=None,routing_provider_priority=["groq","groq"])
    with pytest.raises(ValueError, match="Invalid routing priority"):
        ProviderRegistry(settings=Settings(_env_file=None,routing_provider_priority=["unknown"]))
    invalid=tmp_path/"aliases.yaml"
    invalid.write_text('aliases:\n- provider_id: groq\n  raw_id: a\n  canonical_name: a\n  source: fixture\n- provider_id: groq\n  raw_id: a\n  canonical_name: b\n  source: fixture\n')
    with pytest.raises(ValueError,match="Invalid model alias"):
        ProviderRegistry(aliases_path=invalid)

@pytest.mark.asyncio
async def test_auth_none_cloud_and_nonzero_openrouter_are_not_automatically_free(registry):
    cases=[provider(free_access_confirmed=False,chat_model_allowlist=[]),
           provider("openrouter",free_access_confirmed=False,chat_model_allowlist=[],discovery={"type":"all_available"})]
    for manifest in cases:
        registry._manifests={manifest.id:manifest}
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={"data":[{"id":"paid","pricing":{"prompt":"1","completion":"1"}}]}))) as client:
            worker=DiscoveryOrchestrator(registry,client)
            await worker.run_cycle()
            assert worker.statuses[manifest.id].catalog_count==1
            assert registry.get_eligible_models()==[]


@pytest.mark.asyncio
async def test_bad_credential_type_and_bad_manifest_cannot_stop_healthy_provider(registry,tmp_path):
    registry._manifests["broken"]=provider("broken",auth={"type":"bearer","api_key_env":"CORS_ORIGINS"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=catalog()))) as client:
        worker=DiscoveryOrchestrator(registry,client)
        await worker.run_cycle()
        assert worker.statuses["fixture"].outcome=="succeeded"
        assert worker.statuses["broken"].code=="invalid_configuration"
    path=tmp_path/"providers.yaml"
    import yaml
    path.write_text(yaml.safe_dump({"providers":[provider().model_dump(),
        {**provider("bad").model_dump(),"free_access_confirmed":"SECRET WRONG TYPE"}]}))
    loaded=ProviderRegistry(manifests_path=path,settings=registry.settings)
    install_fixture_evidence(loaded)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=catalog()))) as client:
        worker=DiscoveryOrchestrator(loaded,client)
        statuses=await worker.run_cycle()
        assert statuses["fixture"]["outcome"]=="succeeded"
        assert statuses["invalid_provider_1"]["code"]=="invalid_configuration"
        assert "SECRET" not in json.dumps(statuses)


@pytest.mark.asyncio
async def test_unexpected_provider_error_is_isolated(registry,monkeypatch):
    registry._manifests["other"]=provider("other")
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=catalog()))) as client:
        worker=DiscoveryOrchestrator(registry,client)
        original=worker._headers
        def malformed(manifest):
            if manifest.id=="fixture":
                raise AttributeError("SECRET faulty state")
            return original(manifest)
        monkeypatch.setattr(worker,"_headers",malformed)
        statuses=await worker.run_cycle()
        assert statuses["fixture"]["code"]=="invalid_configuration"
        assert statuses["other"]["outcome"]=="succeeded"


def test_environment_numeric_setting_and_safe_startup_error(monkeypatch):
    from backend.app.config import get_settings
    monkeypatch.setenv("MAX_FAILOVER_ATTEMPTS","5")
    assert Settings(_env_file=None).max_failover_attempts==5
    monkeypatch.setenv("MAX_FAILOVER_ATTEMPTS","SECRET-invalid")
    get_settings.cache_clear()
    try:
        with pytest.raises(ValueError,match="Invalid application configuration") as error:
            get_settings()
        assert "SECRET" not in str(error.value)
    finally:
        monkeypatch.delenv("MAX_FAILOVER_ATTEMPTS")
        get_settings.cache_clear()

@pytest.mark.asyncio
async def test_periodic_worker_refresh_and_stop(registry):
    registry.settings.discovery_interval_seconds=1
    calls=[]
    stop=asyncio.Event()
    def handler(request):
        calls.append(True)
        if len(calls)==2:
            stop.set()
        return httpx.Response(200,json=catalog())
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await asyncio.wait_for(DiscoveryOrchestrator(registry,client).run(stop),timeout=3)
    assert len(calls)==2


@pytest.mark.asyncio
async def test_cancel_discovery_worker_closes_active_response(registry):
    ready=asyncio.Event()
    class Stream(httpx.AsyncByteStream):
        closed=False
        async def __aiter__(self):
            ready.set()
            await asyncio.Event().wait()
            yield b"unused"
        async def aclose(self):
            self.closed=True
    stream=Stream()
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,stream=stream))) as client:
        worker=DiscoveryOrchestrator(registry,client)
        task=asyncio.create_task(worker.run(asyncio.Event()))
        await ready.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert stream.closed
