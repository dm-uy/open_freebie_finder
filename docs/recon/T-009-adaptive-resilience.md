# T-009 Input RECON — Adaptive Resilience

Date: 2026-10-23. Status: measured preparation, not implementation authorization. Route: P2 / B-002 / [T-009](../../TASKS.md). Owner selected T-009 and authorized recon/specification while preserving all free-only constraints. Process: [PROJECT-PROCESS.md](../../PROJECT-PROCESS.md).

## Identity and verification

Branch main, HEAD `6d49e2a174a111dc0a5bb8745530a97d0e9786da`, plus the existing accepted, uncommitted T-006/T-007 work. HEAD alone does not identify the working implementation. Starting status: `/tmp/t009-recon-start-status.txt`; SHA-256 manifest `/tmp/t009-recon-runtime-baseline.json` covers 58 runtime/configuration/test files (backend/scripts Python and provider/alias YAML). Supplementary temporary captures are not durable release artifacts.

Fresh regression: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest backend/tests -q -p no:cacheprovider` → **412 passed in 12.47s**; capture `/tmp/t009-recon-baseline-tests.txt`. Temporary TCP loopback tests are included; no manual external provider inference was performed. Real `.env` was not read or edited; primary backend was not restarted. Its previously authorized bounded background worker remains outside this preparation operation.

The accepted operational delivery baseline remains [primary activation evidence](../../notes/T-007-primary-activation.md). T-007 and P2 remain open; the existing provider/provenance deferrals and unconditional skips are unchanged. Preparation does not require pretending those obligations are complete.

## Actual producers, consumers and gaps

| Source | Observation | Consequence for the proposed slice |
|---|---|---|
| [router](../../backend/app/core/balancer/router.py) | Fixed default 60-second per-provider/raw-model cooldown, stored on the router; expired entries disappear. Nonbilling failures generally trigger cooldown. | No adaptive counter, half-open ownership or stable shared controller exists. Preserve routing order and attempt limits while changing recovery. |
| Same router | Candidate queue filters cooldown during resolution; eligibility is rechecked at dispatch, but no atomic health reservation is acquired immediately before I/O. | A previously built queue can bypass a concurrent failure; parallel recovery needs atomic admission and generation-bound results. |
| Same router / buffered stream | SSE finalizer receives delivery success as a boolean, not a typed upstream outcome. | Client cancellation or billing interruption can be treated like generic failure. Health and delivery telemetry need separate internal outcomes. |
| [adapter](../../backend/app/core/adapters/openai_client.py) | `_error` receives Retry-After for billing classification but ordinary exceptions discard it. Synthetic protocol/network errors can share status 502 with actual HTTP 502. | Add finite safe metadata at the origin; do not classify by exception text or status alone. Preserve existing constructor calls. |
| [chat API](../../backend/app/api/v1/chat.py) | Empty candidate resolution returns 404, including routes removed solely by cooldown. | Distinguish unknown/ineligible models from known eligible routes temporarily blocked by resilience. Preflight must not reserve recovery. |
| [BillingGuard](../../backend/app/core/eligibility/billing.py) | Independent credential-scope holds, positive/invalid-cost latches, owned I/O interruption and bounded financial recovery. Its Retry-After helper clamps to 1..300 seconds. | Preserve this stronger subsystem. A new resilience parser must not change billing semantics or shorten a valid long nonfinancial delay. |
| [evidence](../../backend/app/core/eligibility/evidence.py) | Current scope binds credential epoch, endpoint and profile; changes revoke evidence/assertions. | Bind health tickets to captured scope, reject stale completion; never expose scope or key material. |
| [account eligibility](../../backend/app/core/eligibility/account.py) | Private 401 suspends credential and invalidates leases; route negatives and quota pauses already exist. | Ordinary inference needs consistent auth lockout; preserve private suspension, negative caches and no automatic reassertion. |
| [probe worker](../../backend/app/core/eligibility/probes.py) | Private permits enforce freshness, assertions, financial guards, budgets and both-mode qualification. | Health recovery cannot create eligibility or extra probes. Integrate admission without increasing budgets or creating a second scheduler. |
| [registry](../../backend/app/core/providers/registry.py) | Owns shared eligibility/account/billing state; routers can be recreated. | Shared resilience lifetime belongs here, not in one request/router instance. |
| [settings](../../backend/app/config.py), [.env.example](../../.env.example) | Existing cooldown setting defaults to 60, with no bounded strict validation. | Proposed validation is an explicit compatibility exception, not an as-built restriction. |
| [cascade tests](../../backend/tests/test_cascade_failover.py) / [socket tests](../../backend/tests/test_multi_provider_live.py) | Tests use cooldown helpers; socket fixtures also clear a private cooldown dictionary. | Keep helper signatures, migrate private fixture coupling; retain actual TCP delivery checks. |

The registry source path is verified; no new storage, frontend or onboarding implementation is inferred from target architecture. [DEC-003](../decisions/DEC-003-canonical-model-mapping-and-harness-interop.md) describes intended auth behavior, but does not prove an adaptive implementation or dashboard exists.

## External protocol evidence

[HTTP Semantics §10.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3) defines Retry-After as an HTTP date or nonnegative integer delay. [RFC 6585 §4](https://www.rfc-editor.org/rfc/rfc6585.html#section-4) permits it on 429 but does not define the identity/counting scope. Therefore a credential-wide 429 pause is a proposed conservative application policy, not a claim about provider billing or rate-limit identity. No provider plan, tariff or account entitlement is newly inferred.

## Bounded proposal and unresolved authorization

Prepare [T-009 v1.0.0](../../specs/T-009-adaptive-circuit-breaker.md): typed outcomes, registry-owned adaptive route state, credential-wide quota pause and inference-401 lockout, single recovery admission, current-scope publication, safe diagnostics, deterministic tests and actual loopback proof. Automatic auth recovery, financial recovery changes, new admin endpoints and provider expansion are excluded.

Numerical backoff/limits, quota scope, nontransient quarantine, strict configuration validation and the future isolated smoke packet are proposals requiring exact specification approval. Existing free-account assertions are not upgraded to provider-certified zero cost. No successful health recovery may clear BillingGuard, renew a lease, restore an assertion or authorize a stale/source-ineligible route.

## Independent preparation check

An independent read-only pass checked router/adapter/account/billing/probe/API interactions and recommended generation-bound admission, separate delivery/health outcomes and no new admin endpoint. Final independent specification review found no substantive residual defects after the auth-generation, auth-identity and late-SSE-cost clarifications. It independently confirmed the412/12.47s baseline,58 unchanged runtime hashes,64 local links, balanced markers and clean whitespace; no writes/tests/network/inference or secret-file reads. This is preparation review, not implementation QA.
