"""R3: shared consumer/worker gates without qualification or financial bypass."""
import asyncio
import json
import time
import httpx
import pytest
from backend.tests.test_account_probes import registry, catalog, buffer, frames, pending
from backend.app.core.eligibility.probes import ProbeWorker
from backend.app.core.adapters.openai_client import OpenAIProviderClient, UpstreamProviderError
from backend.app.core.balancer.router import CascadeRouter
from backend.app.core.balancer.resilience import HealthOutcome, ResilienceController


@pytest.mark.asyncio
@pytest.mark.parametrize('streaming_401',[False,True])
async def test_private_401_shared_and_inband_preserves_budget(monkeypatch,streaming_401):
    r,p=registry(monkeypatch);seen=[]
    def handler(request):
        if request.method=='GET':return httpx.Response(200,json=catalog())
        body=json.loads(request.content);seen.append(body['stream'])
        if streaming_401 and not body['stream']:return httpx.Response(200,json=buffer())
        return httpx.Response(200,content='data: {"error":{"code":401}}\n\n') if streaming_401 else httpx.Response(401)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        c=await pending(r,p,client);w=ProbeWorker(r,OpenAIProviderClient(client))
        assert not await w.qualify(p,c)
        assert len(seen)==(2 if streaming_401 else 1)
        assert r.resilience.snapshot()['auth_locked']==1
        assert not r.resilience.peek(p,c.model_id)
        before=len(w.budget.events)
        assert not await w.qualify(p,c)
        assert len(w.budget.events)==before and not w.health_tickets


@pytest.mark.asyncio
async def test_consumer_401_blocks_private_qualification(monkeypatch):
    r,p=registry(monkeypatch)
    def handler(request):
        if request.method=='GET':return httpx.Response(200,json=catalog())
        return httpx.Response(401)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        c=await pending(r,p,client)
        # Trusted local setup: a current both-mode lease exists before consumer failure.
        assert r.accounts.pass_pair(p,c)
        w=ProbeWorker(r,OpenAIProviderClient(client))
        with pytest.raises(UpstreamProviderError):
            await CascadeRouter(r,OpenAIProviderClient(client)).route_completion(c.model_id,{'messages':[]})
        assert w.select(p) is None
        assert not await w.qualify(p,c)
        assert not w.budget.events


@pytest.mark.asyncio
async def test_private_quota_recovery_cannot_publish_partial_pair(monkeypatch):
    r,p=registry(monkeypatch);clock=[time.monotonic()];r.resilience=ResilienceController(r,clock=lambda:clock[0])
    def handler(request):
        if request.method=='GET':return httpx.Response(200,json=catalog())
        return httpx.Response(200,json=buffer())
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        c=await pending(r,p,client);w=ProbeWorker(r,OpenAIProviderClient(client))
        t=r.resilience.acquire(p,c.model_id,private=True)
        r.resilience.finish(t,HealthOutcome('http',429));clock[0]+=60
        # Only one permitted send remains; recovery is not authority to exceed it.
        w.budget.events.append((w.budget.clock(),p.id,'new'))
        assert not await w.qualify(p,c)
        assert len(w.budget.events)==2
        assert not r.get_eligible_models()
        assert r.resilience.peek(p,c.model_id,private=True)
        assert not w.health_tickets


@pytest.mark.asyncio
async def test_source_401_no_inference_auth_and_financial_hold_no_private_recovery(monkeypatch):
    r,p=registry(monkeypatch)
    status=[200];sends=[]
    def handler(request):
        if request.method=='GET':return httpx.Response(status[0],json=catalog())
        sends.append(request);return httpx.Response(200,json=buffer())
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        c=await pending(r,p,client);status[0]=401
        from backend.app.core.discovery.orchestrator import DiscoveryOrchestrator
        await DiscoveryOrchestrator(r,client).discover_provider(p)
        assert r.resilience.snapshot()['auth_locked']==0
        status[0]=200;c=await pending(r,p,client)
        r.billing.hold(c.scope,'insufficient_balance_or_budget',retry_after='0')
        w=ProbeWorker(r,OpenAIProviderClient(client))
        assert not await w.qualify(p,c)
        assert not sends and not w.budget.events


@pytest.mark.asyncio
@pytest.mark.parametrize('status',[401,429])
@pytest.mark.parametrize('fail_sse',[False,True])
async def test_private_error_headers_survive_body_loss(monkeypatch,status,fail_sse):
    r,p=registry(monkeypatch)
    class Broken(httpx.AsyncByteStream):
        async def __aiter__(self):raise httpx.ReadError('secret');yield b''
        async def aclose(self):pass
    def handler(request):
        if request.method=='GET':return httpx.Response(200,json=catalog())
        if fail_sse and not json.loads(request.content)['stream']:return httpx.Response(200,json=buffer())
        return httpx.Response(status,headers={'Retry-After':'3600'},stream=Broken())
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        c=await pending(r,p,client);w=ProbeWorker(r,OpenAIProviderClient(client))
        assert not await w.qualify(p,c)
    assert not r.resilience.peek(p,c.model_id)
    if status==429:
        gate=r.resilience.quotas[c.scope]
        assert gate.until>=time.monotonic()+3590
    else:assert r.resilience.snapshot()['auth_locked']==1


@pytest.mark.asyncio
async def test_worker_owns_quota_recovery_consumer_skips_without_send(monkeypatch):
    r,p=registry(monkeypatch);clock=[time.monotonic()]
    r.resilience=ResilienceController(r,clock=lambda:clock[0]);entered=asyncio.Event();release=asyncio.Event();seen=[]
    async def handler(request):
        if request.method=='GET':return httpx.Response(200,json=catalog())
        body=json.loads(request.content);seen.append(body['stream'])
        if not body['stream']:
            entered.set();await release.wait();return httpx.Response(200,json=buffer())
        return httpx.Response(200,content=frames())
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        c=await pending(r,p,client);assert r.accounts.pass_pair(p,c)
        t=r.resilience.acquire(p,c.model_id);r.resilience.finish(t,HealthOutcome('http',429));clock[0]+=60
        w=ProbeWorker(r,OpenAIProviderClient(client));task=asyncio.create_task(w.qualify(p,c));await entered.wait()
        with pytest.raises(UpstreamProviderError):
            await CascadeRouter(r,OpenAIProviderClient(client)).route_completion(c.model_id,{'messages':[]})
        assert seen==[False] and len(w.budget.events)==1
        release.set();assert await task
        assert seen==[False,True] and len(w.budget.events)==2
        assert r.resilience.peek(p,c.model_id) and r.get_eligible_models()


@pytest.mark.asyncio
@pytest.mark.parametrize('streaming',[False,True])
async def test_private_synthetic_502_keeps_http200_origin(monkeypatch,streaming):
    r,p=registry(monkeypatch)
    def handler(request):
        if request.method=='GET':return httpx.Response(200,json=catalog())
        if streaming and not json.loads(request.content)['stream']:return httpx.Response(200,json=buffer())
        return httpx.Response(200,content='data: {"error":{}}\n\n') if streaming else httpx.Response(200,json={'error':{}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        c=await pending(r,p,client);w=ProbeWorker(r,OpenAIProviderClient(client))
        assert not await w.qualify(p,c)
        assert w.history[-1]['actual_http_status']==200
        assert w.history[-1]['failure_kind']=='protocol'
        assert r.resilience.snapshot()['auth_locked']==0
