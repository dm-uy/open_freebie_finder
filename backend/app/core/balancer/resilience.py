"""Process-local, generation-fenced admission. No sleeps, inference or public secrets."""
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import logging
import re
import time

logger = logging.getLogger(__name__)


@dataclass(frozen=True, repr=False)
class RetryHint:
    delay: float = 0
    deferred: bool = False


def retry_hint(values, wall=None):
    """Normalize a single HTTP hint without retaining header bytes or overflowing."""
    if values is None:
        return RetryHint()
    if isinstance(values, str):
        values = [values]
    if len(values) != 1:
        return RetryHint()
    raw = values[0]
    if not isinstance(raw, str):
        return RetryHint()
    if len(raw) > 256:
        return RetryHint(deferred=True)
    if not raw.isascii():
        return RetryHint()
    raw = raw.strip()
    try:
        if raw.isdigit():
            value = int(raw)
        else:
            if not re.fullmatch(r"(?:[A-Z][a-z]{2}, [0-9]{2} [A-Z][a-z]{2} [0-9]{4} [0-9:]{8} GMT|[A-Z][a-z]+, [0-9]{2}-[A-Z][a-z]{2}-[0-9]{2} [0-9:]{8} GMT|[A-Z][a-z]{2} [A-Z][a-z]{2} [ 0-9][0-9] [0-9:]{8} [0-9]{4})", raw):
                return RetryHint()
            date = parsedate_to_datetime(raw)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            value = max(0, date.timestamp() - (time.time() if wall is None else wall))
        return RetryHint(deferred=True) if value > 86400 else RetryHint(float(value))
    except (ValueError, TypeError, OverflowError, IndexError):
        return RetryHint()


@dataclass(repr=False)
class HealthOutcome:
    kind: str = 'neutral'
    status: int | None = None
    retry: RetryHint = field(default_factory=RetryHint)
    actual_http_status: int | None = None

    def error(self, exc):
        self.kind = getattr(exc, 'failure_kind', 'http')
        self.status = getattr(exc, 'status_code', None)
        self.retry = getattr(exc, 'retry_hint', RetryHint())
        self.actual_http_status = getattr(exc,'actual_http_status',None)
        if getattr(exc, 'billing_reason', None):
            self.kind = 'neutral'


@dataclass(eq=False, repr=False)
class Gate:
    kind: str = 'route'
    state: str = 'CLOSED'
    until: float = 0
    delay: float = 60
    streak: int = 0
    generation: int = 0
    inflight: int = 0
    reason: str = 'available'


@dataclass(eq=False, repr=False)
class Ticket:
    scope: tuple
    identity: tuple
    binding: tuple
    route: Gate | None
    quota: Gate
    generations: tuple
    owners: tuple
    released: bool = False


