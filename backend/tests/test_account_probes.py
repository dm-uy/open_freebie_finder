"""Probe wire framing, bounded admission and cancellation/guard races."""
import asyncio
import json
import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from backend.app.config import Settings
from backend.app.core.providers.registry import ProviderRegistry
from backend.app.core.discovery.orchestrator import DiscoveryOrchestrator, CatalogFailure
from backend.app.core.eligibility.probes import ProbeWorker, ProbeBudget
from backend.app.core.adapters.openai_client import OpenAIProviderClient
from scripts.probe_multi_provider import serve


def registry(monkeypatch, identifier='groq'):
    from backend.app.core.eligibility.account import PROFILES
    monkeypatch.setenv(PROFILES[identifier][3],'synthetic-probe-key')
    r=ProviderRegistry(settings=Settings(_env_file=None,free_account_confirmations=[identifier]))
    return r,r.get_manifest(identifier)


def catalog(identifier='groq', count=1):
    return {'data':[{'id':('synthetic/' if identifier=='nvidia_nim' else '')+f'brand-new-{i}', 'capabilities':{'completion_chat':True,'function_calling':True},
        'architecture':{'output_modalities':['text'],'input_modalities':['text']},
        **({'providers':[{'provider':'synthetic-provider','status':'live','supports_tools':True}]} if identifier=='huggingface' else {})} for i in range(count)]}


def nvidia_free_catalog(count=1):
    rows=[{'resourceType':'ENDPOINT','resourceId':f'public/brand-new-{i}', 'isPublic':True,
        'name':f'brand-new-{i}', 'labels':[
            {'key':'general','unresolvedValues':['nim_type_preview','playgroundtype_chat']},
            {'key':'publisher','values':['synthetic']}],
        'attributes':[{'key':'AVAILABLE','value':'true'},{'key':'PREVIEW','value':'true'}]} for i in range(count)]
    return {'resultTotal':count,'resultPageTotal':1,'results':[{'groupValue':'ENDPOINT','totalCount':count,'resources':rows}]}


def buffer(content='2', **changes):
    return {'choices':[{'index':0,'message':{'role':'assistant','content':content},'finish_reason':'stop'}],
            'usage':{'completion_tokens':1},**changes}


def frames(content='2', terminal=True, done=True):
    parts=[{'choices':[{'index':0,'delta':{'role':'assistant'}}]},
           {'choices':[{'index':0,'delta':{'content':content},'finish_reason':'stop' if terminal else None}]}]
    return ''.join('data: '+json.dumps(v)+'\n\n' for v in parts)+('data: [DONE]\n\n' if done else '')


async def pending(r,p,client):
    d=DiscoveryOrchestrator(r,client)
    await d.discover_provider(p)
    return next(c for (provider,_),c in r.accounts.candidates.items() if provider==p.id)


class LoopbackTransport(httpx.AsyncBaseTransport):
    """Exercise actual sockets while retaining production source/dispatch binding."""
    def __init__(self,url):
        self.url=url
        self.transport=httpx.AsyncHTTPTransport(trust_env=False)
    async def handle_async_request(self,request):
        forwarded=httpx.Request(request.method,self.url+request.url.path,
            headers={k:v for k,v in request.headers.items() if k.lower()!='host'}, content=await request.aread())
        return await self.transport.handle_async_request(forwarded)
    async def aclose(self):await self.transport.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize('identifier',['groq','nvidia_nim','mistral','huggingface'])
