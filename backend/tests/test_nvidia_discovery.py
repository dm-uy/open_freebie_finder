"""Fresh Free Endpoint narrowing must precede private account qualification."""
import copy

import httpx
import pytest

from backend.app.core.discovery.nvidia import intersect_free_chat, SOURCE_REVISION
from backend.app.core.discovery.orchestrator import DiscoveryOrchestrator, CatalogFailure
from backend.tests.test_account_probes import registry, catalog, nvidia_free_catalog


def test_exact_intersection_rejects_legacy_and_does_not_guess_slug_aliases():
    api=catalog('nvidia_nim',2)
    api['data'].append({'id':'legacy/removed'})
    source=nvidia_free_catalog(1)
    selected=intersect_free_chat(api,source)
    assert [r['id'] for r in selected['data']]==['synthetic/brand-new-0']
    assert selected['data'][0]['nvidia_catalog_source']==SOURCE_REVISION
    source['results'][0]['resources'][0]['name']='brand.new-0'
    assert intersect_free_chat(api,source)=={'data':[]}


@pytest.mark.parametrize('change',['nonchat','paid_only','unavailable','notpreview','private','deprecated','missingavailable'])
def test_free_chat_availability_labels_are_all_required(change):
    source=nvidia_free_catalog();row=source['results'][0]['resources'][0]
    if change=='nonchat':row['labels'][0]['unresolvedValues'].remove('playgroundtype_chat')
    elif change=='paid_only':row['labels'][0]['unresolvedValues'].remove('nim_type_preview')
    elif change=='unavailable':row['attributes'][0]['value']='false'
    elif change=='notpreview':row['attributes'][1]['value']='false'
    elif change=='private':row['isPublic']=False
    elif change=='deprecated':row['attributes'].append({'key':'DEPRECATION','value':'10/27/2026'})
    else:row['attributes']=row['attributes'][1:]
    assert intersect_free_chat(catalog('nvidia_nim'),source)=={'data':[]}


@pytest.mark.parametrize('change',['pages','count','missingrow','conflict','labels','ambiguouspublisher','malformedapi','partialapi'])
def test_partial_or_ambiguous_sources_fail_closed(change):
    source=nvidia_free_catalog();api=catalog('nvidia_nim')
    row=source['results'][0]['resources'][0]
    if change=='pages':source['resultPageTotal']=2
    elif change=='count':source['resultTotal']=2
    elif change=='missingrow':source['results'][0]['resources']=[]
    elif change=='conflict':row['attributes'].append({'key':'AVAILABLE','value':'false'})
    elif change=='labels':row['labels']=None
    elif change=='ambiguouspublisher':row['labels'][1]['values'].append('other')
    elif change=='malformedapi':api['data'].append(None)
    else:api['has_more']=True
    with pytest.raises(CatalogFailure):intersect_free_chat(api,source)


@pytest.mark.asyncio
async def test_public_source_no_key_no_admission_and_failure_revokes_cached_lease(monkeypatch,caplog):
    r,p=registry(monkeypatch,'nvidia_nim');seen=[];failure=[False]
    def handler(req):
        seen.append(req)
        if req.url.host=='api.ngc.nvidia.com':
            assert 'authorization' not in req.headers
            assert 'cookie' not in req.headers and 'x-custom-key' not in req.headers
            assert 'synthetic-probe-key' not in str(req.url)
            return httpx.Response(503 if failure[0] else 200,json=nvidia_free_catalog())
        assert req.headers['authorization']=='Bearer synthetic-probe-key'
        return httpx.Response(200,json=catalog('nvidia_nim'))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler),
            headers={'Authorization':'ambient-secret','X-Custom-Key':'ambient-secret'},
            cookies={'session':'ambient-secret'},auth=('ambient-user','ambient-secret')) as client:
        d=DiscoveryOrchestrator(r,client)
        await d.discover_provider(p)
        c=next(iter(r.accounts.candidates.values()))
        assert r.get_eligible_models()==[] and not c.active
        assert r.accounts.pass_pair(p,c)  # Controlled fixture, not a live pass.
        assert r.get_eligible_models()
        failure[0]=True
        await d.refresh_evidence()
        assert not r.get_eligible_models()
        assert all(req.method=='GET' for req in seen)
        assert 'synthetic-probe-key' not in caplog.text


@pytest.mark.asyncio
async def test_current_source_removal_revokes_and_never_falls_back_to_generic_catalog(monkeypatch):
    r,p=registry(monkeypatch,'nvidia_nim');source=nvidia_free_catalog()
    def handler(req):
        return httpx.Response(200,json=source if req.url.host=='api.ngc.nvidia.com' else catalog('nvidia_nim'))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        d=DiscoveryOrchestrator(r,client);await d.discover_provider(p)
        assert r.accounts.pass_pair(p,next(iter(r.accounts.candidates.values())))
        source['results'][0]['resources'][0]['attributes'][0]['value']='false'
        await d.refresh_evidence()
        assert not r.accounts.candidates and not r.get_eligible_models()


@pytest.mark.asyncio
async def test_oversize_public_source_closes_without_retaining_admission(monkeypatch):
    r,p=registry(monkeypatch,'nvidia_nim')
    from backend.app.core.discovery import orchestrator
    monkeypatch.setattr(orchestrator,'MAX_CATALOG_BYTES',1000)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req:httpx.Response(200,
            json={'large':'x'*1001} if req.url.host=='api.ngc.nvidia.com' else catalog('nvidia_nim')))) as client:
        d=DiscoveryOrchestrator(r,client);await d.discover_provider(p)
        assert d.statuses[p.id].code=='response_too_large' and not r.accounts.candidates


def test_scored_teaser_is_not_a_second_page_and_live_snapshot_contract():
    source=nvidia_free_catalog()
    source['results'].insert(0,{'groupValue':'_scored','totalCount':1,'resources':copy.deepcopy(source['results'][0]['resources'])})
    assert len(intersect_free_chat(catalog('nvidia_nim'),source)['data'])==1
