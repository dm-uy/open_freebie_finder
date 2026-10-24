# SPEC-T-009 v1.0.0 — Adaptive Circuit Breaker and Credential Lockout

- **Profile:** BROWNFIELD: change existing routing/admission and failure handling; a new internal module does not create a separate product/interface.
- **Version / status:** 1.0.0 / owner-approved for R1–R3 and the specified isolated live packet on2026-10-23; implementation owner-accepted; subsequent explicitly authorized primary integration verified on2026-10-23.
- **Route / value:** P2 / B-002 / [T-009](../TASKS.md); predictable recovery and uninterrupted free-only inference in [VISION](../VISION.md).
- **Input:** [dated Input RECON](../docs/recon/T-009-adaptive-resilience.md), accepted [primary checkpoint](../notes/T-007-primary-activation.md), existing T-007 contracts.
- **Baseline:** main HEAD `6d49e2a174a111dc0a5bb8745530a97d0e9786da` plus accepted uncommitted work; fresh 412 tests passed in 12.47s. Recon records working-tree identity and measured gaps. This is not a clean release revision.
- **Authority:** Owner explicitly approved v1.0.0, R1–R3 and its limited live checks in chat on2026-10-23. The choices below are approved within that scope; result acceptance and primary restart/activation remain separate decisions. No commit/push or external deployment is implied.
- **Process:** [PROJECT-PROCESS.md](../PROJECT-PROCESS.md), ordered R1–R3 with regression gates; no full framework onboarding.

Primary disposition: the owner subsequently accepted T-009 and separately authorized restart/target checks; primary integration is now verified in the dated section of [results](../notes/T-009-results.md). Earlier approval boundaries remain historical, not an outstanding gate.

$START_DOCUMENT
PURPOSE: Specify bounded adaptive resilience without weakening eligibility, financial safety or response delivery.
SCOPE: Existing normal inference and narrowly defined private qualification admission; in-memory single-process state.
KEYWORDS: T-009, P2, circuit-breaker, quota, auth, free-only, SSE
$START_DOCUMENT_PLAN
$DOCUMENT_PLAN
GOAL: Existing eligible routes recover predictably without bypassing stronger guards => GOAL_ADAPTIVE_RESILIENCE
$END_DOCUMENT_PLAN
$START_SECTION_FEATURE
$START_ARTIFACT_GOAL_ADAPTIVE_RESILIENCE
TYPE: GOAL
KEYWORDS: routing, adaptive-backoff, credential-lockout
$START_CONTRACT
PURPOSE: Protect the accepted active pool from repeated transient failures and unsafe recovery.
DESCRIPTION: Add typed upstream outcomes, shared bounded state and atomic generation-bound recovery admission while retaining existing source/account/billing contracts.
RATIONALE: The current fixed cooldown loses retry hints and cannot safely coordinate parallel recovery or distinguish cancellation from upstream failure.
ACCEPTANCE_CRITERIA: AC-1..AC-16 and the traceability matrix below; independent result review and honest transport/live evidence.
$END_CONTRACT
$START_BODY

## 1. Preserved contract and explicit exceptions

**BR-1 — Brownfield compatibility.** Preserve canonical/raw identity resolution, same-canonical preference and provider ordering, maximum failover attempts, memory-only model listing, master authentication before lookup, request validation, public response/telemetry schemas, masking and T-006 validation isolation. Preserve adapter exception constructor call compatibility and router cooldown helper signatures. Retain a deepcopy-safe read-only `_cooldowns` compatibility snapshot for the protected T-006 nonmutation test; other fixtures may migrate away from private dictionary mutation. It must not claim recovery or clear controller state.

The only intended consumer/configuration exceptions are: adaptive rather than fixed transient pauses; credential-wide nonfinancial 429 pause and inference-401 lockout; one admitted recovery rather than unrestricted expiry; known currently eligible but health-blocked requests return 503 rather than 404; cooldown setting gains bounded strict validation. Other status/delivery behavior remains unchanged. No new public endpoint, UI, persistent store, dependency or runtime service is introduced.

