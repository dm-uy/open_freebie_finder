# SPEC-T-010 v1.0.0 — Task-Specific Free Catalogs and Inference APIs

- **Profile:** MIXED — new task subsystem and interfaces inside the existing backend; preserved chat contracts are explicit.
- **Version / status:** 1.0.0 / owner-approved for N1–N4 and the bounded isolated verification packet on2026-10-23. Independent specification reviews are clear. Result acceptance and primary activation remain separate.
- **Route:** P2 / B-002 / T-010, nearest before T-008.
- **Implementation checkpoint:** N1–N4 source candidate locally verified and partially accepted by the owner on2026-10-23; [results and AC matrix](../notes/T-010-results.md). AC-18 remains OPEN/UNVERIFIED for all tasks; primary activation is pending.
- **Pending amendment:** [T-010 v1.1.0](T-010-free-variant-admission.md) proposes free-variant admission/speech corrections. Its implementation approval is pending; v1.0.0 remains effective until that approval. The amendment states exact precedence and retains all other base contracts.
- **Input RECON:** [T-010](../docs/recon/T-010-task-specific-inference.md).
- **Process:** [PROJECT-PROCESS.md](../PROJECT-PROCESS.md).

$START_DOCUMENT
PURPOSE: Extend free inference to four distinct tasks without contaminating chat catalogs or weakening cost controls.
SCOPE: OpenRouter-first task catalogs and bounded embeddings, rerank, decisions and text-to-speech interfaces.
KEYWORDS: T-010, P2, embeddings, rerank, decisions, speech, free-eligibility
$START_DOCUMENT_PLAN
$DOCUMENT_PLAN
GOAL: Dynamically eligible task-specific inference preserves task semantics and existing chat clients => GOAL_TASK_INFERENCE
$END_DOCUMENT_PLAN
$START_SECTION_FEATURE
$START_ARTIFACT_GOAL_TASK_INFERENCE
TYPE: GOAL
KEYWORDS: task-catalog, exact-model, dynamic-evidence, zero-cost
$START_CONTRACT
PURPOSE: Give applications task-specific inference through the proxy with explicit capability and free-access contracts.
DESCRIPTION: Separate task inventories, evidence, request validation and delivery while sharing credential financial/auth protection.
RATIONALE: The current registry and transport are chat-specific; listing nonchat models there would imply unsupported behavior.
ACCEPTANCE_CRITERIA: AC-1 through AC-18 and the traceability table.
$END_CONTRACT
$START_BODY

## 1. Outcome, authority and scope

**Approval record:** On2026-10-23 the owner explicitly approved T-010 v1.0.0 and N1–N4 with the stated admission limits and authorized implementation under the lightweight process. This approval settles D1–D7 and the proposed policy/boundaries below. Historical preparation/pending wording describes the pre-approval stage, not an outstanding implementation gate. No primary restart, commit/push or external deployment is included.

The owner requested this preparation on2026-10-23: synchronize project records, make the change nearest on the route, then prepare a standalone specification for embeddings, rerank, decisions and speech, keeping dynamic free determination and task-separated catalogs. This authorizes the present recon/specification only. Approval of this exact version would authorize N1–N4 and the bounded verification packet below; result acceptance, primary activation/restart, commits/push and external deployment remain separate.

Baseline: main `78a1aa4790293781aafe81e786ee4e3b7f098ef2` plus accepted uncommitted changes, fresh493 tests/16.62s. [Input RECON](../docs/recon/T-010-task-specific-inference.md) owns source observations, prior sandbox failure and observation limits. This is not a clean release baseline.

**Done when:** Four task-specific protocol paths and isolated catalogs meet AC-1..17, independent cumulative QA passes, and AC-18 reports actual external delivery per task honestly. Complete T-010 requires positive free live delivery for all four tasks; if source/enforcement evidence is insufficient, report a verified partial implementation with the affected live AC OPEN/UNVERIFIED. Neither an empty eligible list nor a local fixture closes positive delivery. A partial result can be separately accepted by the owner, with remaining task IDs/criteria retained.

**Stop and ask when:** A task needs weaker free assurance, another provider, unknown fee interpretation, model equivalence assertion, a new dependency/service/store, protected-file modification, higher live budget or primary changes. Finish independent safe stages first. Source disappearance deterministically excludes admission; it does not authorize broader probing or repeated research/inference. Do not reopen settled chat/free decisions.

Included: OpenRouter-first dynamic inventory, strict task eligibility, bounded text-only embeddings/rerank/decisions, preset-voice text-to-speech, memory-only public task lists and authenticated diagnostic catalog. Other providers retain their accepted chat scope. Excluded: STT/transcription, audio chat, image/video generation, token/multimodal inputs, voice cloning/reference uploads, realtime/streamed audio delivery, generic proxy URLs, semantic cache, vector database/index creation, automatic nonchat qualification, new task auto aliases, dashboard and onboarding. Return conditions are separate approved task/provider or protocol specifications.