async def test_four_profiles_real_socket_pair_and_dynamic_route(monkeypatch,identifier):
    r,p=registry(monkeypatch,identifier)
    upstream=FastAPI()
    seen=[]
    @upstream.get('/{path:path}')
    async def models(path):
        return nvidia_free_catalog() if path.startswith('v2/search/') else catalog(identifier)
    @upstream.post('/{path:path}')
    async def completion(path,request:Request):
        value=await request.json();seen.append((path,request.headers.get('authorization'),value))
        if value['stream']:return StreamingResponse(iter([frames()]),media_type='text/event-stream')
        return buffer()
    with serve(upstream) as url:
        async with httpx.AsyncClient(transport=LoopbackTransport(url),trust_env=False) as client:
            c=await pending(r,p,client)
            w=ProbeWorker(r,OpenAIProviderClient(client))
            from backend.app.core.telemetry.store import get_telemetry_store
            await get_telemetry_store().clear()
            assert r.get_eligible_models()==[]
            assert await w.qualify(p,c)
            assert await get_telemetry_store().get_recent()==[]
            assert len(r.get_eligible_models())==1
            assert len(seen)==2
            from backend.app.core.balancer.router import CascadeRouter
            router=CascadeRouter(r,OpenAIProviderClient(client),max_attempts=1)
            canonical=r.get_eligible_models()[0].canonical_name
            result=await router.route_completion(canonical,{'messages':[{'role':'user','content':'1+1=?'}],'max_tokens':32})
            assert result['model']==canonical
            stream=await router.route_stream_completion(canonical,{'messages':[{'role':'user','content':'1+1=?'}],'max_tokens':32})
            content=''.join([chunk async for chunk in stream])
            assert content.count('data: [DONE]')==1
            assert len(seen)==4
            for path,auth,value in seen:
                assert path.endswith('/chat/completions') and auth=='Bearer synthetic-probe-key'
                assert value['max_tokens']==32 and value['messages'][0]['content']=='1+1=?'
                assert set(value)=={'model','messages','stream','max_tokens'}
                assert value['model']==c.model_id
                if identifier=='huggingface':assert value['model'].endswith(':synthetic-provider')
            assert not r.billing.active and not w.permits


@pytest.mark.asyncio
@pytest.mark.parametrize('broken',[frames('',True,True),frames('2',False,True),frames('2',True,False),frames()+'data: [DONE]\n\n',frames().replace('"content": "2"','"tool_calls": [{"id":"x"}]')])
async def test_raw_sse_must_complete_once_with_visible_text(monkeypatch,broken):
    r,p=registry(monkeypatch)
    def handle(req):
        if req.method=='GET':return httpx.Response(200,json=catalog())
        return httpx.Response(200,text=broken) if json.loads(req.content)['stream'] else httpx.Response(200,json=buffer())
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        c=await pending(r,p,client)
        w=ProbeWorker(r,OpenAIProviderClient(client))
        assert not await w.qualify(p,c)
        assert r.get_eligible_models()==[]
        assert not r.billing.active


@pytest.mark.asyncio
@pytest.mark.parametrize('broken',[buffer(None),buffer(''),buffer('2',usage={'completion_tokens':33}),buffer('2',choices=[{'message':{'content':'2','audio':{'x':'bad'}},'finish_reason':'stop'}])])
async def test_failed_buffered_does_not_send_sse(monkeypatch,broken):
    r,p=registry(monkeypatch)
    seen=[]
    def handle(req):
        if req.method=='GET':return httpx.Response(200,json=catalog())
        seen.append(req);return httpx.Response(200,json=broken)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        c=await pending(r,p,client)
        assert not await ProbeWorker(r,OpenAIProviderClient(client)).qualify(p,c)
        assert len(seen)==1 and not c.active


@pytest.mark.asyncio
async def test_scope_change_cancels_inflight_and_shutdown_awaits(monkeypatch):
    r,p=registry(monkeypatch)
    entered=asyncio.Event()
    async def handle(req):
        if req.method=='GET':return httpx.Response(200,json=catalog())
        entered.set();await asyncio.Event().wait()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        c=await pending(r,p,client);w=ProbeWorker(r,OpenAIProviderClient(client))
        task=asyncio.create_task(w.qualify(p,c))
        await asyncio.wait_for(entered.wait(),1)
        monkeypatch.setenv('GROQ_API_KEY','changed-key')
        r.accounts.observe()
        with pytest.raises(asyncio.CancelledError):await task
        assert not r.billing.active and not r.accounts.inflight and not w.permits


@pytest.mark.asyncio
async def test_consumer_balance_hold_forbids_automatic_recovery_after_expiry(monkeypatch):
    r,p=registry(monkeypatch)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req:httpx.Response(200,json=catalog()))) as client:
        c=await pending(r,p,client);w=ProbeWorker(r,OpenAIProviderClient(client))
        r.billing.hold(c.scope,'insufficient_balance_or_budget',retry_after='1')
        r.billing.holds[c.scope].expires_at=0
        assert w.select(p) is None
        assert not await w.qualify(p,c)
        assert len(w.budget.events)==0


def test_sliding_budgets_partitions_and_no_credential_reset():
    clock=[0.];b=ProbeBudget(lambda:clock[0])
    assert b.reserve('a','new') and b.reserve('a','new')
    assert not b.reserve('a','new')
    assert b.reserve('b','new') and b.reserve('b','new')
    assert not b.reserve('c','new')
    for i in range(60):
        clock[0]+=61;assert b.reserve(str(i%4),'new')
    clock[0]+=61
    assert not b.reserve('new-credential','new')
    for i in range(128):
        clock[0]+=61;assert b.reserve(str(i%4),'renewal')
    clock[0]+=61
    assert not b.reserve('new-credential','renewal')
    clock[0]+=86400
    assert b.reserve('a','new')