**BR-2 — Free-only invariants.** Existing T-007 [base](T-007-multi-provider-discovery-and-cascade.md), [dynamic correction](T-007-dynamic-free-eligibility.md), [OpenRouter amendment](T-007-openrouter-price-evidence-amendment.md) and [hybrid correction](T-007-hybrid-account-eligibility.md) retain their precedence. Strict OpenRouter pricing/output checks and owned zero-price routing constraints remain mandatory. Account mode still requires current explicit assertion, fresh dynamic catalog, exact dispatch binding and unexpired both-mode lease. Health success is neither price evidence nor qualification publication. Unavailable monetary cost remains unavailable; no manual model-ID admission lists.

BillingGuard always wins: a latch/hold is never cleared or shortened by health success, expiry, quota recovery, source refresh or assertion changes. No added balance probe or automatic reassertion/rebinding. Existing worker financial suppression and private negative caches remain effective. Complete valid answers survive observed billing incidents, which block future dispatch; before output, existing failover is permitted; after semantic SSE output, never replay to another provider. Keep one redacted error and no DONE on interrupted incomplete SSE; completed streams preserve their existing terminal handling.

Cloudflare/Cerebras/GitHub remain unconditional skips. HF primary unconfirmed, Gemini/gateway/provenance deferrals and other T-007 obligations remain unchanged. T-009 cannot close full T-007 or P2 by itself.

## 2. Decisions submitted with this version

| ID | Bounded proposal | Reason / consequence |
|---|---|---|
| D1 | Route-scoped service/network backoff; credential-scope 429 pause | Avoid hammering sibling routes after quota failure; credential scope is conservative proxy policy, not provider-certified quota scope. |
| D2 | Inference 401 requires deliberate restart or a genuinely different resolved credential; no timed auth recovery | Align consumer dispatch with existing private suspension. New epoch alone never restores a revoked account assertion. |
| D3 | Base 60s, exponential cap 900s; safe Retry-After horizon 86400s | Predictable bounded local backoff; longer upstream hints cannot be silently shortened. |
| D4 | No new diagnostics API; internal aggregate snapshot and sanitized transition events | Bound scope and avoid a new privileged surface. |
| D5 | Strict integer cooldown base 1..300; current default remains 60 | Reject accidental zero/negative/unbounded recovery loops, with sanitized startup errors. |
| D6 | R1–R3 plus isolated strict-OpenRouter happy-path smoke | Fault cases use real local sockets; never exhaust real balances or manufacture upstream auth/quota failures. |

These are not previously owner-settled decisions. Approval of this exact version accepts these choices and the implementation/smoke bounds; primary integration remains separate. If a choice changes, revise the specification before implementing the changed contract.

## 3. State, scope and lifecycle

**BR-3 — Shared bounded state.** One registry-owned controller is reused by routers and the existing private worker. Route key: existing captured credential/endpoint/profile epoch scope plus raw model identity. Quota gates use that same captured scope without model identity. Auth lockout is additionally keyed by the private resolved credential identity for the stable provider, independent of source URL/profile/epoch: those fields can change without changing the key. Keep the blocked identity across such changes and key restoration until deliberate process restart; a genuinely different credential has independent state. Never use an incremented eligibility epoch alone as proof of a new key. Compare identities only in private memory, without serializing recoverable fingerprints. No raw scope, credential, fingerprint or endpoint enters diagnostics or persistence. State is memory-only and process-local; multiple workers/restart do not share state or preserve latches. Existing financial restart semantics are unchanged, not newly guaranteed durable.

Route state: CLOSED, OPEN(until), HALF_OPEN(one ticket), or DEFERRED(manual/reset condition). Quota has the same lifecycle; auth is an independent latched gate. Store saturating failure streak, generation and at most one recovery owner per gate. Normal CLOSED dispatch may be concurrent. Service/quota transitions are fenced independently by each gate's generation: a matching failure opens/increments that gate once; stale outcomes cannot escalate, close or resurrect its newer state. A route-generation change does not invalidate an independently current quota ticket. CLOSED successful completions do not reset another concurrent ticket's newer failure. Auth401 is fenced by current credential identity and actual inference/auth binding, never by route/quota generation: a concurrent current-binding401 must latch even after another request opened a newer service/quota generation. A changed source/profile alone cannot make that still-current identity/binding result harmless. BillingGuard retains its own stronger scope-fenced handling.