## 2. Choices submitted for approval

The code/source researchers independently proposed additive catalogs, endpoint-specific evidence and exact-target routing. Root's assessment favors those options for compatibility and proof isolation. This table records proposals; owner approval of this exact version settles them.

| ID | Proposed choice | Alternative / consequence / reconsideration |
|---|---|---|
| D1 | OpenRouter as the only new-task upstream | Expanding all direct providers now adds unresearched tariff/account/probe contracts; return under separately approved profiles |
| D2 | Preserve default chat list; explicit `task` query and separate privileged inventory | One combined default pollutes Harness pickers; multiple independent model-list paths add API surface. Revisit for a concrete client |
| D3 | Add task catalog/evidence rather than generalizing destructive chat snapshots | Generalizing every existing model path risks accepted T-007/T-009 contracts. Shared credentials/guards remain mandatory |
| D4 | Exact target for all new tasks; no alternative model/provider fallback in v1 | Generic chat cascade can silently corrupt embedding indexes or change score/voice/decision semantics. Return only with explicit equivalence contract |
| D5 | Fully buffer all new-task responses, including bounded audio | Audio streaming needs a separate post-header failure contract; deferred. This slice never emits chat SSE from nonchat APIs |
| D6 | Strict unknown on unresolved task fee/enforcement coverage | Successful probes and free website labels are not pricing evidence. No conditional-account shortcut for OpenRouter |
| D7 | N1–N4 with full regression gates and honest partial external delivery | One large unreviewed change is harder to verify; no phase/task closure from local protocol support alone |

## 3. Preserved contracts

**BR-1 — Compatibility.** Preserve accepted chat request/response/status/auth behavior, canonical/raw resolution, `auto:free`, closed text profile, existing account assertions/leases/budgets, provider order and masking, telemetry schemas, no replay after started SSE, T-006 isolation and all T-009 recovery/generation rules. Preserve the493-test baseline by behavior rather than a permanent count. Do not modify approved historical specs to masquerade as new approval. Allowed exceptions: additive task APIs, explicit task query on models, additive internal task ownership/scope hooks, shared cross-task account guards, isolated task diagnostic events and task discovery scheduling. Existing no-query models JSON shape and unauthenticated access stay unchanged.

**BR-2 — Dynamic free assurance.** No model-ID lists, name/suffix-only classification, cached website parsing, successful-inference-as-price proof, or inherited chat/account certificates. Inventory, capability, current free evidence and operational health are distinct. `unknown`, expired and paid rows are never dispatched or listed as eligible. Missing/invalid/negative/nonfinite/boolean monetary values never become zero. Guard unavailable monetary reporting stays unavailable. Existing profile skips and deferred providers remain effective.

## 4. Task catalog and public interfaces

**BR-3 — Isolated identities and snapshots.** Use task enum `chat|embeddings|rerank|decisions|speech`. New task row identity is `(task, logical_provider_id, exact_raw_model_id)`, with task-specific source URL/query, captured credential epoch, exact dispatch URL, profile revision, source revision, observed/expiry time and capability metadata. No fake provider IDs to evade account protection. Keep task storage separate from `_models_cache`/chat evidence and never call provider-wide chat replacement with a task snapshot. Register/prune/refresh one task without deleting another; duplicate conflicting IDs in one task cannot certify first-wins data. Supported task labels/architecture must agree; a negative capability wins. Preserve exact raw IDs; no automatic cross-task canonical alias inference.

For new-task public IDs use the exact reversible string `openrouter::<raw_id>`. Raw IDs are1..512 UTF-8 characters, no control characters or embedded configured secret; provider/task comes from trusted registry identity. Parse the first `::` once, compare exact strings, never build a URL from a public ID. Nonchat responses use that requested public ID in their model field; preserve raw upstream identity privately for validation. A model is never presented as another semantic model. No new auto aliases, and chat aliases cannot be used at nonchat endpoints.

| Public surface | Contract |
|---|---|
| GET `/v1/models` or `?task=chat` | Existing chat-only shape/IDs/auto:free, memory-only; no new fields |
| GET `/v1/models?task=embeddings\|rerank\|decisions\|speech` | Same OpenAI list envelope, only current free/capable task IDs, sorted/deduplicated, no alias placeholder |
| GET `/api/admin/models/catalog?task=all\|chat\|embeddings\|rerank\|decisions\|speech` | Optional existing master-key auth before lookup; default all; safe diagnostic inventory including paid/unknown and blocked rows |
| POST `/v1/embeddings` | Text vectors profile below; upstream S2 |
| POST `/v1/rerank` | Text relevance profile below; upstream S3 |
| POST `/v1/decisions` | Local stable path; upstream alpha Decisions S4, not `/v1/systemone` |
| POST `/v1/audio/speech` | Bounded fully buffered preset-voice speech; upstream S5 |

