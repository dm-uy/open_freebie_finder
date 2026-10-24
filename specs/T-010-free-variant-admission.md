# SPEC-T-010 v1.1.0 — Dynamic Free-Variant Admission Amendment

- **Profile:** BROWNFIELD — correct admission and speech validation in the accepted partial task subsystem.
- **Version / status:** 1.1.0 / approval candidate; independent reviews completed with clarifications; implementation approval pending.
- **Route:** P2 / B-002 / T-010, before T-008.
- **Base:** [v1.0.0](T-010-task-specific-inference.md), accepted partial result; full AC-18 remains open.
- **Input RECON:** [Admission amendment](../docs/recon/T-010-admission-amendment.md).
- **Authority:** Owner requested read-only recon and an amendment on2026-10-23. No amendment implementation, inference or primary activation is authorized yet.

$START_DOCUMENT
PURPOSE: Admit dynamically published free task variants without manual model lists.
SCOPE: OpenRouter embeddings, rerank, decisions and speech; preserve accepted task and chat boundaries.
KEYWORDS: T-010, P2, free-variant, dynamic-eligibility, speech
$START_DOCUMENT_PLAN
$DOCUMENT_PLAN
GOAL: Source-bound free variants enable four task protocols => GOAL_TASK_FREE_VARIANTS
$END_DOCUMENT_PLAN
$START_SECTION_FEATURE
$START_ARTIFACT_GOAL_TASK_FREE_VARIANTS
TYPE: GOAL
KEYWORDS: free-evidence, exact-target, no-paid-fallback, task-catalog
$START_CONTRACT
PURPOSE: Replace conservative evidence gaps with a documented bounded admission basis.
DESCRIPTION: Check fresh exact free-variant entries, validate all published fees, and preserve task semantics and financial holds.
RATIONALE: Missing optional request pricing and unavailable numeric ceilings currently exclude every observed task route.
ACCEPTANCE_CRITERIA: AC-A1 through AC-A12 and traceability.
$END_CONTRACT
$START_BODY
## 1. Outcome, authority and precedence

**Done when:** A1–A3 meet AC-A1..12, all preserved base criteria pass, independent cumulative QA is clear, and four actual free task deliveries meet base AC-18. Each missing positive delivery remains OPEN/UNVERIFIED; a new partial result requires honest disposition, not a mock pass. Neither a public free catalog entry nor a successful local socket test proves external delivery.

**Stop and ask when:** Evidence needs a wider interpretation than this amendment, another upstream, alias equivalence, unknown price units, paid/conditional-account fallback, more sends, an extra protocol/dependency/store, protected edits or primary integration. Complete independent safe work first. Ordinary source outage/rate limiting means unavailable, not permission to widen admission or keep probing indefinitely.

Approval of this exact version would settle proposals A-D1..4 and authorize ordered A1–A3, including the finite isolated packet in §8. It would not authorize primary restart/activation, commits/push or deployment. Current authority is preparation only. The owner's acceptance of v1.0.0 partial implementation is recorded in [results](../notes/T-010-results.md); it does not close AC-18.

After approval, this amendment takes precedence only over: base §5 fee/enforcement admission rules; the mandatory voice/model-specific format restrictions in the speech profile; source-revision normalization; and the original one-send-per-task verification packet. It also supersedes any other base wording that unconditionally keeps rerank/speech externally gated or equates absent task ceilings with rejection. In base BR-11, the assertion that enforcement gates dispatch is replaced only by BR-A2..4's explicit source-contract assurance plus owned exact dispatch; all monetary unavailability, latch propagation and402 classification rules remain unchanged. Base BR-1/BR-2, exact-target semantics, all remaining protocols/limits, AC-1..18, privacy/auth/quota/guard invariants and scope protections remain binding. Historical base text stays readable with a cross-reference banner. No chat missing-request exception or account assertion is transferred into this profile.

## 2. Measured context and consequential choices

Input baseline: main `78a1aa4790293781aafe81e786ee4e3b7f098ef2` plus the accepted uncommitted 81-file runtime candidate. Retained final base tests:658 passed/36.82s; not a new run during this documentation-only preparation. Public unauthenticated catalog reads on2026-10-23 found exact free variants in all four task catalogs, often with only prompt/completion prices. Counts are observations in RECON, never model lists. No inference or secret-file access occurred in preparation.