def test_catalog_negative_capability_collision_and_overflow(monkeypatch):
    r,p=registry(monkeypatch,'huggingface');d=DiscoveryOrchestrator(r)
    data=catalog('huggingface')
    data['data'][0]['providers'].append({'provider':'second-provider','status':'live'})
    _,models=d._parse(p,data)
    assert len(models)==2 and len({m.canonical_name for m in models})==1
    data['data'][0]['providers'].append({'provider':'second-provider','status':'error'})
    with pytest.raises(CatalogFailure):d._parse(p,data)
    data=catalog('huggingface');data['data'][0]['architecture']['output_modalities']=['text','audio']
    assert d._parse(p,data)[1]==[]
    with pytest.raises(CatalogFailure):d._parse(p,catalog('huggingface',1001))


def test_semantic_data_after_terminal_cannot_qualify():
    from backend.app.core.eligibility.protocol import ProbeProtocol
    p=ProbeProtocol()
    p.event(json.dumps({'choices':[{'delta':{},'finish_reason':'stop'}]}))
    p.event(json.dumps({'choices':[{'delta':{'content':'too late'}}]}))
    p.event('[DONE]')
    assert not p.passed


@pytest.mark.asyncio
async def test_budget_exhaustion_defers_without_destroying_valid_lease(monkeypatch):
    r,p=registry(monkeypatch)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req:httpx.Response(200,json=catalog()))) as client:
        c=await pending(r,p,client);w=ProbeWorker(r,OpenAIProviderClient(client))
        assert r.accounts.pass_pair(p,c)
        prior=c.passed_at
        for _ in range(2):assert w.budget.reserve(p.id,'new')
        assert not await w.qualify(p,c)
        assert c.active and c.passed_at==prior


def test_partition_exhaustion_does_not_starve_due_renewals(monkeypatch):
    from backend.tests.test_account_eligibility import setup,snapshot
    import time
    r,p=setup(monkeypatch)
    ids=('renewal',)+tuple(f'pending-{i}' for i in range(80))
    snapshot(r,p,ids)
    c=r.accounts.candidates[(p.id,'renewal')]
    r.accounts.pass_pair(p,c)
    c.passed_at=time.monotonic()-43201
    c.retry_at=0
    # Keep a source-fresh, still-valid lease while all exploration quota is used.
    w=ProbeWorker(r)
    now=time.monotonic()
    w.budget.events.extend((now-100-i,'groq' if i%4==0 else str(i%4),'new') for i in range(64))
    assert w.select(p) is c
    assert not w.budget.can_reserve(p.id,'new')


@pytest.mark.asyncio
async def test_recognized_financial_incident_aborts_pair_before_next_mode(monkeypatch):
    r,p=registry(monkeypatch);seen=[]
    def handle(req):
        if req.method=='GET':return httpx.Response(200,json=catalog())
        seen.append(req);return httpx.Response(200,json=buffer())
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        c=await pending(r,p,client)
        def documented_incident(handle,profile,data):
            r.billing.hold(handle.scope,'unexpected_paid_cost')
            return 'positive'
        monkeypatch.setattr(r.billing,'inspect_cost',documented_incident)
        w=ProbeWorker(r,OpenAIProviderClient(client))
        assert not await w.qualify(p,c)
        assert len(seen)==1 and not c.active and not r.billing.active
        assert r.billing.diagnostics(c.scope)['latched']
        assert w.select(p) is None


@pytest.mark.asyncio
async def test_undocumented_cost_field_does_not_invent_effective_charge(monkeypatch):
    r,p=registry(monkeypatch)
    def handle(req):
        if req.method=='GET':return httpx.Response(200,json=catalog())
        return httpx.Response(200,text=frames()) if json.loads(req.content)['stream'] else httpx.Response(200,json=buffer(usage={'cost':123,'completion_tokens':1}))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        c=await pending(r,p,client);w=ProbeWorker(r,OpenAIProviderClient(client))
        assert await w.qualify(p,c)
        assert all(row['cost_status']=='unavailable' for row in w.history)
        assert not r.billing.holds