**BR-4 — Catalog views.** Public model reads perform no network/probes, reservations or TTL renewal; task query rejects repeated/unknown parameters or `task=all` with redacted400. Normal no-query calls remain compatible. Catalog lists eligibility rather than a promise of current health; a temporary service pause need not hide otherwise eligible IDs. Privileged inventory envelope: `object=list`, `data` sorted by task/provider/id, and `tasks` aggregate status list. Row fields are exactly `id,task,provider_id,eligibility,basis,reason,assurance,observed_at,expires_in_seconds,health,capabilities`; eligibility enum free/paid/unknown, health available/blocked/unknown. Capabilities contain only normalized dimension/format/voice metadata needed by that task; raw descriptions, arbitrary metadata/prices, credentials, endpoints, scopes and upstream bodies are not exposed. Task status has `task,inventory_state,eligible_count,live_delivery`; live_delivery is not dynamically fabricated by listing. Historical production request success is not a persisted certification. Default live_delivery is unverified. Chat diagnostics are a nonmutating safe projection of existing state. Report counts from the same frozen memory view. Maximum5000 diagnostic rows (1000 per task) and no pagination claim beyond this bounded scope; overflow of a task source fails that task, not silent truncation. When no master key is configured, auth remains permissive under the existing local-operation policy; do not call this a public-safe deployment design.

**BR-5 — Discovery lifecycle.** Existing orchestrator remains the single lifespan owner. Add owned bounded task jobs; use S2 embedding catalog and three S1 API task filters, not four website URLs and not a competing all-model snapshot. Request exact owned HTTPS sources on openrouter.ai, no redirects, ambient proxy/auth/cookies or credentials in URLs. At most4 concurrent catalog HTTP operations total across old/new work,15s per source,4MiB decoded per document,1000 rows/task; detect unsupported/incomplete pagination and overflow as a source failure. Existing30s cycle deadline and chat/private-work fairness remain. Tasks refresh at existing evidence interval (default60s), TTL existing120s; catalog GET must refresh actual source, not merely timestamp old rows. Successful empty source atomically removes that task. Source failure/cancellation/incomplete data revokes affected task proof immediately; retain only sanitized unknown diagnostics until next success, bounded to that task's TTL. Another task/chat remains intact. Capture binding before I/O, recheck before publication; source/credential changes invalidate old evidence before dispatch. Cancelling lifespan closes every request/job. Reads never start the worker.

## 5. Exact free-evidence policy

**BR-6 — Owned profiles.** New task evidence must cover its closed request profile, current source, exact inference URL/auth, currency/units and every applicable fee. Reason codes include `unsupported_profile,unsupported_enforcement,price_scope_unknown,invalid_evidence,paid,expired,source_unavailable,free_verified`; no untrusted text. The safe initial source interpretation below is binding, not a choice left to the implementer.

| Task | Initial strict policy and evidence limit |
|---|---|
| embeddings | Require declared embeddings output and text input, complete pricing with explicit zero prompt/completion/request. Any additional pricing component is unknown until a task-specific interpretation is approved. No omitted-request exception from chat. Owned ProviderPreferences zero prompt/completion/request ceilings plus require_parameters=true; no client routing overrides |
| decisions | Same complete-zero requirement, exact decisions capability and text/state-only profile; owned zero ceilings/require_parameters as above. No transfer of the chat omitted-request exception |
| rerank | Inventory/protocol implemented, but initial strict verdict is unknown/unsupported_enforcement: verified relation between search-unit pricing and routing ceilings is missing. A generic provider schema is insufficient. No external inference under this version |
| speech | Inventory/protocol implemented, but initial strict verdict is unknown/unsupported_enforcement: no verified zero-ceiling contract or complete fee coverage. No external inference under this version |

Embedding/decisions initially recognize only `prompt,completion,request`; explicit nonzero values yield paid. Any additional key, including cache/reasoning prices borrowed from chat, yields unknown even if apparently zero until a separately approved task profile interprets it. Require all three mandatory keys; source input/output token units must match S2/S4 and owned policy. Structured policy support and complete source prices are both necessary; loss of either removes admission. At dispatch, use the same owned policy builder as admission, reject caller-supplied provider routing, and send canonical string zero values. Existing chat builder/exception remains unchanged. Source capability advertising alone is not a proof that a particular optional request parameter is supported; constrain dispatch to its verified task parameter subset.

This deliberately may produce no eligible nonchat models from current source data (observed request price omission). Do not patch in manual IDs or broaden account mode to obtain a green live check. Unlocking missing-request support, rerank or speech requires a sourced specification amendment with acceptance tests, then exact owner approval. This is an explicit evidence gate, not a feature flag that may be toggled around the policy. No implementation is allowed to claim that all four tasks already have free live supply.