Two independent read-only proposals and root's separate assessment support the following approval candidates; [RECON](../docs/recon/T-010-admission-amendment.md) records alternatives, facts and limits.

| ID | Proposed choice | Rejected alternative / consequence / reconsideration |
|---|---|---|
| A-D1 | Replace the v1 task admission predicate with `catalog_free_variant` assurance based on OpenRouter's documented exact published free variant, fresh task metadata and noncontradictory prices | Requiring absent optional request prices or numeric coverage of every task keeps all four blocked; treating omitted fees as zero or using successful probes as price proof is unsound. Revisit on contract change |
| A-D2 | Exact task catalog is authoritative; endpoint-detail API remains diagnostic, not an extra scheduled admission dependency | Mandatory endpoint fan-out adds state/requests and still does not fill missing fees. Revisit if actual routing contradicts the catalog contract |
| A-D3 | Speech voice optional; default format pcm; explicit voice only from fresh supported_voices; mp3/pcm from documented API schema | Invented voice tables or fabricated model-specific formats cannot be verified. Omitted voice may still fail upstream; never assert universal default-voice availability |
| A-D4 | Retain exact response identity, no nonchat cascade, no monetary mapping, finite two-send allowance per task | Permissive alias stripping and arbitrary cost fields hide identity/billing errors. Evidence for a response alias or money field needs another bounded amendment |

These are proposed owner decisions, not as-built changes. Free-variant assurance depends on the provider's published contract; it is distinct from complete numeric price-cap enforcement and independent billing verification.

## 3. Business requirements and sources

**BR-A1 — Preserve contracts.** Keep every base invariant except the explicit §1 changes. Preserve existing chat lists, strict chat admission, account confirmations/leases, shared financial/auth holds, T-009 state/recovery, T-006 isolation, no-key leakage, one exact nonchat send per consumer request, buffered delivery and all current resource limits. Do not migrate or overwrite chat evidence. Source: accepted base BR-1/BR-2 and owner's request to retain dynamic free checking/task separation.

