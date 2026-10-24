# SPEC-T-007 v1.2.1 Amendment — OpenRouter Enforced Zero-Price Admission

> **Approved v1.3.0:** [Hybrid account correction](T-007-hybrid-account-eligibility.md) was explicitly owner-approved with H1–H4 and its bounded isolated live packet on 2026-10-23. Its section 1 supersedes the named account-mode rules, including NVIDIA strict-only handling for opted-in accounts. Unaffected contracts remain in force; primary activation and result acceptance remain separate.

- Profile: BROWNFIELD; narrow change to the implemented v1.2.0 OpenRouter evidence predicate.
- Status: approved; local implementation and corrected buffered/SSE external delivery verified; owner accepted the correction and authorized primary local activation on 2026-10-23. Owner explicitly approved T-007 v1.2.1 and authorized lightweight implementation including its specified live checks in chat on 2026-10-22. Version: 1.2.1.
- Phase P2 / B-002 / [T-007](../TASKS.md); value: key-only dynamic zero-cost inference in [VISION](../VISION.md).
- Input: [implementation/source recon](../docs/recon/T-007-dynamic-free-eligibility.md), [approved v1.2.0](T-007-dynamic-free-eligibility.md), [candidate results](../notes/T-007-results.md).
- Authorization: owner explicitly requested preparation of an evidence-based OpenRouter source/admission amendment in the structured chat reply on 2026-10-22. Subsequent exact owner approval authorizes this amendment and its bounded live checks, after adequate current amended evidence. Result acceptance, commit/push and deployment remain separate.
- Baseline: main HEAD 6d49e2a174a111dc0a5bb8745530a97d0e9786da plus the uncommitted v1.2.0 candidate identified by hashes in the results note. Final v1.2.0 regression: 285 passed in 9.71s; that is not a test result for this proposal.

$START_DOCUMENT
PURPOSE: Restore useful OpenRouter discovery under a bounded, explicit provider-enforced zero-price guarantee when its live catalog omits request pricing.
SCOPE: Only OpenRouter evidence semantics for absent pricing.request; preserve strict source binding, request validation, routing caps, billing guards and every other provider gate.
KEYWORDS: OpenRouter, request pricing, enforced ceiling, evidence, T-007
$START_DOCUMENT_PLAN
$DOCUMENT_PLAN
GOAL Admit source-verified zero-token OpenRouter models with mandatory zero-price enforcement => GOAL_OPENROUTER_ENFORCED_ADMISSION
$END_DOCUMENT_PLAN
$START_SECTION_FEATURE
$START_ARTIFACT_GOAL_OPENROUTER_ENFORCED_ADMISSION
TYPE: GOAL
KEYWORDS: pricing omission, dynamic models, no manual lists
$START_CONTRACT
PURPOSE: Avoid permanently excluding genuine zero-token offers solely because the live source omits a field that the provider can bound on dispatch.
DESCRIPTION: Catalog refresh identifies explicit zero-token offers → a distinct evidence basis records the missing request price and enforced ceiling → each dispatch retains zero request/token/image limits; unavailable free routes fail over safely.
RATIONALE: A missing price is not an observed zero. Provider-side rejection of prices above the configured ceiling is a separate source of assurance and must be named as such.
ACCEPTANCE_CRITERIA: AC-O1 through AC-O8 below.
$END_CONTRACT
$START_BODY

## 1. Observed problem and source basis

The v1.2.0 catalog/evidence probe succeeded but admitted zero OpenRouter models: all 468 observed entries were unknown/price_scope_unknown. Public read-only follow-up at 2026-10-22T21:22:32Z found pricing.request absent in all 468 entries; 20 had explicit zero prompt/completion prices and only those two pricing keys. A dynamically selected zero-token model's endpoint-detail response also omitted request pricing (one endpoint, prompt/completion/discount keys). The sample does not establish that every endpoint omits it. No credentials or generation requests were used for this follow-up. Sanitized stdout and reproducible command are in RECON.