## 6. Closed request and response profiles

**BR-7 — Validation before I/O.** For all four endpoints: master auth precedes body validation/model lookup; generate/return X-Request-ID using existing semantics. Read request incrementally with256KiB decoded limit; JSON object only, duplicate keys/NaN/Infinity rejected. Reject unknown top-level/nested fields with400 `unsupported_free_request`, no input echo; malformed JSON400, excessive body413. Required model is an exact public task ID1..1024 chars. Provider/options/tools/URL-valued control fields/plugins/traces/user forwarding and stream fields are outside these closed profiles; ordinary input text may contain inert URL strings. Treat all strings/state/question text as inert user data; never execute/fetch instructions, schema, URLs or returned content. Only trusted profile/schema code controls URLs, headers and guards. No LLM-based manifest/validation step. All numeric inputs strict (booleans are not integers), finite; schema/control text cannot override eligibility or routing. Order is authentication, bounded structural validation, exact task target lookup, current eligibility/guard checks, then optional route capability checks and final send admission. Thus a structurally valid known speech target with unsupported free enforcement returns503 rather than probing voices or dispatching; unsupported optional capability on an otherwise eligible route returns400.

| Task | Allowed request fields and bounds | Successful response validation |
|---|---|---|
| embeddings | model,input,dimensions,encoding_format. input nonempty string or1..32 nonempty strings;4096 chars/item,32768 combined. dimensions optional strict integer1..8192, only if current source documents support. encoding_format absent or float; emit float explicitly. Token inputs/base64/input_type deferred | OpenAI list envelope; exactly one item per input, unique indices covering0..n-1, embedding arrays finite floats of equal dimension1..8192; requested dimension must match. Reject wrong model/object/index/count/shape; no partial batches |
| rerank | model,query,documents,top_n. query nonempty<=4096 chars;1..32 nonempty string documents<=4096 each,32768 combined; top_n strict1..document count, default all | results count equals effective top_n, unique indices within original documents, finite relevance_score; preserve upstream ranking/scores and original index mapping. Reject invalid rows/duplicates; never infer score calibration or sort a repaired result |
| decisions | model,state,questions. state nonempty text<=8192 chars (JSON context/multimodal deferred).1..8 named questions; names1..64 chars. Each exactly type,instructions,criteria; instructions nonempty<=1024. type choice: criteria map2..16 unique labels1..64 to nonempty text<=512; score: ordered list2..16 nonempty descriptions<=512; noul: exactly false/true criteria descriptions. No box/other primitives | answers exactly requested question IDs/types. noul finite0..1; choice one submitted label and full matching probability map; score finite0..k-1, exact indexed legend and probability map. Probabilities finite0..1 with sum within1e-3 of1. Optional confidence finite0..1. Reject unknown answer fields except schema-declared type-specific fields; no prose repair. Verify model identity before public masking |
| speech | model,input,voice,response_format,speed. input nonempty<=512 chars; voice1..128 chars and present in current authoritative supported_voices; response_format required mp3 or pcm supported by that route, no default guessing; speed absent or exactly1. No instructions/references/options/cloning/multispeaker | Full nonempty audio bytes, bound below. MIME audio/mpeg for mp3 with valid ID3 or MPEG frame prefix; audio/pcm for pcm,16-bit little-endian even byte count. No JSON/HTML error passed as audio. Minimal framing validation does not certify pronunciation, complete decodability or semantic quality |

Task metadata must explicitly support optional dimensions, speech format and voice to allow them; absent support yields400 before I/O. The current general Model schema does not establish dimension/format capability metadata; do not manufacture those fields. Until an approved authoritative metadata mapping is available, omit optional dimensions and keep affected speech requests unavailable; supported_voices alone does not prove output format support. The base task profiles cannot widen merely because an upstream adds a field. Only typed nonnegative integer usage counters are copied: embeddings prompt_tokens/total_tokens; rerank search_units/total_tokens; decisions input_tokens/output_tokens when present. Omit undocumented fields and monetary values; do not reflect usage wholesale. Missing counters are omitted, never synthesized as measured usage. Response object fields are model/id/object/data/usage for embeddings as applicable; rerank id/model/results/usage; decisions id/model/answers/usage. Other routing/private provider fields are removed. Sanitize/redact identifiers and errors against configured secrets before output; a matching secret in a model/voice ID excludes that row. Preserve vector values/audio bytes as intended user output without logging them. Do not log prompts/documents/state/answers/audio or raw response bodies.