**BR-A2 — Dynamic variant assurance.** Replace the prior v1.0.0 nonchat admission predicate, including its complete-three-price branch; this amendment does not retain a parallel base-ID admission path. For each of the four tasks admit only an exact current published `:free` ID from the owned task catalog, with text input and output_modalities exactly `[task]`, no explicit disabled/negative task capability, and valid zero prices under BR-A3. The suffix alone is insufficient: appending it to an absent ID never creates evidence. Use `basis=catalog_free_variant`, `assurance=provider_free_variant_contract`; this does not claim atomic price-cap coverage. A fully priced base variant is not admitted even when its current prices are zero; preserve visibility as unknown. A positive published monetary fee is paid/ineligible regardless of variant label. Source: [Free Variant contract](https://openrouter.ai/docs/guides/routing/model-variants/free), [models API](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties), dated task catalog observations; applying that general variant guarantee to these four explicit task entries is the bounded A-D1 interpretation submitted for approval.

**BR-A3 — Typed pricing with no invented zero.** Require explicit valid nonnegative finite decimal prompt and completion values, both zero. Recognized additional monetary keys are request, audio, audio_output, image, image_output, image_token, input_audio_cache, input_cache_read, input_cache_write, input_cache_write_1h, internal_reasoning, web_search. Every present monetary value must be valid zero. A positive recognized fee means paid/ineligible, invalid data or an unknown pricing key means unknown/ineligible. Absent optional values remain absent in normalized evidence. Accept optional numeric nonboolean finite discount in [0,1] only as metadata; never use a discount to admit a positive base fee. Accept absent or empty-list overrides only; all other overrides remain unknown. Nulls, booleans, negative/nonfinite values and oversized decimal strings never count as free; retain the128-character monetary-string bound. Field recognition is a versioned protocol schema, not a model list. Source: official [PublicPricing SDK schema](https://raw.githubusercontent.com/OpenRouterTeam/python-sdk/main/src/openrouter/components/publicpricing.py); source-snapshot identity must be saved during implementation, no runtime SDK dependency needed.

**BR-A4 — Owned exact dispatch.** Freeze the exact task/raw free ID, source/profile revision and effective owned routing policy together. Immediately before the one upstream send revalidate current source, credential epoch/profile, TTL, binding and financial/auth/quota eligibility after all awaits. A changed entry, price/capability/policy or key invalidates prior evidence; source failure never reuses last-known free admission. No client provider overrides, models fallback arrays, plugins, paid search/tools, BYOK configuration, router IDs or arbitrary passthrough fields. Preserve exact owned task URLs and no redirects/ambient credentials. The payload keeps the admitted free ID byte-for-byte; no base-ID substitution. Retain the existing zero prompt/completion/request string caps and require_parameters for embeddings/decisions as defense in depth. For rerank/speech use only the documented closed task request; do not inject unsupported price/search-unit controls or label them enforced. Upstream routing within that exact published free variant relies on the variant contract, never an application fallback to another model. Source: base exact-target/security contracts, [ProviderPreferences schema](https://raw.githubusercontent.com/OpenRouterTeam/python-sdk/main/src/openrouter/components/providerpreferences.py), task API schemas and free-variant paid-fallback warning.

**BR-A5 — Speech protocol correction.** Only model and input are mandatory. Omitted response_format normalizes to pcm; explicit format is mp3 or pcm. Omit voice upstream when absent; do not choose/invent a voice. If voice is present, require the existing bounded string plus membership in the current source-supported_voices list; missing/empty metadata cannot authorize an explicit voice. API format support is a protocol enum, not fabricated per-model metadata. No machine mapping for per-model format support/denial has been established. Do not infer one from arbitrary keys or prose, and do not publish fabricated per-model format lists. Allow either documented protocol format with an honest upstream error if a particular route rejects it; introducing a per-model mapping requires reviewed source/schema evidence. Retain speed absent/exact1,512 input characters, no instructions, cloning, references, multi-speaker or streamed audio. Fully buffer and validate the chosen format using base byte/content-type/size rules. Source: [speech API](https://openrouter.ai/docs/api/api-reference/tts/create-speech), [official TTS guide](https://openrouter.ai/blog/tutorials/text-to-speech/). The tutorial advises omission only when a provider documents a default; the API itself makes voice optional. A-D3 deliberately proposes allowing omission without asserting a default voice or availability, relying on an honest upstream rejection when unsupported. This source tension and bounded interpretation require exact amendment approval.

**BR-A6 — Honest evidence lifecycle and diagnostics.** Memory-only TTL/public-list purity, bounded task discovery and duplicate/incomplete-catalog rules remain. Bind the normalized revision to task, exact ID, architecture, recognized pricing INCLUDING optional presence and discount/overrides, relevant capability data, assurance/profile revision and dispatch policy; never hash/publish arbitrary raw content or credentials. Any changed fact cannot silently retain a previous revision. Diagnostic output exposes safe basis/assurance and fixed reasons, never key/epoch/private binding; distinguish price/capability evidence from route health and positive live proof. Current shared monetary observation stays unavailable, not zero; do not infer cost from unknown usage fields. An existing OpenRouter financial/account latch vetoes this assurance across chat and tasks and cannot be cleared by refresh. Source: base lifecycle/privacy/financial contracts and T-007/T-009 guard decisions.

**BR-A7 — Verified bounded delivery.** Preserve regression baseline by behavior, add discriminating admission/lifecycle/protocol/socket tests, independent cumulative QA and actual short isolated deliveries for all four tasks. Production code contains no model allowlists; probe selection uses the freshly eligible catalog with deterministic sorting. Probe failure never certifies price/free access. Retain all failed/uncertain attempts and ledger reservations; no implicit reset after CLI restart or version change. Source: owner request and base AC-18/live-proof requirements, narrowed finite packet §8.

## 4. Expected architecture and preserved semantics

Existing stack and dependencies unchanged. The registry-owned TaskCatalog gains a versioned variant-pricing interpretation; TaskDiscovery retains four owned source jobs and current bounds. TaskExecutor distinguishes admission assurance from optional owned provider controls, removing the current generic `policy is not None` eligibility gate for these four proven variants. An absent numeric-cap object alone is neither positive evidence nor a veto when BR-A2..4 hold. No generic free bypass or alternative account profile is introduced.

Source catalogs stay `/api/v1/embeddings/models` and `/api/v1/models?output_modalities={rerank|decisions|speech}`. Dispatch stays `/api/v1/embeddings`, `/api/v1/rerank`, `/api/alpha/decisions`, `/api/v1/audio/speech`. Public paths and `openrouter::<raw_id>` remain unchanged; task inventories remain separate from default chat and auto:free. Canonical slug is descriptive metadata, never routing/response equivalence authority. Embedding dimensions remain source-gated; JSON response model must still match the exact requested raw ID. No reordering, padding or model substitution repairs vector/decision/rerank results.

Keep current request256KiB, response/audio8MiB, errors64KiB, request30s/upstream15s, source4MiB/1000 rows, four-slot source concurrency, existing configured refresh/TTL, cancellation/resource closure and safe errors. No extra scheduled endpoint-detail HTTP calls, HTML parsers, automatic qualification or new background inference. Untrusted input strings and catalog descriptions cannot alter route/policy; closed structural fields and an adversarial input test verify this without interpreting embedded instructions.

## 5. Boundaries and editable paths

**Always:** retain fail-closed contradictions and current guards; use authoritative dynamic catalogs; mark missing delivery UNVERIFIED; save revision-bound evidence and observed failures; synchronize only affected records.

**Ask first:** scope/profile/price-source expansion, alias equivalence, new dependencies or storage, higher live budget, protected changes or primary integration. Existing exact approval of A1–A3 would suffice for that work; do not request it again after every bounded failed attempt.

**Never:** manual model/voice allowlists, suffix synthesis, price guesses, paid fallback, retries that exceed ledger reservations, real keys in records, primary restart or publication without separate authority.

**MAY EDIT after approval:**
- `backend/app/core/tasks/**`: admission schema, snapshot binding, speech profile, owned policy/dispatch and safe diagnostic changes only.
- `backend/app/api/v1/tasks.py`, `backend/app/api/admin/models.py`: only related schema/diagnostic integration if required; keep existing public paths/auth/order.
- `scripts/probe_task_inference.py`: finite amendment ledger, speech default path, deterministic source selection, safe proof reports and actual CLI execution.
- `backend/tests/test_task_*.py`, `backend/tests/task_fixtures.py`: additive amendment regressions and socket/CLI coverage; preserve previous assertions unless the explicitly superseded profile changes them.
- `specs/T-010-free-variant-admission.md`, base T-010 status/precedence banner only; `docs/recon/T-010-admission-amendment.md`; `notes/T-010-results.md`, optional `notes/T-010-admission-results.md`, `notes/next-steps-current-checkpoint.md`; `README.md`, `VISION.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `TASKS.md`, `HANDOFF.md`; append-only relevant notes in `docs/decisions/DEC-002-declarative-provider-schema.md` and `DEC-003-canonical-model-mapping-and-harness-interop.md`. Label proposal versus verified as-built.

**DO NOT TOUCH:** `.env`/real credentials, settings/confirmations, `.env.example`, providers.yaml/model_aliases.yaml, chat API/router/adapters, `core/eligibility/**` including request/account/probe/billing mechanisms, `core/balancer/**`, `core/discovery/**`, registry.py and main.py, provider validation/admin providers and their probes/tests, other existing tests, other approved specs/decisions, dependencies, frontend, AGENTS/PROJECT-PROCESS rules, Git history/remotes. If code shows an actual needed exception, prepare the concrete scope change before touching it. This tighter amendment scope intentionally does not reopen all base MAY EDIT paths.

## 6. Ordered implementation stages (approval pending)

| Stage | Outcome | Separate regression gate before continuing |
|---|---|---|
| A1 | Source-verified variant assurance, complete price normalization/revision, policy distinction and diagnostics | Task catalog/discovery/transport tests plus full backend regressions; all contradictions, TTL/key/policy changes and shared holds exclude sends |
| A2 | Optional speech voice/default pcm and exact task dispatch; focused sockets/CLI protocol updates | All task protocol/API/socket tests and full backend suite; old chat behavior, private data and exact vectors preserved |
| A3 | Durable finite ledger, CLI proof, independent cumulative review and bounded four-task external packet | Actual CLI/data-only execution, real sockets, independent scope/source verification, full backend regressions; BR/AC reconciliation and owner result review |

The executor may organize roles locally, but must preserve independent assessment and cumulative result QA. Record allowed paths and dirty inventory before delegation; report every out-of-scope write without reverting another writer. Commit/integration remains outside these stages.

## 7. Acceptance criteria and traceability

| AC | BR | Scenario / verification | Exact expected result and evidence |
|---|---|---|---|
| AC-A1 | A1 | Full backend baseline plus preserved base ACs | All tests pass by behavior; chat/T-006/T-009 protections untouched; dated command/output and candidate manifest |
| AC-A2 | A2,A3 | Fresh exact catalog free entries for each task, request absent and known extra fees zero | All four can be eligible under variant assurance; request remains absent; separate safe basis/assurance shown. No fixture ID copied into production tables |
| AC-A3 | A2,A3 | Missing exact free entry, synthesized suffix, zero-price base ID, wrong output/input, disabled/negative capability | Never eligible/send; exact supported text task free entry remains eligible even if other input modalities are also listed |
| AC-A4 | A3 | Positive fee (including auxiliary), unknown fee key, invalid/negative/nonfinite/bool/null/oversized price, malformed discount, nonempty overrides | Paid/unknown with zero sends; discount1 never rescues positive base prices; zero recognized fees and empty overrides accepted |
| AC-A5 | A4,A6 | TTL, source failure/incomplete/duplicates, same-ID price/capability changes, key A→B→A, policy/profile change | No stale admission; revisions change for evidence changes, old bindings cannot send; public reads produce no network/reservation/mutation |
| AC-A6 | A1,A4,A6 | Existing cross-task/account latch, auth/quota hold, concurrency/cancel before send | Held requests cannot send or reset holds; privacy/cancellation invariants and terminal tracing preserved |
| AC-A7 | A4 | Inspect captured real-socket outbound requests for all four tasks; adversarial input asks to change model/policy | Exact admitted free ID and owned URL, no fallback/addons/passthrough; emb/dec retain owned zero caps; rerank/speech receive no fabricated caps; at most one send per consumer request |
| AC-A8 | A5 | Omitted voice/format; known/unknown explicit voices; mp3/pcm; forbidden references/instructions/speed and arbitrary source format keys | Omitted voice stays omitted and default pcm validates; known fresh voice allowed, unknown rejected before send; closed fields unchanged; arbitrary format metadata cannot fabricate capabilities; upstream default failure honestly redacted |
| AC-A9 | A1,A5 | Real loopback JSON/audio, wrong-model JSON, malformed vector/decision/rerank/audio, timeout/body bounds | Preserve base semantic validation; full buffer before delivery, exact response ID only, no replay/cascade, resources closed |
| AC-A10 | A6 | Key sentinels in IDs/voice/errors/pricing metadata/reports/logs, usage cost without approved mapping | No secret exposure or cost=0 invention; monetary status unavailable; pure safe diagnostics and actual reports inspected |
| AC-A11 | A7 | Real CLI help, data-only command, ledger exhaustion/restart/uncertain-send/cancel/concurrent packet tests | One shared versioned allowance2/task,8 total; no reset/overspend, reservation before send, report provenance and outcomes retained |
| AC-A12 | A7 | Independent cumulative/source/scope review, full regression gate and actual bounded task packet | Review findings resolved; four distinct actual structurally valid free task responses required for base AC-18. Any absent positive remains OPEN/UNVERIFIED |

Coverage: BR-A1→A1/A6/A9; A2→A2/A3; A3→A2/A4; A4→A5/A7; A5→A8/A9; A6→A5/A6/A10; A7→A11/A12. Base AC-18 closure still needs every task's actual positive proof, not merely amendment tests.

## 8. Delivery and live packet proposed for exact approval

Use the existing isolated CLI `.venv/bin/python scripts/probe_task_inference.py`. It creates an isolated registry/app and real loopback proxy, never primary. Existing commands: `--help`, `--task embeddings --max-sends 0 --output /tmp/t010-a-embeddings-preflight.json`. Future amended command retains the existing `--max-sends 0|1` interface and one upstream send maximum per invocation; a second invocation is permitted within the shared allowance. Repeat with task rerank, decisions or speech and unique private report names. **These are implementation-stage commands, NOT permission to execute inference during preparation.** Run documented help/data-only command for real after CLI changes; store stdout/result and final code identity.

Prerequisites: explicit approval of this exact amendment/packet, existing local OpenRouter credential loaded without displaying/persisting it, current dynamically eligible exact free candidate, no account financial/auth/quota hold, candidate/tests/private-output/ledger checks. No account funding, BYOK configuration or provider/settings changes. A zero-send source/preflight cannot consume a reserved inference send or pass delivery.

**Budget:** maximum2 reserved sends per task,8 total across A1–A3, restarts and invocations. Never spend another task's allowance. Use separate fixed private0600 `/tmp/t010-v1.1-live-budget.json` with version `T-010-v1.1.0`, immutable caps and persistent atomic reservations before a potentially sent request. Preserve old v1.0.0 ledger and attempts; new allowance is explicitly proposed here, not reset of an old packet. Count all reserved, failed, uncertain and cancelled sends; exhausted budget means stop that task, retain UNVERIFIED and report. Successful first delivery needs no second send. Second send only for a diagnosed transient/protocol issue, same exact current target or next freshly eligible sorted candidate; never retry financial/auth holds or bypass current freshness. CLI restart cannot clear an in-memory packet hold: persist a safe terminal halt reason and forbid later invocations after financial/auth incidents; no recovery is authorized by this packet. Unknown terminal outcomes require reconciliation before another send.

Inputs are fixed public synthetic text, no user content: embeddings one string <=64 characters, float encoding, no dimensions; rerank one query <=64 and two documents <=64 characters each, top_n1; decisions text state <=64 and one choice question with2 labels, question/labels <=32 characters each; speech one sentence <=32 characters, voice omitted unless exact fresh metadata authorizes a selected voice, pcm default (second send may test mp3 only after diagnosing format incompatibility). These APIs have no common32-token output cap; do not inject unsupported max_tokens. Retain512-character production speech cap and all existing production resource bounds; the packet is smaller. No automatic catalogs-wide testing.

Select candidates solely by current task admission and deterministic ID sorting, persist safe exact candidate and revision, packet/profile/version and final source hashes. Actual delivery must pass proxy status, full task protocol/audio validation and match actual/consumed upstream counts. Reports omit text/audio/vectors, keys, headers, raw bodies and private bindings; write unique owned regular0600 files under/tmp with current symlink/unsafe-file protections. Keep only safe HTTP/error classes, counters, timings, task/source/model identifiers after secret checks and unavailable monetary status. Do not claim measured zero billing when no documented cost field is available. Save aggregate redacted proof/failed attempts/AC reconciliation in result notes. Primary verification requires later separate authorization.

## 9. Risks, limits and deviations

- The variant contract is a source-backed provider guarantee, not independent atomic billing verification. Catalogs can change between refresh and dispatch; the request remains exact free variant and no application paid fallback exists. Outage, removed variants and changed schemas fail closed. If provider behavior violates the guarantee, stop the packet and use the shared guard where the documented financial signal exists; do not fabricate nonchat monetary observability.
- Cross-task application of the general variant guarantee is a bounded approval proposal. Numeric ceilings remain only defense in depth where documented; no search-unit/speech ceiling is invented. Unknown future price keys/conditional overrides intentionally block affected rows until reviewed.
- Speech's optional voice/default format are schema facts, not proof of a model's default voice, quality or availability. Current free speech metadata lacks supported_voices. An actual upstream rejection may leave speech positive proof open; no guessed voice/cloning is permitted.
- Exact response model validation may reject an otherwise valid canonicalized upstream response. Do not silently strip suffixes or treat canonical_slug as equivalence; record actual mismatch and request a scoped identity amendment if needed.
- Source SDK/docs are mutable and can disagree. Save checked source contents/digests or commit identities during implementation; source skew is not permission to forward extra fields. No SDK installation required.
- Endpoint details are useful research corroboration, not a universal live availability gate: undocumented status integers are not treated as proven health. Public observations are not inference proof or immutable inventory.
- No maintained generated code map or database schema exists in this subsystem; no database/artifact-processor check applies. Real socket/CLI/external checks apply as specified. Implementation deviations: none at preparation; record any actual deviation in result notes and obtain changed-scope approval before it is used.

$END_BODY
$START_LINKS
IMPLEMENTS: VISION.md / Zero-Cost Inference; ROADMAP.md / P2
IMPACTS: T-010-task-specific-inference.md / GOAL_TASK_INFERENCE; DEC-002; DEC-003; DEC-005
REQUIRES: ../docs/recon/T-010-admission-amendment.md; ../notes/T-010-results.md
$END_LINKS
$END_ARTIFACT_GOAL_TASK_FREE_VARIANTS
$END_SECTION_FEATURE
$END_DOCUMENT