At most 4096 route entries and 256 combined quota/auth entries, including retained blocked identities. Remove obsolete service/quota scopes/routes when no owned I/O remains; invalidate their tickets immediately. Retained auth identities are exempt from that pruning. Evict only idle CLOSED entries with no outstanding tickets. Never evict a live OPEN/HALF_OPEN/DEFERRED/auth entry to reset protection. Capacity exhaustion rejects new admission without an upstream attempt, with a finite diagnostic reason. Cleanup, release and outcome publication are idempotent.

Credential/endpoint/profile changes invalidate old service/quota tickets and state before new dispatch; late old-scope429/success cannot affect the new scope. A late401 from a different credential or obsolete inference/auth binding cannot latch a new identity; existing auth lockouts for the same credential survive catalog/profile/endpoint changes. Preserve existing assertion revocation even if the key is restored. Router recreation in the same registry must not reset protection. Deliberate process restart is the only explicit operator reset surface in this slice; selecting a genuinely different credential uses its separate state without clearing the old identity's latch; no hot reset endpoint is added.

## 4. Typed failures and timing

**BR-4 — Origin classification.** Extend adapter/probe internal outcomes with finite failure kinds and normalized retry metadata. Keep constructor positional compatibility. Classify where the error originates; never parse exception strings, arbitrary JSON fields or model names. Preserve existing documented billing classification first. Capture actual HTTP status separately from synthetic status. New health metadata contains no raw body/header, key, prompt or reply; existing transient parsing inputs may be consumed by unchanged billing/probe policy but must not be copied into health state, events or snapshots.

| Outcome, after financial classification | Scope and effect |
|---|---|
| Existing financial hold/latch or cancellation caused by it | Existing BillingGuard only; health-neutral, cannot close another gate |
| Actual inference HTTP/in-band effective 401 | Auth latch for still-current captured credential identity/binding; no automatic retry; private 401 suspension/lease invalidation still applies |
| Nonfinancial HTTP/in-band effective 429 | Credential quota OPEN with adaptive delay; no sibling-route hop in that credential while held |
| Actual upstream 5xx, tagged transport failure or upstream timeout | Adaptive route OPEN |
| Other nonfinancial HTTP 4xx, invalid upstream 200 completion/framing | Route quarantine for one base interval; no exponential increment or auth latch |
| Local pre-send configuration/validation failure, caller cancellation, client disconnect without upstream fault | Health-neutral; release ownership; retain existing consumer error/telemetry behavior |
| Valid upstream completion, no financial incident on that attempt | Matching-generation success may close owned route/quota gates |

Discovery/catalog GET 401/403 is not an inference auth latch; existing source invalidation still applies. Standalone 403 does not establish revoked credentials. Private fixed 1-hour route negatives and probe scheduling pauses remain stronger where already defined. Synthetic protocol 502 must not be mistaken for actual HTTP 502.

**BR-5 — Backoff and Retry-After.** Existing setting `CIRCUIT_BREAKER_COOLDOWN_SECONDS` becomes strict integer 1..300, default60. Accept decimal environment strings through the existing typed settings source; reject boolean, fraction, out-of-range or malformed input without echo. Local adaptive delay is `min(900, base * 2**(streak-1))`, streak saturates at16; default sequence60,120,240,480,900. Fixed quarantine does not increment/reset this streak. Matching valid recovery success resets it. No jitter in this first slice; no request sleeps or adapter-level retry loop.

Parse Retry-After separately from BillingGuard's existing helper, which remains unchanged. For a single ASCII value up to256 bytes, support nonnegative decimal seconds or a valid HTTP date per [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3); capture wall time once, convert to monotonic not-before. Missing, duplicate or malformed values use local delay. Zero/past dates never shorten local delay. For a valid delay at most86400s, use the later of server not-before and local delay. Valid larger delays, or oversized hints, produce DEFERRED with finite reason `retry_after_exceeds_horizon`, requiring deliberate restart/new scope; never silently clamp and retry early. Do not retain/log the raw header. Honor supported hints for 429/5xx and fixed 4xx quarantine; protocol faults without a trustworthy HTTP hint use local policy. HTTP date and delay arithmetic must be overflow-safe.