**BR-8 — Bounded transport.** Use owned async httpx transport, no new dependency; trust_env=false, follow_redirects=false, explicit headers/auth and content type. One total30s request deadline, at most15s per actual attempt, at most existing max_failover_attempts (default3) and no internal SDK retries. Effective byte bound is8MiB for each complete JSON or audio response, incrementally checked after decompression, including error bodies under a stricter64KiB cap. Request timeout/client disconnect/cancel closes active response/client and releases all permits/tickets in finally. No temp files/spooling of audio or provider output. Source/input/output limits are deterministic local policy, not claims about provider limits. No automatic rate-limit/balance exhaustion probes.

## 7. Routing, shared safety and delivery

**BR-9 — Exact semantics.** Target selection is exact task/provider/raw identity with captured source revision and request compatibility; no chat alias or cross-model fallback. When an independently equivalent upstream route does not exist, return503 rather than substitute. In v1 there is one provider and one route per target; perform at most one actual send to that route for a consumer request. Existing attempt ceiling is an upper bound, not a reason to repeat the same failing route. Retry/failover framework must skip exhausted routes; circuit/quota waits do not sleep inside requests. An embedding dimension/index mismatch is a protocol fault; never split a batch across models, infer equivalence from dimensions or canonical spelling, or hide a changed model/revision behind masking. If source has no immutable revision, expose that absence in diagnostic capability metadata and document that upstream silent weight changes cannot be detected; exact ID pinning is not an immutable-vector-space guarantee. Clients must pin/version their index lifecycle independently.

**BR-10 — Shared protection.** All task routes sharing logical provider and resolved credential share credential auth/quota and a conservative financial umbrella that also blocks accepted chat. Task source/endpoint/profile binding and service breaker state remain distinct. Reuse/refine existing controllers through additive hooks, not separate uncoordinated copies. A new-task401 cannot be escaped by another task or source/profile change with the same credential; catalog401 is not an inference auth latch. New-task402/financial incidents block sibling tasks/chat consistently; task-specific HTTP429 shares credential quota,5xx/protocol health stays route-specific. Existing protected scopes/active I/O and umbrella latches survive pruning, source refresh and router/orchestrator recreation within the same retained registry/controller ownership domain; no removal or late success clears them. An independently created registry/isolated application has separate state, as in the accepted architecture. Replacing the primary registry without process restart is unsupported in this version and is not an exposed reset action; do not introduce process-global state that couples isolated applications. Endpoint/task changes must not create an unlatched sibling of the same financial account. Retain existing process-local/restart limitations; no new reset API. Use captured binding/generation/identity fencing, not serialized key fingerprints. All-or-none acquisition with no await before owned send; check eligibility, source/credential freshness, request capability, financial/auth/quota/service gates immediately before each actual send. Local skips create zero upstream attempts.

**BR-11 — Cost and delivery outcomes.** Task monetary parsers require task-specific documented payer/currency mapping; never reuse a chat mapping just because provider ID matches. S4 includes a numeric usage.cost example but does not establish its payer/currency semantics for this task. All four task monetary results therefore remain unavailable in this version until a sourced task-specific mapping is separately approved; token/search counts, a field named cost and audio bytes are never monetary estimates. Preserve the existing guard mechanism for recognized chat observations and cross-task propagation of its positive/invalid-charge latches. Never claim actual task monetary monitoring from an unverified mapping. Enforcement, not post-hoc cost inspection, gates dispatch. Existing balance classification is reused only for documented same-provider labels; generic402 remains a conservative financial hold, not invented quota classification.

Mark a syntactically valid complete result complete before applying a concurrently observed shared billing incident (including recognized chat monetary observations). Deliver it successfully while latching all subsequent sibling dispatches; retain separate incident and delivery outcomes. Concurrent incomplete work interrupted by a financial hold cannot dispatch again to evade it. All nonchat delivery is fully buffered: validate body/shape first, then send one response. Before completion failover may use only independently admissible exact-equivalent unused routes (none in v1); after headers/body start, no restart, replay or audio splicing. Downstream failure is distinct from upstream health; successful upstream work does not clear a newer latch. Chat's existing complete-answer/SSE semantics remain unchanged. Never send an SSE error event into an audio stream.

**BR-12 — Errors and diagnostics.** New task endpoints:401 authentication failure;400 closed-profile/task mismatch;404 unknown task target;503 known but price-unknown/paid/expired/health/financial/auth blocked or no safe route;502 final malformed upstream protocol. All use redacted OpenAI-style error envelope and X-Request-ID. Do not expose upstream body, credential, billing identity or arbitrary headers. Do not echo Retry-After until safely normalized under T-009. Preflight includes known diagnostic inventory so unknown free status does not masquerade as a404 missing model. Log one bounded task event per consumer request with task, request ID, safe public target, attempt count, delivery outcome and finite failure code; separate financial incident. No new telemetry database or changes to old chat trace/stats schemas. Sanitize new endpoint422/default exception responses; no raw Pydantic inputs.

## 8. Architecture and edit boundary

