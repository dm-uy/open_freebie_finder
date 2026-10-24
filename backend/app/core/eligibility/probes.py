"""Bounded private qualification, separate from public routing and telemetry."""
import asyncio
from collections import deque
from dataclasses import dataclass, field
import time

from backend.app.core.balancer.resilience import HealthOutcome, retry_hint
from backend.app.core.eligibility.account import RENEW_SECONDS
from backend.app.core.eligibility.request import prepare_dispatch


class ProbeBudget:
    """Atomic event-loop reservations; all attempted sends consume local budget."""
    def __init__(self, clock=None):
        self.clock = clock or time.monotonic
        self.events = deque()

    def can_reserve(self, provider, partition):
        now = self.clock()
        while self.events and self.events[0][0] <= now - 86400:
            self.events.popleft()
        recent = [e for e in self.events if e[0] > now - 60]
        if (len(self.events) >= 192 or sum(e[1] == provider for e in self.events) >= 96
                or sum(e[2] == partition for e in self.events) >= (128 if partition == 'renewal' else 64)
                or len(recent) >= 4 or sum(e[1] == provider for e in recent) >= 2):
            return False
        return True

    def reserve(self, provider, partition):
        if not self.can_reserve(provider, partition):
            return False
        self.events.append((self.clock(), provider, partition))
        return True


@dataclass(frozen=True, repr=False)
class ProbePermit:
    worker: object
    manifest: object
    candidate: object
    partition: str
    mode: bool
    deadline: float
    nonce: object
    health: HealthOutcome = field(default_factory=HealthOutcome,compare=False,repr=False)

    def authorize(self):
        w = self.worker
        p = self.manifest
        a = w.registry.accounts
        a.observe()
        # The worker alone owns permits; never hand a pending route to the router.
        if ((self.nonce, self.mode) in w.spent or self.nonce not in w.permits or not a.current(p, self.candidate)
                or p.id in a.suspended or time.monotonic() >= self.deadline
                or not w.registry.billing.available(self.candidate.scope)
                or self.candidate.scope in w.registry.billing.holds):
            return False
        ticket = w.registry.resilience.acquire(p,self.candidate.model_id,private=True)
        if ticket is None:
            return False
        if not w.budget.reserve(p.id, self.partition):
            w.registry.resilience.rollback(ticket)
            return False
        w.health_tickets[(self.nonce,self.mode)] = ticket
        w.spent.add((self.nonce, self.mode))
        return True


