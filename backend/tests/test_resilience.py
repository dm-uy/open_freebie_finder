"""T-009 measured-clock admission and origin-classification contracts."""
from datetime import datetime, timezone
from email.utils import format_datetime
from types import SimpleNamespace
import pytest
from backend.app.core.balancer.resilience import ResilienceController, HealthOutcome, RetryHint, retry_hint
from backend.app.config import Settings


class Registry:
    def __init__(self):
        self.settings=SimpleNamespace(circuit_breaker_cooldown_seconds=60)
        self.key='sentinel-secret'
        self.epoch=1
        self.manifest=SimpleNamespace(id='p',base_url='https://example.test/v1',auth=SimpleNamespace(type='bearer',custom_header_name=None,api_key_env='KEY'))
        self.eligibility=SimpleNamespace(scope=lambda p: (p.id,'endpoint',self.epoch,'profile'))
    def credential(self,p): return self.key
    def get_manifest(self,p): return self.manifest if p=='p' else None
    def get_manifests(self): return [self.manifest]


@pytest.fixture
def system():
    registry=Registry(); now=[1000.0]
    return registry,ResilienceController(registry,clock=lambda:now[0]),now


def test_backoff_single_recovery_and_stale_generation(system):
    r,c,now=system
    a=c.acquire(r.manifest,'m');b=c.acquire(r.manifest,'m')
    c.finish(a,HealthOutcome('http',503));c.finish(b,HealthOutcome('success'))
    assert not c.peek(r.manifest,'m')
    for delay in [60,120,240,480,900,900]:
        gate=c.routes[(c.scopes['p'],'m')]
        assert gate.until==now[0]+delay
        now[0]+=delay
        assert c.peek(r.manifest,'m') and c.peek(r.manifest,'m')
        t=c.acquire(r.manifest,'m');assert t is not None
        assert c.acquire(r.manifest,'m') is None
        if delay==900 and gate.streak==6:
            c.finish(t,HealthOutcome('success'));break
        c.finish(t,HealthOutcome('transport'))
    assert c.peek(r.manifest,'m')
    assert gate.streak==0


def test_auth_survives_service_generation_catalog_epoch_and_key_restore(system):
    r,c,now=system
    a=c.acquire(r.manifest,'a');b=c.acquire(r.manifest,'a')
    c.finish(a,HealthOutcome('http',503))
    c.finish(b,HealthOutcome('http',401))
    r.epoch+=1
    assert not c.peek(r.manifest,'other')
    r.key='different';r.epoch+=1
    assert c.acquire(r.manifest,'other')
    r.key='sentinel-secret';r.epoch+=1
    assert not c.peek(r.manifest,'other')
    assert 'sentinel-secret' not in str(c.snapshot())


def test_stale_identity_401_does_not_block_new_key(system):
    r,c,now=system;t=c.acquire(r.manifest,'a')
    r.key='new';r.epoch+=1
    c.finish(t,HealthOutcome('http',401))
    assert c.peek(r.manifest,'a')


def test_shared_quota_recovery_private_and_neutral_cleanup(system):
    r,c,now=system;t=c.acquire(r.manifest,'a')
    c.finish(t,HealthOutcome('http',429,RetryHint(3600)))
    assert not c.peek(r.manifest,'b',private=True)
    now[0]+=3600
    t=c.acquire(r.manifest,'pending',private=True)
    assert t and c.acquire(r.manifest,'b') is None
    c.finish(t)  # cancellation: no reset or streak increment
    assert not c.peek(r.manifest,'a')
    now[0]+=60
    t=c.acquire(r.manifest,'pending',private=True);assert t
    c.finish(t,HealthOutcome('success'))
    assert c.peek(r.manifest,'a')