def test_declared_negative_capability_and_changed_binding_stay_revoked(monkeypatch):
    r,p=registry(monkeypatch);d=DiscoveryOrchestrator(r)
    data=catalog();data['data'][0]['capabilities']['completion_chat']=False
    assert d._parse(p,data)[1]==[]
    p.discovery.type='manual'
    assert r.accounts.assertion_reason(p)=='credential_revoked'
    p.discovery.type='all_available'
    assert r.accounts.assertion_reason(p)=='credential_revoked'


def test_recreated_worker_keeps_runtime_quota(monkeypatch):
    r,p=registry(monkeypatch)
    first=ProbeWorker(r)
    assert first.budget.reserve(p.id,'new') and first.budget.reserve(p.id,'new')
    second=ProbeWorker(r)
    assert second.budget is first.budget
    assert not second.budget.reserve(p.id,'new')


@pytest.mark.parametrize('calls',[None,[]])
def test_nullable_absent_tool_calls_are_valid_text_not_tools(calls):
    from backend.app.core.adapters.openai_client import valid_completion
    from backend.app.core.eligibility.protocol import ProbeProtocol
    data=buffer()
    data['choices'][0]['message']['tool_calls']=calls
    assert valid_completion(data)
    p=ProbeProtocol();p.buffered(data)
    assert p.passed
    data['choices'][0]['message']['tool_calls']=[{'type':'function'}]
    assert not valid_completion(data)


@pytest.mark.asyncio
async def test_hf_hold_blocks_all_exact_provider_rows(monkeypatch):
    r,p=registry(monkeypatch,'huggingface')
    data=catalog('huggingface')
    data['data'][0]['providers'].append({'provider':'other-provider','status':'live'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req:httpx.Response(200,json=data))) as client:
        await pending(r,p,client)
        rows=list(r.accounts.candidates.values())
        for c in rows:assert r.accounts.pass_pair(p,c)
        assert len(r.get_eligible_models())==2
        r.billing.hold(rows[0].scope,'unexpected_paid_cost')
        assert rows[0].scope==rows[1].scope and r.get_eligible_models()==[]


@pytest.mark.asyncio
async def test_cumulative_sse_body_bound_closes_and_never_admits(monkeypatch):
    import backend.app.core.adapters.openai_client as adapter
    r,p=registry(monkeypatch);closed=[]
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            for _ in range(20):
                yield b'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n'
            yield frames().encode()
        async def aclose(self):closed.append(True)
    def handle(req):
        if req.method=='GET':return httpx.Response(200,json=catalog())
        if json.loads(req.content)['stream']:return httpx.Response(200,stream=Stream())
        return httpx.Response(200,json=buffer())
    monkeypatch.setattr(adapter,'MAX_RESPONSE_BYTES',512)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        c=await pending(r,p,client)
        assert not await ProbeWorker(r,OpenAIProviderClient(client)).qualify(p,c)
        assert closed and not r.billing.active and r.get_eligible_models()==[]


@pytest.mark.asyncio
async def test_global_two_pairs_and_one_per_credential_owned_cancellation(monkeypatch):
    from backend.app.core.eligibility.account import PROFILES
    names=['groq','nvidia_nim','mistral']
    for name in names:monkeypatch.setenv(PROFILES[name][3],'synthetic-probe-key')
    r=ProviderRegistry(settings=Settings(_env_file=None,free_account_confirmations=names))
    entered=[];block=asyncio.Event()
    async def handle(req):
        if req.method=='GET':
            data=(nvidia_free_catalog() if req.url.host=='api.ngc.nvidia.com'
                  else catalog('nvidia_nim' if req.url.host=='integrate.api.nvidia.com' else 'groq'))
            return httpx.Response(200,json=data)
        entered.append(req.url.host)
        await block.wait()
        return httpx.Response(200,json=buffer())
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        pairs=[]
        for name in names:
            p=r.get_manifest(name);c=await pending(r,p,client);pairs.append((p,c))
        w=ProbeWorker(r,OpenAIProviderClient(client))
        tasks=[asyncio.create_task(w.qualify(p,c)) for p,c in pairs]
        async with asyncio.timeout(1):
            while len(entered)<2:await asyncio.sleep(.001)
        assert await tasks[2] is False
        assert not await w.qualify(*pairs[0])
        assert len(entered)==2 and len(r.billing.active)==2
        for task in tasks:task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        assert not r.billing.active and not r.accounts.inflight and not w.permits