class ProbeWorker:
    def __init__(self, registry, client=None):
        from backend.app.core.adapters.openai_client import OpenAIProviderClient
        self.registry = registry
        self.client = client or OpenAIProviderClient()
        # Recreating an orchestrator/worker must not replenish runtime quotas.
        if not hasattr(registry.accounts, "probe_budget"):
            registry.accounts.probe_budget = ProbeBudget()
        self.budget = registry.accounts.probe_budget
        self.permits = set()
        self.health_tickets = {}
        self.spent = set()
        self.cursor = {}
        self.provider_cursor = 0
        self.partition_cursor = {}
        self.history = deque(maxlen=192)

    def select(self, manifest):
        a = self.registry.accounts
        now = time.monotonic()
        if (a.assertion_reason(manifest) or manifest.id in a.suspended
                or now < a.paused_until.get(manifest.id, 0)):
            return None
        if (not self.registry.billing.available(self.registry.eligibility.scope(manifest))
                or not self.registry.resilience.peek(manifest,private=True)):
            return None
        cs = sorted((c for (p, _), c in a.candidates.items() if p == manifest.id), key=lambda c: c.model_id)
        due = [c for c in cs if a.current(manifest, c) and now >= c.retry_at
               and (not a.healthy(c, now) or now >= c.passed_at + RENEW_SECONDS)]
        groups = {"renewal": [], "new": []}
        for c in due:
            groups["renewal" if c.active and a.healthy(c, now) else "new"].append(c)
        preferred = self.partition_cursor.get(manifest.id, "renewal")
        for partition in (preferred, "new" if preferred == "renewal" else "renewal"):
            rows = groups[partition]
            if not rows or not self.budget.can_reserve(manifest.id, partition):
                continue
            key = manifest.id, partition
            index = self.cursor.get(key, 0) % len(rows)
            self.cursor[key] = index + 1
            self.partition_cursor[manifest.id] = "new" if partition == "renewal" else "renewal"
            return rows[index]
        return None

    async def qualify(self, manifest, candidate):
        a = self.registry.accounts
        task = asyncio.current_task()
        if (manifest.id in a.inflight and a.inflight[manifest.id] is not task) or len(a.inflight) > 2:
            return False
        if manifest.id not in a.inflight and len(a.inflight) >= 2:
            return False
        a.inflight[manifest.id] = task
        partition = 'renewal' if candidate.active and a.healthy(candidate, time.monotonic()) else 'new'
        nonce = object()
        self.permits.add(nonce)
        passed = deferred = False
        try:
            async with asyncio.timeout(30):
                deadline = time.monotonic() + 30
                for streaming in (False, True):
                    permit = ProbePermit(self, manifest, candidate, partition, streaming, deadline, nonce)
                    payload = prepare_dispatch(self.registry.dispatch_profile(manifest),
                        {'model': candidate.model_id, 'messages': [{'role': 'user', 'content': '1+1=?'}],
                         'max_tokens': 32, 'stream': streaming})
                    outcome = None
                    try:
                        outcome = await self.client.qualify(permit, payload)
                    finally:
                        ticket = self.health_tickets.pop((nonce,streaming),None)
                        health = permit.health
                        if outcome is not None and outcome.passed:
                            health.kind = "success"
                        self.registry.resilience.finish(ticket,health,financial=candidate.scope in self.registry.billing.holds)
                    self.history.append({'provider': manifest.id, 'stream': streaming,
                        'status': outcome.status, 'passed': outcome.passed,
                        'completion_tokens': outcome.completion_tokens, 'cost_status': outcome.cost_status,
                        'code': outcome.code, 'diagnostics': outcome.diagnostics,
                        'failure_kind': permit.health.kind, 'actual_http_status': permit.health.actual_http_status})
                    if not streaming and outcome.code == "permit_unavailable":
                        # Queue pressure is not a failed health observation.
                        deferred = True
                        candidate.retry_at = time.monotonic() + 60
                        return False
                    if not outcome.passed or not a.current(manifest, candidate) or not self.registry.billing.available(candidate.scope):
                        a.fail_pair(manifest, candidate, outcome.status, outcome.retry_after, outcome.diagnostics)
                        return False
                passed = a.pass_pair(manifest, candidate)
                return passed
        except asyncio.CancelledError:
            a.fail_pair(manifest, candidate)
            raise
        except Exception:
            a.fail_pair(manifest, candidate)
            return False
        finally:
            self.permits.discard(nonce)
            self.spent.difference_update({(nonce, False), (nonce, True)})
            if a.inflight.get(manifest.id) is task:
                a.inflight.pop(manifest.id, None)
            if not passed and not deferred:
                # A partial pair is never reusable admission evidence.
                candidate.active = False
                candidate.passed_at = None

    async def run(self, stop):
        a = self.registry.accounts
        tasks = set()
        try:
            while not stop.is_set():
                a.observe()
                manifests = sorted(self.registry.get_manifests(), key=lambda p: p.id)
                if manifests:
                    start = self.provider_cursor % len(manifests)
                    for offset, p in enumerate(manifests[start:] + manifests[:start]):
                        if len(a.inflight) >= 2:
                            break
                        if p.id in a.inflight:
                            continue
                        c = self.select(p)
                        if c is not None:
                            task = asyncio.create_task(self.qualify(p, c))
                            a.inflight[p.id] = task
                            tasks.add(task)
                            task.add_done_callback(tasks.discard)
                            # Advance on real scheduling, not one-second idle
                            # polls:60s quotas and10 manifests otherwise phase-
                            # lock the first two accounts and starve the third.
                            self.provider_cursor = (start + offset + 1) % len(manifests)
                try:
                    await asyncio.wait_for(stop.wait(), 1)
                except TimeoutError:
                    pass
        finally:
            for task in tuple(tasks):
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
