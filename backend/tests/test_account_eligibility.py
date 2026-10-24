"""Account assurance, scope revocation and independent freshness contracts."""
import asyncio
import pytest
from pydantic import ValidationError
from backend.app.config import Settings
from backend.app.core.providers.registry import ProviderRegistry
from backend.app.core.providers.models import DiscoveredModel
from backend.app.core.eligibility.account import LEASE_SECONDS


def setup(monkeypatch, confirmed=True):
    monkeypatch.setenv('GROQ_API_KEY', 'synthetic-account-key')
    settings=Settings(_env_file=None, free_account_confirmations=['groq'] if confirmed else [])
    r=ProviderRegistry(settings=settings)
    return r,r.get_manifest('groq')


def snapshot(r,p,ids=('new-a',),metadata=None):
    s=r.eligibility.scope(p)
    r.eligibility.publish(p,{m:metadata or {} for m in ids},s)
    return r.accounts.candidates[(p.id,ids[0])]


@pytest.mark.parametrize('bad', [['openrouter'],['google_gemini'],['groq','groq'],[True],[1],['GROQ'],'groq',{},None])
def test_strict_confirmations(bad):
    with pytest.raises((ValidationError,ValueError)):
        Settings(_env_file=None,free_account_confirmations=bad)


def test_default_off_and_legacy_flags_cannot_admit(monkeypatch):
    r,p=setup(monkeypatch,False)
    p.free_access_confirmed=True
    p.chat_model_allowlist=['new-a']
    c=snapshot(r,p)
    assert not r.accounts.pass_pair(p,c)
    assert r.eligibility.get(p,'new-a').verdict.reason=='assertion_required'
    assert Settings(_env_file=None).free_account_confirmations==[]


@pytest.mark.asyncio
async def test_pending_not_routable_legacy_model_list_ignored_after_pair(monkeypatch):
    r,p=setup(monkeypatch)
    p.chat_model_allowlist=['obsolete-model']
    c=snapshot(r,p)
    await r.register_models([DiscoveredModel(id='new-a',canonical_name='provider:groq/new-a',provider_id='groq')])
    assert r.get_eligible_models()==[]
    assert r.accounts.pass_pair(p,c)
    assert [m.id for m in r.get_eligible_models()]==['new-a']
    evidence=r.eligibility.get(p,'new-a')
    assert evidence.verdict.basis=='user_confirmed_account_probe'
    assert evidence.verdict.assurance=='user_asserted'
    assert not evidence.verdict.tools


@pytest.mark.asyncio
async def test_scope_change_revokes_even_if_key_restored_and_late_result(monkeypatch):
    r,p=setup(monkeypatch)
    c=snapshot(r,p)
    assert r.accounts.pass_pair(p,c)
    monkeypatch.setenv('GROQ_API_KEY','different-synthetic-key')
    r.accounts.observe()
    assert r.eligibility.get(p,'new-a') is None
    monkeypatch.setenv('GROQ_API_KEY','synthetic-account-key')
    snapshot(r,p)
    assert not r.accounts.pass_pair(p,c)
    assert r.accounts.assertion_reason(p)=='credential_revoked'


def test_setting_toggle_does_not_reconfirm_or_clear_financial_hold(monkeypatch):
    r,p=setup(monkeypatch)
    c=snapshot(r,p)
    r.billing.hold(c.scope,'unexpected_paid_cost')
    r.settings.free_account_confirmations=[]
    r.accounts.observe()
    r.settings.free_account_confirmations=['groq']
    assert not r.accounts.pass_pair(p,c)
    assert r.billing.diagnostics(c.scope)['latched']


def test_fresh_catalog_cannot_renew_availability_or_failed_pass(monkeypatch):
    clock=[100.]
    monkeypatch.setattr('backend.app.core.eligibility.account.time.monotonic',lambda:clock[0])
    r,p=setup(monkeypatch)
    c=snapshot(r,p)
    assert r.accounts.pass_pair(p,c)
    clock[0]+=LEASE_SECONDS+1
    snapshot(r,p)
    assert r.eligibility.get(p,'new-a').verdict.state=='unknown'
    assert r.accounts.pass_pair(p,c)
    r.accounts.fail_pair(p,c,403)
    snapshot(r,p)
    assert r.eligibility.get(p,'new-a').verdict.state=='unknown'
    assert c.retry_at==clock[0]+3600


def test_pool_replacement_and_cache_recovery_respect_capacity(monkeypatch):
    r,p=setup(monkeypatch)
    ids=tuple(f'model-{i}' for i in range(7))
    snapshot(r,p,ids)
    cs=[r.accounts.candidates[(p.id,i)] for i in ids]
    for c in cs[:5]:assert r.accounts.pass_pair(p,c)
    r.accounts.fail_pair(p,cs[5])
    assert sum(c.active for c in cs)==5
    assert r.accounts.pass_pair(p,cs[6])
    assert sum(c.active for c in cs)==5
    r.accounts.invalidate_source(p.id)
    snapshot(r,p,ids)
    assert sum(c.active for c in cs)==5


def test_source_removal_and_capability_changes_invalidate_pass(monkeypatch):
    r,p=setup(monkeypatch)
    c=snapshot(r,p)
    assert r.accounts.pass_pair(p,c)
    replacement=snapshot(r,p,metadata={'capabilities':{'function_calling':True}})
    assert replacement is not c and not r.accounts.pass_pair(p,c)
    assert r.eligibility.get(p,'new-a').verdict.state=='unknown'
    snapshot(r,p,ids=('new-b',))
    assert r.eligibility.get(p,'new-a') is None