Existing Python/FastAPI/httpx/Pydantic stack, no new runtime dependencies/storage/service. Proposed relationship: existing orchestrator -> owned task catalog/evidence; explicit task handlers -> closed validators -> exact task router -> task transport; registry owns task store and shared billing/resilience. The chat router keeps its current contracts. Protocol-specific task parsing is compatible with DEC-002's declarative provider identity; it does not authorize arbitrary executable expressions or custom provider adapters. During implementation append approved task-specific exact-target/guard notes to relevant decisions and architecture; do not rewrite old decisions as if already nonchat-aware.

| MAY EDIT path | Purpose |
|---|---|
| backend/app/core/tasks/ (new) | Catalog, evidence, profiles, validation, exact router and task transport |
| backend/app/core/providers/registry.py | Owned task state, safe lifecycle/pruning and cross-task guard hooks |
| backend/app/core/discovery/orchestrator.py | Single-worker bounded task job integration/fairness |
| backend/app/core/eligibility/billing.py | Additive financial umbrella/owned I/O integration preserving chat and constructor contracts |
| backend/app/core/balancer/resilience.py | Additive task-route vs shared credential hooks preserving accepted health semantics |
| backend/app/api/v1/__init__.py, models.py; backend/app/api/v1/tasks.py (new) | Mount task routes and explicit task catalog query |
| backend/app/api/admin/__init__.py; backend/app/api/admin/models.py (new) | Mount safe privileged diagnostic catalog |
| backend/tests/test_task_*.py (new), backend/tests/task_fixtures.py (new) | Task, cross-task safety/race, protocol and real-socket tests |
| scripts/probe_task_inference.py (new) | Finite isolated task probe below |
| README.md, VISION.md, ARCHITECTURE.md, ROADMAP.md, TASKS.md, HANDOFF.md; docs/recon/T-010-task-specific-inference.md; notes/T-010-results.md (new); notes/next-steps-current-checkpoint.md | Affected instructions/status/source/BR-AC evidence |
| docs/decisions/DEC-002-declarative-provider-schema.md, DEC-003-canonical-model-mapping-and-harness-interop.md, DEC-005-adaptive-resilience.md | Append approved task-specific refinements only |

DO NOT TOUCH: real.env/.env/keys/confirmation entries; main.py; api/admin/providers.py; providers/validation.py and validation_models.py; test_provider_validation.py and test_provider_validation_live.py; scripts/probe_provider_validation.py; current chat.py, chat request/evidence/account/probes policy, adapter/openai_client.py, balancer/router.py; providers.yaml/model_aliases.yaml; NVIDIA discovery; all other existing tests/configuration/dependency/stack/UI/runtime paths; PROJECT-PROCESS.md/AGENTS.md process rules; other specs; Git history/remote. Shared guard hooks may read existing interfaces; if a protected change is genuinely needed, propose an amendment first. Do not weaken a test to get green.

## 9. Ordered stages and regression gates

- **N1 — Identity, catalogs and proof lifecycle:** task storage/binding/source snapshots, public task query and privileged inventory, source restrictions/strict unknown policies. Full existing regression plus targeted source/TTL/namespace tests; no inference.
- **N2 — Embeddings and rerank:** closed text protocols, exact-target router/transport, vector/index validation and shared financial/auth/quota integration. Real loopback success/failure/limits, cross-task races and full regression. Rerank remains externally gated by section5.
- **N3 — Decisions and speech:** typed question/answer validation, bounded raw audio protocol, safety/cancel handling; no fake live admission for gated speech. Loopback protocol/cost/complete-answer tests and full regression.
- **N4 — Cumulative independent review and delivery ledger:** review whole candidate, real sockets through an isolated complete application/lifespan, optional eligible external packet, docs/operator guidance and BR/AC reconciliation. Protected-file and runtime hashes, exact candidate identity. No primary activation.

## 10. Acceptance criteria and traceability

The sources below distinguish settled requirements from design submitted with this version. Local limits/interfaces are proposed policy, not claimed upstream limits.

| BR | Source / authority |
|---|---|
| BR-1 | Accepted [T-007 hybrid](T-007-hybrid-account-eligibility.md), [T-009](T-009-adaptive-circuit-breaker.md), baseline in Input RECON; D2/D3 exceptions pending approval |
| BR-2 | Owner's current dynamic-free requirement, VISION section2, accepted T-007 contracts |
| BR-3 | Input RECON registry/evidence observations; independent additive-layer proposal and D3/D4 |
| BR-4 | Owner's task-separated catalog request; DEC-003 memory-only chat listing; D2 |
| BR-5 | Existing orchestrator bounds in Input RECON; S1/S2 catalog contracts; D3 scoped lifecycle proposal |
| BR-6 | Owner's preserved free constraints; S2/S6/S7 evidence limits; D6 conservative source interpretation pending approval |
| BR-7 | S2–S5 protocol contracts; D4/D5 narrowed request profiles and proposed local bounds |
| BR-8 | Existing httpx ownership/privacy model in Input RECON; D5 proposed nonchat resource bounds |
| BR-9 | Independent vector-space/semantic assessment; D4 exact-target policy pending approval |
| BR-10 | Accepted [DEC-005](../docs/decisions/DEC-005-adaptive-resilience.md)/T-009 account guards; proposed D3 cross-task extension |
| BR-11 | Owner-settled complete-answer/no-replay decisions in T-007; S4/S5 monetary limitations; D5/D6 |
| BR-12 | Existing chat auth/redaction/correlation contract; D2/D3 proposed task diagnostics/error extension |

