"""T-009 actual-socket delivery plus controlled ownership and classification races."""
import asyncio
from contextlib import asynccontextmanager
import json
import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from scripts.probe_multi_provider import serve
from backend.app.main import create_app
from backend.app.config import Settings
from backend.app.core.providers.models import ProviderManifest, DiscoveredModel
from backend.app.core.providers.registry import ProviderRegistry
from backend.app.core.balancer.router import CascadeRouter
from backend.app.core.balancer.resilience import ResilienceController
from backend.app.core.adapters.openai_client import OpenAIProviderClient, UpstreamProviderError
from backend.tests.eligibility_fixtures import install_fixture_evidence


async def registry_for(urls):
    manifests=[ProviderManifest(id=p,name=p,base_url=url+'/v1',models_endpoint=url+'/v1/models',auth={'type':'none'}) for p,url in urls]
    r=ProviderRegistry(settings=Settings(_env_file=None,proxy_master_key=None),manifests=manifests)
    install_fixture_evidence(r)
    await r.register_models([DiscoveredModel(id=model,provider_id=p,canonical_name='shared',context_window=4096)
                            for p,_ in urls for model in ('a','b')])
    return r


def completion():return {'choices':[{'message':{'role':'assistant','content':'OK'}}]}


def sse():return 'data: '+json.dumps({'choices':[{'delta':{'content':'OK'}}]})+'\n\ndata: [DONE]\n\n'


@pytest.mark.asyncio
@pytest.mark.parametrize('failure',[429,503,401])
@pytest.mark.parametrize('streaming',[False,True])
async def test_real_socket_cross_credential_failover_and_auth(monkeypatch,failure,streaming):
    first=FastAPI();second=FastAPI();seen=[]
    @first.post('/v1/chat/completions')
    async def fail(request:Request):
        seen.append(('alpha',(await request.json())['model']))
        return JSONResponse({'error':{'code':failure}},status_code=failure,headers={'Retry-After':'3600'})
    @second.post('/v1/chat/completions')
    async def success(request:Request):
        body=await request.json();seen.append(('beta',body['model']))
        return StreamingResponse(iter([sse()]),media_type='text/event-stream') if body['stream'] else completion()
    with serve(first) as a,serve(second) as b:
        r=await registry_for([('alpha',a),('beta',b)])
        app=create_app(provider_registry=r)
        @asynccontextmanager
        async def fixed_lifespan(app):yield
        app.router.lifespan_context=fixed_lifespan
        from backend.app.api.v1 import chat
        monkeypatch.setattr(chat,'get_settings',lambda:r.settings)
        with serve(app) as base:
            async with httpx.AsyncClient(base_url=base,trust_env=False) as client:
                result=await client.post('/v1/chat/completions',json={'model':'shared','messages':[],'stream':streaming})
                assert result.status_code==200
                assert 'OK' in result.text
                if streaming:assert result.text.count('data: [DONE]')==1
                assert seen==[('alpha','a'),('beta','a')]
                assert not r.resilience.peek(r.get_manifest('alpha'),'a')
                assert r.resilience.peek(r.get_manifest('alpha'),'b') is (failure==503)
                assert (await client.get('/v1/models')).status_code==200


@pytest.mark.asyncio
async def test_blocked_known_503_unknown_404_and_no_attempt(monkeypatch):
    r=await registry_for([('alpha','http://127.0.0.1:1')]);router=CascadeRouter(r)
    for model in ('a','b'):router.set_cooldown('alpha',model,100)
    app=create_app(provider_registry=r);app.state.cascade_router=router
    from backend.app.api.v1 import chat
    monkeypatch.setattr(chat,'get_settings',lambda:r.settings)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://test') as c:
        assert (await c.post('/v1/chat/completions',json={'model':'shared','messages':[]})).status_code==503
        assert (await c.post('/v1/chat/completions',json={'model':'missing','messages':[]})).status_code==404
    from backend.app.core.telemetry.store import get_telemetry_store
    trace=(await get_telemetry_store().get_recent())[0]
    assert not trace.attempts