def test_financial_priority_and_capacity(system):
    r,c,now=system;t=c.acquire(r.manifest,'a');c.finish(t,HealthOutcome('http',401),financial=True)
    assert c.peek(r.manifest,'b')
    c.route_limit=1
    t=c.acquire(r.manifest,'a');c.finish(t,HealthOutcome('http',503))
    assert c.acquire(r.manifest,'b') is None
    assert c.snapshot()['capacity_rejections']==1


@pytest.mark.parametrize('values,delay,deferred',[
    (None,0,False),(['0'],0,False),(['3600'],3600,False),(['86401'],0,True),
    (['9'*256],0,True),(['x'*257],0,True),(['5','6'],0,False),(['bad'],0,False),
    (['-1'],0,False),(['1.5'],0,False),(['∞'],0,False),
    ([format_datetime(datetime.fromtimestamp(4600,timezone.utc),usegmt=True)],3600,False),
])
def test_retry_after(values,delay,deferred):
    hint=retry_hint(values,wall=1000)
    assert (hint.delay,hint.deferred)==(delay,deferred)


@pytest.mark.parametrize('value',[0,301,True,1.5,'x'])
def test_strict_settings(value):
    with pytest.raises(ValueError):Settings(_env_file=None,circuit_breaker_cooldown_seconds=value)


def test_deferred_never_retries_early_and_duplicate_finish_inert(system):
    r,c,now=system;t=c.acquire(r.manifest,'a')
    c.finish(t,HealthOutcome('http',429,retry_hint('86401')))
    before=c.snapshot();c.finish(t,HealthOutcome('success'))
    assert c.snapshot()==before
    now[0]+=999999
    assert not c.peek(r.manifest,'b')


def test_route_epoch_obsolete_and_auth_binding_stale(system):
    r,c,now=system;t=c.acquire(r.manifest,'a')
    r.epoch+=1;r.manifest.base_url='https://other.test/v1'
    c.finish(t,HealthOutcome('http',401))
    assert c.peek(r.manifest,'a')
    t=c.acquire(r.manifest,'a');r.epoch+=1
    c.finish(t,HealthOutcome('http',503))
    assert c.peek(r.manifest,'a')


def test_protocol_quarantine_not_exponential_and_billing_recovery_neutral(system):
    r,c,now=system;t=c.acquire(r.manifest,'a');c.finish(t,HealthOutcome('protocol'))
    gate=c.routes[(c.scopes['p'],'a')]
    assert gate.streak==0 and gate.until==1060
    now[0]+=60;t=c.acquire(r.manifest,'a')
    c.finish(t,HealthOutcome('success'),financial=True)
    assert not c.peek(r.manifest,'a') and gate.streak==0
    now[0]+=60;t=c.acquire(r.manifest,'a');c.finish(t,HealthOutcome('success'))
    assert c.peek(r.manifest,'a')


def test_independent_quota_generation_after_route_failure(system):
    r,c,now=system;a=c.acquire(r.manifest,'a');b=c.acquire(r.manifest,'a')
    c.finish(a,HealthOutcome('http',503));c.finish(b,HealthOutcome('http',429))
    assert not c.peek(r.manifest,'b')


def test_retry_date_past_and_boundary():
    assert retry_hint(['Thu, 01 Jan 1970 00:00:00 GMT'],wall=1000).delay==0
    assert retry_hint(['86400']).delay==86400


def test_budget_rollback_does_not_postpone_recovery(system):
    r,c,now=system;t=c.acquire(r.manifest,'a');c.finish(t,HealthOutcome('http',429));now[0]+=60
    t=c.acquire(r.manifest,'a',private=True);c.rollback(t)
    assert c.acquire(r.manifest,'a',private=True) is not None


def test_capacity_never_evicts_auth_and_router_scopes(system):
    r,c,now=system;c.credential_limit=2
    t=c.acquire(r.manifest,'a');c.finish(t,HealthOutcome('http',401))
    r.key='different';r.epoch+=1
    assert c.acquire(r.manifest,'a') is None
    r.key='sentinel-secret';r.epoch+=1
    assert not c.peek(r.manifest,'a')