| AC | BR | Scenario / method | Exact expected evidence |
|---|---|---|---|
| AC-1 | 1 | Full pre/post backend regression; protected path hash audit | Original493 behavior preserved plus new tests; list actual passed counts, no protected changes |
| AC-2 | 3,4 | Same raw ID in multiple task snapshots; inspect no-query/chat/task/admin lists | No collisions/replacement; old chat JSON unchanged; nonchat never enters default picker; explicit lists show only eligible task rows |
| AC-3 | 3,5 | Source removal/failure/duplicate/overflow/TTL/credential change; concurrent late refresh | Immediate affected-task revocation; no other task/chat loss; stale publication blocked; catalog reads zero network/mutation |
| AC-4 | 2,6 | Table-driven pricing/enforcement cases and owned outbound capture | Missing request unknown; positive paid; invalid/unknown fee unknown; no chat exception transfer; mandatory zero ceilings on every eligible embedding/decisions send |
| AC-5 | 2,6 | Rerank/speech positive-looking catalog and existing direct-provider assertions | Visible unknown diagnosis, no eligible public entry and zero external/qualification inference; toggling a flag/list cannot bypass |
| AC-6 | 7,12 | Auth-first adversarial validation, duplicate JSON/oversized/nested/unknown/URL/schema instructions | Exact redacted401/400/413, no secret/body echo and zero outbound; data instructions cannot alter route/policy |
| AC-7 | 7,9 | Embedding multi-input/dimension/index/nonfinite/wrong-model fixtures | Valid full vectors preserve order/model; invalid full response rejected; no batch split or model substitution |
| AC-8 | 7,9 | Rerank top_n/results/indices/scores fixtures | Original document mapping/order retained, invalid rows rejected; no fallback to chat |
| AC-9 | 7,9 | Each decision primitive plus wrong labels/type/sum/NaN/prose | Typed valid result; malformed502, no repair or schema/model substitution |
| AC-10 | 7,8,11 | Real socket mp3/pcm success, wrong MIME/JSON/empty/oversize/truncated transport and cancellation | Full bounded audio or redacted pre-output error; no partial audio/replay/splice; all I/O closed |
| AC-11 | 1,10 | Cross-task401/402/429/5xx; prune/refresh/router recreation; paired concurrent recovery | Account guards shared with chat; service state distinct; stale success cannot clear guards; exactly one owned quota recovery |
| AC-12 | 8,10 | Credential/source/policy/latch race between resolution and send; cancellation-suppressing transport | Final recheck prevents invalid send, no permit/response leak, zero attempts for skips |
| AC-13 | 10,11 | Complete valid task result concurrent with recognized chat positive/invalid cost or documented402 hold; task usage.cost sentinels | Completed answer delivered success, financial incident separate, future siblings blocked; task monetary value unavailable, no inference from field name; no delayed complete result lost |
| AC-14 | 4,12 | Secret sentinels in IDs/voice/body/errors/logs/catalog; existing telemetry schema comparison | No credential/scope/raw output leakage; bounded task events; chat traces/stats unchanged |
| AC-15 | 5,8 | Real-loopback full application lifespan with slow/failed task source and concurrent chat health/probes | No worker duplication/starvation, shared4-concurrency/bounds,30s cycle/15s operations, proper shutdown |
| AC-16 | 1,12 | Actual new CLI --help, no-credential and denied eligibility runs | Strict bounded/redacted diagnostics, zero inference when blocked; command below demonstrably exists after implementation |
| AC-17 | 1..12 | Independent cumulative source/code review, scope and BR/AC reconciliation | No unresolved material finding; distinguish root checks, independent review and real delivery; all outputs hash-bound |
| AC-18 | 2,6,8..12 | Bounded external delivery packet per task through isolated proxy | Positive free live delivery recorded separately for all four tasks or affected task OPEN/UNVERIFIED. Unknown/empty/mocks cannot pass this AC; no full T-010 closure without positive proofs |

## 11. Delivery and limited live packet