@pytest.mark.asyncio
async def test_parallel_recovery_waits_for_cancel_cleanup():
    r=await registry_for([('alpha','https://upstream.test')]);clock=[1000.]
    r.resilience=ResilienceController(r,clock=lambda:clock[0])
    p=r.get_manifest('alpha');t=r.resilience.acquire(p,'a')
    from backend.app.core.balancer.resilience import HealthOutcome
    r.resilience.finish(t,HealthOutcome('http',503));clock[0]+=60
    entered=asyncio.Event();closing=asyncio.Event();closed=asyncio.Event()
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'data: {"choices":[{"delta":{"content":"OK"}}]}\n\n'
            entered.set();await asyncio.Event().wait()
        async def aclose(self):
            closing.set();await closed.wait()
    async def handler(request):return httpx.Response(200,stream=Stream())
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        router=CascadeRouter(r,OpenAIProviderClient(client))
        stream=await router.route_stream_completion('a',{'messages':[]})
        await stream.__anext__()
        task=asyncio.create_task(stream.aclose());await closing.wait()
        assert r.resilience.acquire(p,'a') is None
        closed.set();await task
        assert not r.resilience.peek(p,'a')
        clock[0]+=60
        assert r.resilience.acquire(p,'a') is not None


@pytest.mark.asyncio
@pytest.mark.parametrize('fault,kind',[('http','http'),('protocol','protocol'),('network','transport'),('local','neutral')])
async def test_origin_classification(fault,kind):
    from backend.app.core.balancer.resilience import HealthOutcome
    r=await registry_for([('alpha','https://upstream.test')]);p=r.get_manifest('alpha')
    def handler(request):
        if fault=='network':raise httpx.ConnectError('sentinel-secret')
        return httpx.Response(502) if fault=='http' else httpx.Response(200,json={'wrong':'shape'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter=OpenAIProviderClient(client)
        if fault=='local':
            def invalid_config(p):raise ValueError('sentinel-secret')
            adapter._get_completions_url=invalid_config
        with pytest.raises(UpstreamProviderError) as error:
            await adapter.complete(p,'a','shared',{'messages':[]})
        assert error.value.failure_kind==kind
        assert 'sentinel-secret' not in str(error.value)


@pytest.mark.asyncio
@pytest.mark.parametrize('late_cost',['0.1',True,'NaN'])
async def test_recovery_finish_then_late_cost_cannot_close(late_cost):
    from backend.tests.test_billing_guard import registry_for as billing_registry,event
    from backend.app.core.balancer.resilience import HealthOutcome
    r=await billing_registry();now=[1000.];r.resilience=ResilienceController(r,clock=lambda:now[0])
    p=r.get_manifest('openrouter');t=r.resilience.acquire(p,'a')
    r.resilience.finish(t,HealthOutcome('http',503));now[0]+=60
    text=event({'content':'ready'})+event({},'stop')+event(cost=late_cost)+'data: [DONE]\n\n'
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,content=text))) as client:
        router=CascadeRouter(r,OpenAIProviderClient(client))
        stream=await router.route_stream_completion('shared',{'messages':[]})
        output=''.join([part async for part in stream])
    gate=r.resilience.routes[(r.eligibility.scope(p),'a')]
    assert gate.state=='OPEN' and gate.streak==1
    assert r.billing.holds and 'ready' in output and output.count('data: [DONE]')==1


@pytest.mark.asyncio
async def test_finish_reason_then_cancel_is_neutral_until_cleaned():
    from backend.tests.test_billing_guard import registry_for as billing_registry,event
    from backend.app.core.balancer.resilience import HealthOutcome
    r=await billing_registry();now=[1000.];r.resilience=ResilienceController(r,clock=lambda:now[0])
    p=r.get_manifest('openrouter');t=r.resilience.acquire(p,'a');r.resilience.finish(t,HealthOutcome('http',503));now[0]+=60
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,content=event({'content':'ready'},'stop')+'data: [DONE]\n\n'))) as client:
        stream=await CascadeRouter(r,OpenAIProviderClient(client)).route_stream_completion('shared',{'messages':[]})
        assert 'ready' in await stream.__anext__()
        await stream.aclose()  # final usage/DONE has not been consumed
    gate=r.resilience.routes[(r.eligibility.scope(p),'a')]
    assert gate.state=='OPEN' and gate.streak==1