The official [Models guide](https://openrouter.ai/docs/guides/overview/models) describes price units and an example request field; it does not establish that omission means zero. The official [provider routing guide](https://openrouter.ai/docs/guides/routing/provider-selection#max-price) documents price filtering, including a per-request ceiling, and distinguishes max_price rejection from soft performance preferences. This proposal relies on that documented enforcement contract, not on a claim that omitted fees are free. Actual enforcement remains a platform guarantee with the reactive guard as defense against a reported violation; the local proxy cannot prove the platform never misbills.

## 2. Options and proposed decision

| Option | Consequence | Disposition |
|---|---|---|
| Keep v1.2.0 strict required-field rule | All currently measured OpenRouter entries remain unknown; no free generations from this snapshot | Historical v1.2.0 behavior, retained as the measured baseline |
| Replace missing request with numeric zero | Conflates absent metadata with measured price; hides the original evidence gap | Rejected proposal |
| Explicit zero-token catalog prices plus mandatory provider-enforced zero request ceiling | Names the missing source field, binds a distinct evidence basis to the already enforced request policy and permits dynamic offers without manual IDs | Selected and owner-approved on 2026-10-22 |

The owner selected this bounded enforcement guarantee in the explicit v1.2.1 approval. No further Groq/NVIDIA guarantee change is proposed. No external account tier, credits or console/session interface is added.

## 3. Normative change to v1.2.0

Only the required presence of pricing.request in section 6 changes for the exact bound OpenRouter profile. All other v1.2.0 rules and ACs remain in force, including unknown-field rejection, credential/source epochs, TTL/failure revocation, request-profile coverage, guarded output semantics and the scope of B1–B4.

- Require explicit valid zero prompt and completion prices and positive text capability, as before. Missing, malformed, negative or nonfinite token prices remain unknown; positive token prices remain paid. No suffix, model ID or free-plan attestation confers admission.
- If request is present, parse it strictly: zero qualifies under the existing complete-catalog-price basis, positive is paid, and null/bool/invalid is unknown. Only an absent request key may use the new enforced basis. Do not reinterpret a present null/invalid value as absent.
- For an absent request key, use basis catalog_zero_tokens_with_request_ceiling and fixed reason free_enforced, with covered_profile=text_chat_v1 and source_id=openrouter_zero_price. Keep the observed pricing dict unchanged; never synthesize pricing.request=0, a zero invoice or a catalog_effective_price claim for the missing fee.
- That basis is eligible only while its exact approved source/inference/auth binding remains valid and the owned dispatch policy is openrouter_zero_price. Recheck policy capability with evidence immediately before dispatch and on listings; loss of policy support revokes this basis. No client or manifest flag may claim arbitrary endpoint enforcement.
- Every dispatch and provider fallback continues to inject prompt=0, completion=0, request=0, image=0 under provider.max_price and require_parameters=true. A missing request price is not permission to omit any cap, use BYOK, route through a partner, retry without constraints or pass provider options from the client.
- Preserve the existing conservative handling of other price components: applicable recognized positive fees are paid, malformed or unknown components are unknown. Conditional pricing.overrides remains unsupported/unknown in this amendment; do not implement an override interpreter. Do not expand media, caching controls, built-ins, request parameters or inference endpoints.
- A provider rejection because no route satisfies zero ceilings uses ordinary bounded safe failure/cascade. It cannot trigger an uncapped retry. The billing guard still latches actual positive operator charges or invalid recognized cost metadata; unavailable monetary reporting is not an invoice of zero.

The evidence store remains in memory. No new setting/flag, dependency or persistence is required. Existing refresh/TTL, size/concurrency/deadline and privacy bounds remain unchanged. Strict unknown remains the default for unsupported providers, including Groq/NVIDIA and unverified local/cloud provenance.

## 4. Business requirements

- **BR-O1 — Preserve the approved correction.** Source: owner-approved v1.2.0. Change only the OpenRouter absent-request predicate/basis and its diagnostics; preserve validation, expiry, billing and output contracts.
- **BR-O2 — Name the assurance accurately.** Sources: observed live omission and official routing contract. Distinguish explicit zero catalog price, absent request price, enforced maximum and actual reported operator charge. No synthetic zero certificate.
- **BR-O3 — Enforcement is mandatory.** Sources: VISION zero-cost value and v1.2.0 BR-D5. Current exact profile binding and owned zero ceilings are admission conditions, not optional optimizations.
- **BR-O4 — Dynamic and honest delivery.** Sources: owner's no-manual-list requirement and live-evidence rules. Real source observations must yield appropriate current classification without hardcoded IDs; fixtures cannot establish external enforcement.

## 5. Boundaries and verification

MAY EDIT: backend/app/core/eligibility/evidence.py and request.py (predicate/basis/policy coupling only), backend/app/core/providers/registry.py (current enforced-policy admission check), backend/tests/test_dynamic_eligibility.py, test_free_request_profile.py and test_multi_provider_live.py (targeted/regression/socket cases), scripts/probe_multi_provider.py (safe basis/reason diagnostics if needed), this proposal, the existing dynamic eligibility recon and results note, ARCHITECTURE.md, TASKS.md, ROADMAP.md and HANDOFF.md. Update only the v1.2.0 metadata cross-reference when this amendment is approved; preserve its original approved predicate as history.

DO NOT TOUCH: .env/credentials, accepted T-006/admin contracts, billing guard/output semantics, telemetry schema/store, provider keys/accounts/plans, Groq/NVIDIA admission, other profiles/manifests, model-ID lists/aliases, frontend, dependencies, external deployment. No commit/push/deployment or deliberately paid inference test. No implementation before exact amendment approval.

| AC | BR | Required check / expected evidence |
|---|---|---|
| AC-O1 | BR-O1 | Full backend suite on exact candidate; all accepted validation and unaffected v1.2.0 scenarios retained. Current 285-test observation is a baseline, not a quota. |
| AC-O2 | BR-O2 | Explicit request zero retains existing basis; absent request uses enforced basis with unchanged raw metadata; present null/bool/malformed/negative/nonfinite remains unknown; positive remains paid. |
| AC-O3 | BR-O2, BR-O3 | Missing/invalid/positive token prices, unknown/positive other fees and overrides cannot use the missing-request exception. Nontext and inadequate tool capability stay excluded. |
| AC-O4 | BR-O3 | Loss/change of source/auth/endpoint/owned dispatch policy invalidates enforced admission before listing or HTTP. Same-shaped custom provider data never selects this guarantee. |
| AC-O5 | BR-O1, BR-O3 | Real-socket buffered/SSE and failover capture preserves all zero ceilings; client provider override rejected before I/O. A no-route response cannot lead to uncapped retry. |
| AC-O6 | BR-O4 | Real current OpenRouter catalog/evidence probe reports dynamically classified observed non-seed offers with explicit basis/reason and source age. Catalog may change; report actual counts. No mock-pass or manual model selector certifies eligibility. |
| AC-O7 | BR-O4 | After approval and actual adequate amended evidence, at most one buffered and one SSE free micro-generation through an isolated real local proxy, maximum 32 output tokens each, with enforced caps and safe telemetry/billing status. Missing credentials, no eligible offer, zero-route rejection or reported charge is UNVERIFIED/failure with exact safe reason; never fake delivery. No paid-model enforcement stress test. |
| AC-O8 | BR-O1..4 | Independent cumulative result review, protected validation hashes, source interpretation, safe captures and final record links; result acceptance distinct from implementation approval. |

Current execution evidence: [results](../notes/T-007-results.md). On 2026-10-23 the owner explicitly authorized root-cause repair and necessary repeated 32-token checks. The original contains-text predicate had admitted music text+audio endpoints despite uncovered song charges; current execution conservatively requires output_modalities exactly ["text"], superseding that capability subset without expanding parameters, profiles or tariff coverage. Mixed outputs are unknown / unsupported_output_modality. This is an authorized safety repair, not a model blacklist. Nested provider INVALID_ARGUMENT caused the observed OpenRouter 400 / isolated proxy 503; its exact rejected argument was not disclosed. Corrected source admits 18/468 offers. Final 334 tests pass; AC-O7 buffered/SSE proof now passes with visible output, reported cost zero, max_tokens=32 and all string-zero caps verified. Earlier failed/protocol-only/music captures remain historical and do not certify delivery. AC-O8 independent final verification is clear; the correction was owner-accepted on 2026-10-23 and primary backend buffered/SSE checks now pass at 127.0.0.1:8001 with32-token caps and reported zero cost. Full T-007/P2 remains open.

## 6. Delivery, risks and finish

Existing source-only command: .venv/bin/python scripts/probe_multi_provider.py --provider-id openrouter --mode evidence. Historically it returned UNVERIFIED under strict v1.2.0; current corrected evidence and delivery results are recorded above. Existing proxy command uses --mode proxy; the implementation must bound its max_tokens to 32 for this amendment before any new generation run. Verify --help with an actual run. Save sanitized stdout, exits, timestamps, exact source interpretation and candidate hashes in notes/T-007-results.md; no keys, generated text or account IDs. Required suite: .venv/bin/pytest backend/tests -q plus git diff --check, with permission for local socket tests.

Done when AC-O1..8 have honest evidence and independent review, with unresolved external delivery explicitly identified. Stop dependent admission work for an undocumented enforcement assumption, contradictory current official contract, required paid usage, extra account credentials or price components outside this contract. Continue independent approved work. Result acceptance, commit/push and deployment are separate.

Known risks: reliance on provider enforcement, bounded catalog observation delay, absent final monetary reporting, no guarantee of refund or zero loss for in-flight work if the provider violates its own constraints. A rejected free-route request may reduce availability. Other direct-provider source gaps and full T-007/P2 obligations remain open.

$END_BODY
$START_LINKS
IMPLEMENTS: [VISION](../VISION.md), zero-cost value and Success Criterion 2.
IMPACTS: [v1.2.0](T-007-dynamic-free-eligibility.md), section 6 absent-request predicate only; [T-007](../TASKS.md).
REQUIRES: [RECON](../docs/recon/T-007-dynamic-free-eligibility.md); [candidate results](../notes/T-007-results.md).
$END_LINKS
$END_ARTIFACT_GOAL_OPENROUTER_ENFORCED_ADMISSION
$END_SECTION_FEATURE
$END_DOCUMENT