Required future tool (does not exist at spec preparation): `.venv/bin/python scripts/probe_task_inference.py --task TASK --max-sends 1 --output /tmp/t010-TASK.json`. CLI accepts exactly embeddings/rerank/decisions/speech; sends range0..1, default0. No URL/key/model-ID/free-override argument. Select deterministically from current eligible task inventory in lexical public-ID order and validate captured binding at send. No manual candidate list. Mode0 validates local/preflight diagnostics only, never inference. `--help` and no-credential/blocked cases are actual CLI acceptance checks.

After implementation approval, N4 may run one isolated application/socket per task using actual owned lifespan and existing key resolver without printing keys. Construct isolated settings/registry with only the existing OpenRouter manifest and empty account confirmations, without modifying any environment file; disable unrelated/private qualification before startup and instrument outbound sends to prove no background inference. Task catalog GETs may run, but no chat/private/direct-provider generation is permitted. If isolation cannot be established, stop before startup rather than importing the primary's confirmations. No primary restart/configuration/account changes. At most **one external inference send per task, four total across this version**, no automatic private qualification or retries; persist consumed budget before uncertain send and never reset on script restart. Model/source catalog GETs remain bounded by section4 and do not count as inference. One embedding text of<=32 chars; one rerank query<=32 chars plus two documents<=32 chars each; one decision state<=64 chars and one yes/no question<=64 chars; speech text<=32 chars, one source-supported preset voice/format. These tasks do not accept chat max_tokens uniformly: do not pretend all probes are capped32 output tokens. The strict evidence policy must admit the exact request before any send; current rerank/speech evidence gates prevent those external sends until separately approved amendment.

Tool uses a private0600 process-local send ledger `/tmp/t010-live-budget.json`, monotonic budget in the isolated run, safe0600 JSON diagnostics and no prompts/output/vector/audio/keys/scope fingerprints in the report. Record task, candidate-safe ID, verified source/profile revision, assurance, actual send count, HTTP/protocol/delivery outcome, bounded sizes/counts, recognized monetary observation or unavailable, timestamps and candidate hashes. No committed private captures. Ledger failure/unknown outcome fails closed. Concurrent runs need atomic ledger ownership; no claim of multi-host budget durability.

Observe actual proxy response, task structure and correlation-bound sanitized event; do not call direct upstream delivery proxy proof. The complete test consumer validates audio/container or vector semantics structurally in memory without storing content. Unsupported enforcement, absent request prices/voices, missing credentials/quota, or no eligible candidate => UNVERIFIED with exact reason, zero sends. Actual unknown-cost result cannot retroactively establish free eligibility. Do not exhaust quota to test errors. Use loopback fixtures for401/402/429/cost incidents. Failed or inconclusive live sends consume their budget and remain recorded; another packet needs owner approval. Successful fixture delivery is mandatory even for externally gated profiles, but never replaces external proof.

## 12. Risks, gaps and approval consequences

- Complete free evidence is currently missing for observed zero-token embedding/decisions rows with absent request price. Rerank search-unit enforcement and speech free-enforcement are unverified. This version fixes the contracts/catalog architecture while failing closed; it does not promise immediate activation of four free task pools. Unlock amendments must name their sources, revised BR/AC and live bounds.
- Exact ID pinning cannot detect silent upstream weight/revision changes; no immutable embedding space is guaranteed when the provider supplies no revision. Clients own index versioning/rebuilds.
- Decisions is alpha; incompatible schema changes produce unavailable/unsupported rather than permissive passthrough. Source content may change independently of the pinned local parser.
- Speech MIME/prefix checks are structural, not a full decoder or quality test; full buffering limits latency/maximum duration and is intentional. No speech cost is inferred from audio length.
- Cross-task guard integration is the largest regression risk. Distinguish route health from credential/financial umbrella, retain scope fencing/pruning ownership and independently review cumulative races before live work.
- Narrow request subsets reject otherwise valid newer SDK/provider features. README must document each task's supported fields and returned503 reasons; no generic full-OpenAI compatibility claim.
- Source URLs/types are checked primary interfaces; prices/account state and current inventory are not permanent facts. Preserve no-manual-list policy even if sources temporarily leave every pool empty.
- Full implementation approval is pending. Proposed architecture/choices are not yet binding DEC updates. No implementation deviations at preparation; later deviations require disposition in notes/T-010-results.md and exact approval for changed contract/boundary.


$END_BODY
$START_LINKS
IMPLEMENTS: VISION.md sections 2 and 4; ROADMAP.md P2 / T-010
IMPACTS: docs/decisions/DEC-002-declarative-provider-schema.md; docs/decisions/DEC-003-canonical-model-mapping-and-harness-interop.md; docs/decisions/DEC-005-adaptive-resilience.md
REQUIRES: T-010 Input RECON; accepted T-007/T-009 operational baseline
$END_LINKS
$END_ARTIFACT_GOAL_TASK_INFERENCE
$END_SECTION_FEATURE
$END_DOCUMENT