@pytest.mark.asyncio
@pytest.mark.parametrize('after_output',[False,True])
async def test_real_socket_preoutput_switch_afteroutput_no_replay(after_output):
    upstream=FastAPI();seen=[]
    @upstream.post('/v1/chat/completions')
    async def completion(request:Request):
        body=await request.json();seen.append(body['model'])
        if body['model']=='a':
            text='data: '+json.dumps({'choices':[{'delta':{'content':'partial'} if after_output else {'role':'assistant'}}]})+'\n\n'
            text+='data: {"error":{"code":503}}\n\n'
        else:text=sse()
        return StreamingResponse(iter([text]),media_type='text/event-stream')
    with serve(upstream) as url:
        r=await registry_for([('alpha',url)])
        stream=await CascadeRouter(r).route_stream_completion('shared',{'messages':[]})
        output=''.join([part async for part in stream])
    assert seen==(['a'] if after_output else ['a','b'])
    assert output.count('data: [DONE]')==(0 if after_output else 1)
    assert ('upstream_stream_error' in output)==after_output


@pytest.mark.asyncio
@pytest.mark.parametrize('status',[401,429,503])
@pytest.mark.parametrize('streaming',[False,True])
@pytest.mark.parametrize('body_failure',['read','oversize','timeout'])
async def test_error_headers_survive_failed_diagnostic_body(status,streaming,body_failure):
    from backend.app.core.balancer.resilience import HealthOutcome
    class Broken(httpx.AsyncByteStream):
        async def __aiter__(self):
            if body_failure=='oversize':yield b'x'*(4*1024*1024+1)
            elif body_failure=='timeout':raise httpx.ReadTimeout('secret')
            else:raise httpx.ReadError('secret')
        async def aclose(self):pass
    r=await registry_for([('alpha','https://upstream.test')]);p=r.get_manifest('alpha')
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req:httpx.Response(status,headers={'Retry-After':'3600'},stream=Broken()))) as client:
        adapter=OpenAIProviderClient(client)
        from backend.app.core.adapters.openai_client import UpstreamRateLimitError
        with pytest.raises((UpstreamProviderError,UpstreamRateLimitError)) as error:
            if streaming:await adapter.stream_complete(p,'a','shared',{}).__anext__()
            else:await adapter.complete(p,'a','shared',{})
        assert error.value.status_code==status and error.value.actual_http_status==status
        assert error.value.failure_kind=='http' and error.value.retry_hint.delay==3600


@pytest.mark.asyncio
@pytest.mark.parametrize('streaming',[False,True])
async def test_malformed_inband_error_is_fixed_protocol_quarantine(streaming):
    r=await registry_for([('alpha','https://upstream.test')]);p=r.get_manifest('alpha');now=[1000.]
    r.resilience=ResilienceController(r,clock=lambda:now[0]);seen=[]
    def handler(request):
        seen.append(request)
        return httpx.Response(200,content='data: {"error":{"message":"bad"}}\n\n') if streaming else httpx.Response(200,json={'error':{'code':'bad'}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        router=CascadeRouter(r,OpenAIProviderClient(client),max_attempts=1)
        for _ in range(2):
            with pytest.raises(UpstreamProviderError):
                if streaming:await router.route_stream_completion('shared',{'messages':[]})
                else:await router.route_completion('shared',{'messages':[]})
            gate=r.resilience.routes[(r.eligibility.scope(p),'a')]
            assert gate.streak==0 and gate.until==now[0]+60
            now[0]+=60
    assert len(seen)==2


@pytest.mark.asyncio
@pytest.mark.parametrize('failure',[httpx.ReadError,httpx.ReadTimeout])
async def test_terminal_transport_failure_delivers_but_updates_future_health(failure):
    from backend.tests.test_billing_guard import event
    class TailFailure(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield event({'content':'ready'},'stop').encode()
            raise failure('secret')
        async def aclose(self):pass
    r=await registry_for([('alpha','https://upstream.test')]);p=r.get_manifest('alpha')
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req:httpx.Response(200,stream=TailFailure()))) as client:
        stream=await CascadeRouter(r,OpenAIProviderClient(client)).route_stream_completion('shared',{'messages':[]})
        output=''.join([part async for part in stream])
    assert 'ready' in output and output.count('data: [DONE]')==1
    assert not r.resilience.peek(p,'a')
    assert r.resilience.routes[(r.eligibility.scope(p),'a')].streak==1