@pytest.mark.asyncio
async def test_absolute_deadline_aborts_owned_io_without_second_send(monkeypatch):
    r,p=registry(monkeypatch);sends=[]
    async def handle(req):
        if req.method=='GET':return httpx.Response(200,json=catalog())
        sends.append(req)
        await asyncio.Event().wait()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        c=await pending(r,p,client);w=ProbeWorker(r,OpenAIProviderClient(client))
        original=asyncio.timeout;deadlines=[]
        def short_deadline(seconds):
            deadlines.append(seconds)
            return original(.01 if seconds>1 else seconds)
        monkeypatch.setattr(asyncio,'timeout',short_deadline)
        assert not await w.qualify(p,c)
        assert len(sends)==1 and 30 in deadlines
        assert not r.billing.active and not r.accounts.inflight and not c.active


def test_probe_diagnostic_shapes_never_echo_upstream_identifiers_or_content():
    from backend.app.core.eligibility.protocol import safe_probe_diagnostics
    secret='private-sentinel-do-not-echo'
    data={'detail':'Function '+secret+' not found for account '+secret,
          'choices':[{'message':{'content':secret,'tool_calls':None},'finish_reason':'stop'}],
          'unknown_'+secret:secret}
    shape=safe_probe_diagnostics(data)
    assert shape['error_contract']=='function_not_found_for_account'
    assert shape['content_kind']=='string' and shape['visible_text']
    assert secret not in json.dumps(shape)
    assert safe_probe_diagnostics(None,non_json_body=b'404 page not found\n')['error_contract']=='plain_page_not_found'


@pytest.mark.asyncio
async def test_non_json_provider_404_has_safe_diagnostics_and_no_sse(monkeypatch):
    r,p=registry(monkeypatch,'nvidia_nim');seen=[]
    def handle(req):
        if req.method=='GET':return httpx.Response(200,json=nvidia_free_catalog() if req.url.host=='api.ngc.nvidia.com' else catalog('nvidia_nim'))
        seen.append(req);return httpx.Response(404,text='404 page not found\n')
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        c=await pending(r,p,client);w=ProbeWorker(r,OpenAIProviderClient(client))
        assert not await w.qualify(p,c)
        assert len(seen)==1
        assert w.history[-1]['diagnostics']['error_contract']=='plain_page_not_found'
        assert r.get_eligible_models()==[]


@pytest.mark.asyncio
async def test_nvidia_missing_function_negative_cache_does_not_disable_other_routes(monkeypatch):
    import time
    r,p=registry(monkeypatch,'nvidia_nim')
    def handler(req):
        data=nvidia_free_catalog(2) if req.url.host=='api.ngc.nvidia.com' else catalog('nvidia_nim',count=2)
        return httpx.Response(200,json=data)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await pending(r,p,client)
        first,second=list(r.accounts.candidates.values())
        r.accounts.fail_pair(p,first,404,diagnostics={'error_contract':'function_not_found_for_account'})
        assert first.retry_at-time.monotonic()>3599
        assert first.reason=='incompatible'
        assert r.accounts.pass_pair(p,second)
        assert not r.billing.holds and p.id not in r.accounts.suspended
        assert len(r.get_eligible_models())==1
        assert r.accounts.diagnostics(p)['reasons']['incompatible']==1


@pytest.mark.asyncio
async def test_provider_rotation_survives_minute_budget_poll_phase_lock(monkeypatch):
    """Ten manifests and60 one-second polls must not starve the third account."""
    r=ProviderRegistry(settings=Settings(_env_file=None))
    worker=ProbeWorker(r)
    accounts=r.accounts
    allowed={'groq','mistral','nvidia_nim'}
    slots=[2];ticks=[0];launched=[];idle_cursors=[]
    def select(manifest):
        return object() if manifest.id in allowed and slots[0]>0 else None
    async def qualify(manifest,candidate):
        slots[0]-=1
        launched.append(manifest.id)
        accounts.inflight.pop(manifest.id,None)
    stop=asyncio.Event()
    async def poll(awaitable,timeout):
        awaitable.close()
        await asyncio.sleep(0)
        ticks[0]+=1
        if ticks[0] in {1,59}:idle_cursors.append(worker.provider_cursor)
        if ticks[0] in {60,120}:slots[0]=2
        if ticks[0]>=122:stop.set()
        raise TimeoutError
    monkeypatch.setattr(worker,'select',select)
    monkeypatch.setattr(worker,'qualify',qualify)
    monkeypatch.setattr(asyncio,'wait_for',poll)
    await worker.run(stop)
    assert launched[:2]==['groq','mistral']
    assert 'nvidia_nim' in launched[2:4], launched
    assert idle_cursors[0]==idle_cursors[1]
    assert launched==['groq','mistral','nvidia_nim','groq','mistral','nvidia_nim']
