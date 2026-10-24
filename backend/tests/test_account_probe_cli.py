"""Bounded isolated diagnostic using real upstream and proxy TCP sockets."""
import json
from types import SimpleNamespace
import httpx
import pytest
from fastapi import FastAPI,Request
from fastapi.responses import StreamingResponse
from backend.app.config import Settings
from scripts import probe_multi_provider as cli
from backend.tests.test_account_probes import LoopbackTransport,catalog,buffer,frames


@pytest.mark.asyncio
async def test_explicit_assertion_required_without_any_network(monkeypatch,capsys):
    args=SimpleNamespace(provider_id='groq',confirm_nonbillable_account=False)
    assert await cli.account_probe(args)==1
    assert json.loads(capsys.readouterr().out)['code']=='explicit_nonbillable_assertion_required'


@pytest.mark.asyncio
async def test_isolated_cli_qualification_then_actual_proxy_delivery(monkeypatch,capsys):
    from backend.app.api.v1 import chat
    monkeypatch.setenv('GROQ_API_KEY','synthetic-probe-key')
    settings=Settings(_env_file=None,proxy_master_key=None)
    monkeypatch.setattr(cli,'get_settings',lambda:settings)
    monkeypatch.setattr(chat,'get_settings',lambda:settings)
    app=FastAPI();seen=[]
    @app.get('/{path:path}')
    async def models(path):return catalog()
    @app.post('/{path:path}')
    async def completion(path,request:Request):
        value=await request.json();seen.append(value)
        if value['stream']:
            return StreamingResponse(iter([frames().replace('"role": "assistant"', '"role": "assistant", "tool_calls": null')]),media_type='text/event-stream')
        response=buffer()
        response['choices'][0]['message']['tool_calls']=None
        return response
    original=httpx.AsyncClient
    with cli.serve(app) as url:
        def client_factory(*args,**kwargs):
            if 'event_hooks' in kwargs:
                kwargs['transport']=LoopbackTransport(url)
            return original(*args,**kwargs)
        monkeypatch.setattr(httpx,'AsyncClient',client_factory)
        args=SimpleNamespace(provider_id='groq',confirm_nonbillable_account=True)
        assert await cli.account_probe(args)==0
    lines=capsys.readouterr().out.splitlines()
    report=json.loads(lines[-1])
    assert report['outcome']=='PASS' and report['inference_sends']==4
    assert len(seen)==4 and all(row['max_tokens']==32 for row in seen)
    assert report['primary_activated'] is False
    assert report['cost_reporting']=='unavailable'
    assert len(report['results'])==2 and all(row['passed'] for row in report['results'])
    assert all(row['auth_bound'] for row in report['wire'])


@pytest.mark.asyncio
@pytest.mark.parametrize('bounds',[{'candidate_offset':-1},{'candidate_offset':1000},{'candidate_limit':4},{'candidate_limit':0},{'send_limit':9},{'send_limit':0}])
async def test_invalid_followup_bounds_do_not_load_credentials_or_send(monkeypatch,capsys,bounds):
    def forbidden():pytest.fail('Invalid bounds must fail before loading settings or network')
    monkeypatch.setattr(cli,'get_settings',forbidden)
    args=SimpleNamespace(provider_id='nvidia_nim',confirm_nonbillable_account=True,**bounds)
    assert await cli.account_probe(args)==1
    assert json.loads(capsys.readouterr().out)['code']=='invalid_packet_bounds'