[RFC 6585](https://www.rfc-editor.org/rfc/rfc6585.html#section-4) leaves 429 counting/identity scope unspecified. The credential-wide policy above is deliberately conservative and may pause unrelated sibling models; do not describe it as upstream account knowledge.

## 5. Atomic dispatch and recovery

**BR-6 — Admission ownership.** Listing, preflight and queue construction use pure peeks: no reservations, expiry deletion or HTTP. Before every actual send, recheck current source/credential/profile/lease or private permit, request compatibility, financial admission, auth and health. Acquire route/quota recovery ownership atomically all-or-none; rollback every partial acquisition if another gate refuses. No await between final health check/reservation and handing the request to owned adapter I/O. Preserve existing scope/financial race cancellation. Skips consume no attempt, private inference budget or telemetry upstream attempt.

Expired OPEN is eligible for one HALF_OPEN ticket, not automatically CLOSED. Other concurrent consumers skip it and may use a different eligible provider within the existing attempt budget. Do not wait in the request for recovery. Tickets capture scope/generation; stale/duplicate service/quota outcomes are inert, while current-binding401 still latches as defined in BR-3. A HALF_OPEN owner releases only after its I/O is complete/closed, including cancellation cleanup; no lease expiry may admit a second recovery while old I/O is live.

If one send owns both route and quota recovery, valid success closes both matching generations. A new 429 advances quota backoff and releases route recovery back to OPEN for its previous local delay; service/network failure advances route backoff and reopens owned quota for its previous delay. Fixed quarantine reopens the route for base delay and any owned quota for its previous delay. Neutral/inconclusive termination reopens each owned recovery gate for its previous delay without increment/reset. Auth/financial gates supersede these outcomes; no successful closure after a same-attempt financial incident. Reopening uses completion/cleanup time and retains any later supported not-before.

**BR-7 — Private worker interoperability.** Do not add probes, a scheduler or new inference authority. Existing permitted qualification HTTP sends also check the shared auth/quota gates; ordinary route service/quarantine state applies only to consumer traffic, since private qualification already owns its route-negative policy. A permitted existing private send can own the single expired quota recovery ticket, avoiding deadlock if all consumer leases expire during a pause. It consumes unchanged worker budgets and still requires valid assertion/source/scope and no financial hold, including the existing private ban on financial recovery. Both modes remain necessary for availability publication; one successful quota recovery is not a lease.

Private actual 401/429 updates shared auth/quota state; private nonquota failures keep existing probe policy and, when owning quota recovery, reopen that quota neutrally as specified above. No private outcome resets a consumer route breaker. Release every ticket/permit on cancellation or between-mode rejection; stale results cannot publish or release a different owner. Preserve max32-token fixed prompts, two concurrent pairs globally/one credential, send/day/partition budgets, source/lease TTLs and queue fairness.

## 6. Delivery and API behavior

**BR-8 — Delivery-independent health.** Buffer: valid completion is health success only after cost inspection; complete answer plus a financial incident still delivers successfully, with its separate existing incident record and no health success. SSE: distinguish a semantic terminal indication (for example finish_reason) from final health publication. Remember terminal generation early, but publish the single health success/close recovery only after the existing bounded upstream consumption, all observed final usage/cost inspection and owned upstream cleanup have finished. A later usage.cost incident therefore prevents health success even after finish_reason. Do not add an unbounded drain. If client cancellation stops consumption before this health boundary, the health result is neutral, even after finish_reason; it does not imply a service fault or certify unseen cost. After that boundary, downstream disconnect cannot convert upstream success into failure. Keep recovery ownership until I/O closure; delivery telemetry remains independent. Real upstream faults before/after semantic output update future health protection exactly once. Existing before-output failover and after-output no-replay rules remain; delivery success/correlation/attempt schema stays unchanged. Billing interruption is never a synthetic service failure.

**BR-9 — Client classification.** Preserve unknown/no-current-eligibility 404. If a requested model has current eligible candidates before health filtering but all compatible candidates are blocked by health/auth/capacity, return sanitized503 with correlation and a terminal trace with zero upstream attempts. Exhausting candidates after actual attempts keeps existing503 behavior and trace. Unsupported request400 and master auth precedence remain. A failed financial gate keeps its existing semantics; this slice does not redefine it as a health error. `/v1/models` remains memory-only eligibility listing and may include temporarily unhealthy candidates; it never claims a recovery ticket or promises immediate availability.

**BR-10 — Safe observability.** Provide an internal pure aggregate snapshot (counts by gate/state/finite reason) for tests/operator code, with no new HTTP endpoint or public telemetry fields. Emit bounded structured transition events once per actual transition, using finite reason/state/scope-kind and safe provider label only if existing secret sanitization permits it; otherwise redact. No per-poll noise, raw scope/model/endpoint/header, key substring, prompt, output or monetary amount. Existing correlation identifiers retain their existing contract. A new CLI process must not claim to inspect another process's state.

## 7. Scope of implementation

MAY EDIT, only for this contract:

- `backend/app/core/balancer/router.py`; new `backend/app/core/balancer/resilience.py`.
- `backend/app/core/adapters/openai_client.py` (typed outcomes and owned dispatch/cleanup integration).
- `backend/app/core/providers/registry.py` (shared state lifetime/scope hooks).
- `backend/app/core/eligibility/account.py`, `backend/app/core/eligibility/probes.py` (narrow shared admission/outcome hooks; existing safety/budgets preserved).
- `backend/app/api/v1/chat.py` (pure preflight and explicit404/503 distinction).
- `backend/app/config.py`, `.env.example` (only base validation/documentation; default unchanged).
- `backend/tests/` (relevant meaningful regression/race/socket tests and fixture migration).
- `TASKS.md`, `ROADMAP.md`, `HANDOFF.md`, `ARCHITECTURE.md`, this spec/recon, `notes/T-009-results.md`; new `docs/decisions/DEC-005-adaptive-resilience.md` recording approved choices, not inventing approval.

DO NOT TOUCH: real `.env`/credentials, providers/aliases YAML, billing.py, eligibility evidence/request/protocol policy, discovery parsers, provider schema, primary process, main.py, frontend/dependencies/storage, T-006 admin aggregator/router/validation modules/tests/script, unrelated code/specs or roadmap dependencies. Existing probe limits cannot be altered indirectly. If integration requires another path or a conflicting safety-policy change, stop that dependent work and request a concrete amendment; finish unaffected approved work.

## 8. Ordered execution and delivery evidence

**R1 — Typed outcomes and shared lifecycle.** Implement origin metadata, Retry-After normalization, strict base validation and bounded controller with fake clocks; registry ownership and stale-scope handling. Gate: focused transition/settings/security tests plus full backend regression; no dispatch integration claimed yet.

**R2 — Ordinary routing and output ownership.** Integrate atomic consumer admission, buffered/SSE health timing, HTTP classification, safe events and preflight. Gate: deterministic concurrency/cancellation tests plus real TCP loopback buffered and SSE delivery/failover; full regression before R3.

**R3 — Private hooks and completed candidate.** Integrate existing private permits, quota recovery and auth suspension without changing budgets; prove mixed worker/consumer races, fairness and protected contracts; full regression and independent cumulative result review. Repair defects within scope before reporting completion.

Mandatory local delivery proof uses real loopback sockets/ephemeral ports, actual app/router/adapter and counted upstream requests: 429→other credential, 503/transport fault→alternative route, long Retry-After, 401 sibling lockout, one HALF_OPEN owner, stale success, cancellation, pre-output SSE switch, after-output no replay, financial guard dominance, complete costly answer delivered. Synthetic fixtures supply billing incidents; never induce real provider charges, exhaust quota/balance, submit invalid real keys or weaken TLS/free gates for testing.

Future isolated live smoke, only after exact specification implementation approval: reuse existing probe tooling with strict OpenRouter, one buffered and one SSE consumer request, each cap32 and at most2 attempts; **at most4 actual inference sends total**, no automatic retries beyond that packet. Use dynamic eligible selection, owned zero-price constraints and existing source checks; no account qualification worker/extra provider inference in this isolated packet. Retain modes/status/correlation/attempt count/visible-output/one-DONE evidence without response/key bodies. Missing keys, source or usable route is UNVERIFIED, never mock-pass. An inconclusive packet does not authorize exceeding4 sends. Do not alter the running primary or its configuration. Primary integration is a later owner decision and requires target-environment checks after restart under that grant.

## 9. Acceptance and traceability

| AC | Requirement and decisive evidence | BR |
|---|---|---|
| AC-1 | Fresh full suite passes; canonical routing/order/attempts, exception/helper call compatibility and T-006 unchanged | 1,2 |
| AC-2 | Fake-clock exact base/exponential/cap/reset/quarantine sequences; invalid settings sanitized, default60 intact | 3,4,5 |
| AC-3 | Integer/date/zero/past/invalid/duplicate/oversized/overflow Retry-After; 3600s honored, >86400 deferred; billing helper unchanged | 4,5 |
| AC-4 | Actual HTTP502 vs protocol502/transport/local failures classified distinctly; no message parsing; 402/403 billing precedence | 2,4 |
| AC-5 | Concurrent CLOSED failures increment once; late success/failure cannot change newer generation; duplicate completion inert | 3,6 |
| AC-6 | At expiry one HALF_OPEN send across competing routers; pure peeks claim nothing; cancelled owner closes I/O before release | 3,6 |
| AC-7 | Scope mutation/removal, key restore, router recreation, capacity exhaustion and stale-identity401 tested; current-binding401 after concurrent503 still latches; same-key catalog/profile changes and key restoration do not clear auth; no lost protections or restored assertions | 2,3,6 |
| AC-8 | Nonfinancial429 blocks sibling routes; different credential can serve; matching recovery success resets only eligible owned state | 4,6,7 |
| AC-9 | Consumer/private401 share auth lockout; source GET401/403 and inference403 do not; no timed auth recovery | 2,4,7 |
| AC-10 | Worker/consumer quota recovery race admits one send; budgets, negative caches, both-mode lease/fairness and financial private ban retained | 2,6,7 |
| AC-11 | No stale source/assertion/lease/permit or billing-blocked dispatch; counter/barrier tests prove zero sends and zero charged skipped attempts | 2,6,7 |
| AC-12 | Buffered and SSE terminal/cost/cancel races include finish_reason→late positive/invalid usage.cost, finish_reason→client cancel, and competing recovery before I/O close; complete billing-incident answer delivered, no latch reset/replay | 2,8 |
| AC-13 | Actual TCP delivery proof from R2/R3 with request counts and expected responses; ASGI/mocks alone insufficient | 1,6,8 |
| AC-14 | Known health-blocked503 zero-attempt trace vs unknown404; request400/auth precedence; listing pure and memory-only | 1,9 |
| AC-15 | Sentinel keys embedded in errors/identities/headers never escape events/snapshot/traces; bounded state/events; no new public schema | 3,4,10 |
| AC-16 | Independent cumulative review resolved; isolated live packet honestly PASS/UNVERIFIED/FAIL within4-send cap; primary unchanged and records synchronized | 1,2,10 |

Live PASS requires valid visible output in both modes and one SSE DONE under enforced caps, not merely HTTP200 or eligibility listing. Missing external prerequisites may leave AC-16 live delivery UNVERIFIED while implementation/local verification is reviewable; do not mark all AC/T-009 delivered until the owner accepts that explicit gap or positive proof exists. Local injected incidents prove local protection, not observed real-provider 401/429 behavior.

## 10. Approval and completion record

Owner approved v1.0.0 and R1–R3 including its bounded isolated smoke on2026-10-23. R1–R3 implementation and the bounded isolated smoke are complete: [results and AC matrix](../notes/T-009-results.md),493 full tests, independent81 focused tests after repairs, buffered/SSE live PASS within2 sends. Primary integration is not authorized by that approval. Independent read-only specification review completed on2026-10-23 after repair: no substantive findings remain. Repairs explicitly separated gate generations from auth identity, delayed SSE health publication through final cost inspection/cleanup, and prevented catalog/profile epoch changes from clearing same-key auth lockout. The verifier confirmed412 passed/12.47s baseline, all58 runtime hashes unchanged,64 local links, balanced markers and clean whitespace. It performed no writes, tests, network, inference or secret-file reads. This is preparation review, not implementation QA. Results belong in `notes/T-009-results.md` during implementation, preserving baseline, failures, limits, hashes and exact gates. T-007/P2 remain open.

$END_BODY
$START_LINKS
IMPLEMENTS: ../VISION.md; ../ROADMAP.md (P2); ../docs/decisions/DEC-002-declarative-provider-schema.md; ../docs/decisions/DEC-003-canonical-model-mapping-and-harness-interop.md
IMPACTS: ../TASKS.md; ../HANDOFF.md; ../ARCHITECTURE.md
REQUIRES: ../docs/recon/T-009-adaptive-resilience.md; T-007-hybrid-account-eligibility.md; T-007-openrouter-price-evidence-amendment.md
$END_LINKS
$END_ARTIFACT_GOAL_ADAPTIVE_RESILIENCE
$END_SECTION_FEATURE
$END_DOCUMENT
