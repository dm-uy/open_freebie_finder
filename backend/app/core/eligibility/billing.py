"""Shared credential-scope incidents, bounded balance recovery and owned I/O interruption."""
import asyncio
import anyio
import httpx
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import logging
import time

from backend.app.core.eligibility.evidence import decimal

logger = logging.getLogger(__name__)


class BillingInterrupted(Exception):
    def __init__(self, code="billing_unavailable"):
        self.code=code
        super().__init__("Upstream billing guard stopped this response.")


@dataclass(eq=False, repr=False)
class RequestHandle:
    scope: tuple
    complete: bool = False
    interrupted: asyncio.Event = field(default_factory=asyncio.Event)
    reason: str = "billing_unavailable"
    recovery_hold: object = None

    async def wait_io(self, awaitable):
        operation=asyncio.ensure_future(awaitable)
        signal=asyncio.create_task(self.interrupted.wait())
        delivered=False
        try:
            done, _ = await asyncio.wait((operation,signal),return_when=asyncio.FIRST_COMPLETED)
            # Preserve a result obtained concurrently with the scope hold.
            if operation in done or self.complete:
                value=await operation
                delivered=True
                return value
            raise BillingInterrupted(self.reason)
        finally:
            for task in (operation,signal):
                if not task.done():task.cancel()
            try:
                with anyio.CancelScope(shield=True):
                    await asyncio.gather(operation,signal,return_exceptions=True)
            except BaseException:
                delivered=False
                raise
            finally:
                # send() may finish while interruption/cancellation wins, even
                # if the transport suppresses cancellation. Own that response
                # until it has actually been handed to the adapter.
                if not delivered and operation.done() and not operation.cancelled():
                    try:result=operation.result()
                    except BaseException:result=None
                    if isinstance(result,httpx.Response):
                        with anyio.CancelScope(shield=True):await result.aclose()


@dataclass
class Hold:
    reason: str
    expires_at: float | None
    observed_utc: str
    recovery_active: bool = False


def retry_seconds(raw):
    try:
        if raw is None: return 60.0
        if raw.strip().isascii() and raw.strip().isdigit():
            return float(max(1,min(300,int(raw.strip()))))
        value=parsedate_to_datetime(raw)
        if value.tzinfo is None:value=value.replace(tzinfo=timezone.utc)
        return max(1.0,min(300.0,(value-datetime.now(timezone.utc)).total_seconds()))
    except (ValueError,TypeError,OverflowError,AttributeError):return 60.0


def classify_billing(provider_id, status, data):
    error=data.get("error",{}) if isinstance(data,dict) else {}
    metadata=error.get("metadata",{}) if isinstance(error,dict) else {}
    source=metadata.get("limit_source") if isinstance(metadata,dict) else None
    if provider_id=="openrouter":
        if status==402:
            if source=="openrouter_in_flight_budget":return "billing_temporarily_unavailable"
            if isinstance(metadata,dict) and "limit_source" not in metadata:return "insufficient_balance_or_budget"
            return "billing_access_unverified"
        if status==403 and isinstance(source,str) and source in {"openrouter_guardrail_budget","openrouter_workspace_budget","openrouter_key_limit"}:
            return "insufficient_balance_or_budget"
    if status==402:
        return "insufficient_balance_or_budget" if provider_id=="mistral" else "billing_access_unverified"
    return None


class BillingGuard:
    def __init__(self, registry=None):
        self.registry = registry
        self.holds: dict[tuple,Hold]={}
        self.active: set[RequestHandle]=set()
        self.hold_observers = []
        # OpenRouter task and chat scopes share the same real financial account.
        # Private identities stay inside this retained registry; never serialize.
        self._scope_identities = {}
        self._umbrellas = {}

    def _identity(self, scope):
        if scope in self._scope_identities:
            return self._scope_identities[scope]
        if self.registry is None or not scope or scope[0] != "openrouter":
            return None
        store = self.registry.eligibility
        binding = store._bindings.get(scope[0])
        if binding and len(scope) > 2 and store._epochs.get(scope[0]) == scope[2]:
            return (scope[0], binding[0])
        return None

    def _hold(self, scope):
        own = self.holds.get(scope)
        shared = self._umbrellas.get(self._identity(scope))
        if shared is None:
            return own
        if own is None or shared.expires_at is None:
            return shared
        if own.expires_at is None:
            return own
        return max((own, shared), key=lambda item: item.expires_at)

    def available(self,scope):
        identity = self._identity(scope)
        if identity is not None and identity not in self._umbrellas and len(self._umbrellas) >= 256:
            return False
        hold=self._hold(scope)
        return not hold or (hold.expires_at is not None and time.monotonic() >= hold.expires_at and not hold.recovery_active)

    def begin(self,scope):
        if not self.available(scope):return None
        hold=self._hold(scope)
        if hold:hold.recovery_active=True
        identity = self._identity(scope)
        if identity is not None:
            self._scope_identities[scope] = identity
        handle=RequestHandle(scope, recovery_hold=hold)
        self.active.add(handle)
        return handle

    def finish(self,handle,success=False):
        self.active.discard(handle)
        hold=self._hold(handle.scope)
        if hold and hold is handle.recovery_hold and hold.expires_at is not None and hold.recovery_active:
            if success:
                self.holds = {scope: item for scope, item in self.holds.items() if item is not hold}
                self._umbrellas = {key: item for key, item in self._umbrellas.items() if item is not hold}
            else:
                hold.recovery_active=False
                hold.expires_at=time.monotonic()+60

    def hold(self,scope,reason,*,retry_after=None):
        previous=self._hold(scope)
        if previous and previous.expires_at is None:return
        latched=reason in {"unexpected_paid_cost","unverifiable_cost"}
        self.holds[scope]=Hold(reason,None if latched else time.monotonic()+retry_seconds(retry_after),datetime.now(timezone.utc).isoformat())
        identity = self._identity(scope)
        if identity is not None:
            self._umbrellas[identity] = self.holds[scope]
        for observer in self.hold_observers:
            observer(scope, self.holds[scope])
        # No secret-bearing tuple, identifier, upstream content or amounts logged.
        logger.warning(json.dumps({"event":"billing_guard_incident","reason":reason,"latched":latched}))
        for handle in tuple(self.active):
            if (handle.scope==scope or (identity is not None and self._identity(handle.scope)==identity)) and not handle.complete:
                handle.reason=reason if latched else "billing_unavailable"
                handle.interrupted.set()

    def inspect_cost(self,handle,profile,data):
        if profile != "openrouter_zero_price":return "unavailable"
        usage=data.get("usage") if isinstance(data,dict) else None
        if not isinstance(usage,dict) or usage.get("cost") is None:return "unavailable"
        try:
            amount=decimal(usage["cost"])
        except ValueError:
            self.hold(handle.scope,"unverifiable_cost")
            return "invalid"
        if amount>0:
            self.hold(handle.scope,"unexpected_paid_cost")
            return "positive"
        return "zero"

    def diagnostics(self,scope):
        hold=self._hold(scope)
        if not hold:return {"kind":None}
        return {"kind":hold.reason,"latched":hold.expires_at is None,"observed_at":hold.observed_utc,
            "retry_in_seconds":None if hold.expires_at is None else max(0,round(hold.expires_at-time.monotonic(),3))}

    def prune(self, scopes):
        retained=set(scopes)|{h.scope for h in self.active}
        self.holds={k:v for k,v in self.holds.items() if k in retained}
        self._scope_identities = {key: value for key, value in self._scope_identities.items() if key in retained}