class ResilienceController:
    """Synchronous event-loop atomic reservations shared by all registry consumers."""
    def __init__(self, registry, clock=None, route_limit=4096, credential_limit=256):
        self.registry = registry
        self.clock = clock or time.monotonic
        self.base = registry.settings.circuit_breaker_cooldown_seconds
        self.route_limit = route_limit
        self.credential_limit = credential_limit
        self.routes = {}
        self.quotas = {}
        self.auth = {}
        self.scopes = {}
        self.capacity_rejections = 0

    def _context(self, manifest):
        scope = self.registry.eligibility.scope(manifest)
        identity = (manifest.id, self.registry.credential(manifest))
        binding = (manifest.base_url.rstrip('/'), manifest.auth.type,
                   manifest.auth.custom_header_name, manifest.auth.api_key_env)
        self.scopes[manifest.id] = scope
        # Do not evict retained auth identities, including after key restoration.
        ids = {p.id for p in self.registry.get_manifests()}
        for provider in set(self.scopes) - ids:
            self.scopes.pop(provider,None)
        for rows in (self.routes, self.quotas):
            for key, gate in list(rows.items()):
                old_scope = key[0] if rows is self.routes else key
                if old_scope[0] not in ids or (old_scope[0] == manifest.id and old_scope != scope):
                    if not gate.inflight:
                        del rows[key]
        return scope, identity, binding

    def _current(self, ticket, auth=False):
        manifest = self.registry.get_manifest(ticket.scope[0])
        if manifest is None:
            return False
        scope, identity, binding = self._context(manifest)
        return identity == ticket.identity and binding == ticket.binding and (auth or scope == ticket.scope)

    def _available(self, gate):
        return gate is None or gate.state == 'CLOSED' or (gate.state == 'OPEN' and self.clock() >= gate.until)

    def peek(self, manifest, model_id=None, private=False):
        scope, identity, _ = self._context(manifest)
        return (not self.auth.get(identity, False)
                and self._available(self.quotas.get(scope))
                and (private or self._available(self.routes.get((scope, model_id)))))

    @staticmethod
    def _evict(rows):
        for key, gate in list(rows.items()):
            if not gate.inflight and gate.state == 'CLOSED':
                del rows[key]
                return True
        return False

    def acquire(self, manifest, model_id, private=False):
        scope, identity, binding = self._context(manifest)
        if not self.peek(manifest, model_id, private):
            return None
        new_identity = identity not in self.auth
        needed = int(scope not in self.quotas) + int(new_identity)
        while len(self.quotas) + len(self.auth) + needed > self.credential_limit:
            if not self._evict(self.quotas):
                # Unlatched identities carry no protection and have no I/O owner.
                idle = next((key for key, latched in self.auth.items() if not latched
                    and not any(g.inflight for s, g in self.quotas.items() if s[0] == key[0])), None)
                if idle is None:
                    self.capacity_rejections += 1
                    return None
                del self.auth[idle]
            new_identity = identity not in self.auth
            needed = int(scope not in self.quotas) + int(new_identity)
        route_key = (scope, model_id)
        if not private and route_key not in self.routes:
            while len(self.routes) >= self.route_limit:
                if not self._evict(self.routes):
                    self.capacity_rejections += 1
                    return None
        self.auth.setdefault(identity, False)
        quota = self.quotas.setdefault(scope, Gate(kind="quota",delay=self.base))
        route = None if private else self.routes.setdefault(route_key, Gate(delay=self.base))
        gates = (route, quota)
        owners = tuple(g is not None and g.state == 'OPEN' for g in gates)
        for gate, owner in zip(gates, owners):
            if gate is not None:
                gate.inflight += 1
                if owner:
                    self._transition(gate, 'HALF_OPEN', 'recovery')
        return Ticket(scope, identity, binding, route, quota,
                      tuple(g.generation if g else None for g in gates), owners)

    def _transition(self, gate, state, reason):
        gate.state, gate.reason = state, reason
        logger.info('resilience_transition scope_kind=%s state=%s reason=%s', gate.kind, state, reason)

    def _open(self, gate, adaptive=False, hint=None, delay=None):
        hint = hint or RetryHint()
        if adaptive:
            gate.streak = min(16, gate.streak + 1)
            delay = min(900, self.base * 2 ** (gate.streak - 1))
        gate.delay = gate.delay if delay is None else delay
        gate.until = max(gate.until, self.clock() + max(gate.delay, hint.delay))
        gate.generation += 1
        self._transition(gate, 'DEFERRED' if hint.deferred else 'OPEN',
                         'retry_after_exceeds_horizon' if hint.deferred else 'backoff')

    def finish(self, ticket, outcome=None, financial=False):
        if ticket is None or ticket.released:
            return
        ticket.released = True
        outcome = outcome or HealthOutcome()
        # Auth is fenced independently from route/quota generations and catalog epochs.
        if not financial and outcome.kind == 'http' and outcome.status == 401 and self._current(ticket, auth=True):
            if not self.auth.get(ticket.identity):
                self.auth[ticket.identity] = True
                logger.info('resilience_transition scope_kind=auth state=AUTH_LOCKED reason=credential_rejected')
        current = self._current(ticket)
        for index, gate in enumerate((ticket.route, ticket.quota)):
            if gate is None:
                continue
            gate.inflight -= 1
            if not current or gate.generation != ticket.generations[index]:
                continue
            owner = ticket.owners[index]
            kind, status = ('neutral', None) if financial else (outcome.kind, outcome.status)
            quota_failure = kind == 'http' and status == 429
            service_failure = kind in {'transport', 'timeout'} or (kind == 'http' and status is not None and status >= 500)
            quarantine = kind == 'protocol' or (kind == 'http' and status is not None and 400 <= status < 500 and status not in {401, 429})
            if index == 1 and quota_failure or index == 0 and service_failure:
                self._open(gate, adaptive=True, hint=outcome.retry)
            elif index == 0 and quarantine:
                self._open(gate, hint=outcome.retry, delay=self.base)
            elif owner:
                if kind == 'success' and not self.auth.get(ticket.identity):
                    gate.streak = 0
                    gate.until = 0
                    gate.generation += 1
                    self._transition(gate, 'CLOSED', 'recovered')
                else:
                    self._open(gate)

    def rollback(self, ticket):
        """Release an unsent reservation without extending a pause or charging a failure."""
        if ticket is None or ticket.released:
            return
        ticket.released=True
        for index,gate in enumerate((ticket.route,ticket.quota)):
            if gate is None:
                continue
            gate.inflight-=1
            if ticket.owners[index] and gate.generation==ticket.generations[index]:
                self._transition(gate,'OPEN','admission_rollback')

    def manual_cooldown(self, manifest, model_id, duration):
        ticket = self.acquire(manifest, model_id)
        if ticket is not None:
            self._open(ticket.route, delay=duration)
            self.finish(ticket)

    def cooldown_snapshot(self):
        return {(scope[0], model): gate.until for (scope, model), gate in self.routes.items()
                if gate.state != 'CLOSED'}

    def snapshot(self):
        counts = Counter('route_' + g.state for g in self.routes.values())
        counts.update('quota_' + g.state for g in self.quotas.values())
        counts.update('route_reason_' + g.reason for g in self.routes.values())
        counts.update('quota_reason_' + g.reason for g in self.quotas.values())
        counts['auth_locked'] = sum(self.auth.values())
        counts['auth_reason_credential_rejected'] = sum(self.auth.values())
        counts['capacity_rejections'] = self.capacity_rejections
        return dict(counts)
