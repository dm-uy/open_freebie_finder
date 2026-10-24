# SPEC-T-007 — Multi-Provider Discovery and Safe Cascade Activation

> **Approved v1.3.0:** [Hybrid account correction](T-007-hybrid-account-eligibility.md) was explicitly owner-approved with H1–H4 and its bounded isolated live packet on 2026-10-23. Its section 1 supersedes the named account-mode rules, including NVIDIA strict-only handling for opted-in accounts. Unaffected contracts remain in force; primary activation and result acceptance remain separate.

- Profile: MIXED. Version: 1.1.0. Status: approved. Implementation approval: owner-approved in chat on 2026-10-22.
- Phase P2 / B-002 / [T-007](../TASKS.md).
- Subsequent owner clarification: dynamic key-scoped free eligibility without manual model lists is required. [Proposed v1.2.0 correction](T-007-dynamic-free-eligibility.md) records the replacement contract and source gaps; it was owner-approved in chat on 2026-10-22 with caveats and B1–B4. This note does not retroactively change v1.1.0 approval or acceptance.

> **Contract precedence — v1.2.0 approved:** The correction's [section 1 replacement list](T-007-dynamic-free-eligibility.md#1-relationship-to-the-approved-base) supersedes this base's static certification and explicitly listed request/output/provenance semantics. Unaffected base obligations remain in force. Owner approval of the correction is recorded in that specification; historical base evidence is preserved.

- Input: [T-007 RECON](../docs/recon/T-007-multi-provider-discovery.md), baseline HEAD `6d49e2a174a111dc0a5bb8745530a97d0e9786da` plus owner-accepted T-006 working-tree candidate.
- Preparation authorized in chat on 2026-10-22. Owner explicitly requires discovery across other providers and excludes Cerebras; this does not approve the proposed implementation below.
- Implementation complete; independent runtime QA clear; result acceptance pending. Final commands, candidate hashes, live evidence and named limitations: [T-007 results](../notes/T-007-results.md). Owner explicitly confirmed free Groq/NVIDIA access for short live checks.
- Owner decision record (chat/form answers, 2026-10-22): A — defer Cloudflare as unsupported_profile with no T-007 requests; B — owner can supply Groq/NVIDIA keys, so their live generation remains mandatory; subsequent explicit answer defers Gemini live generation until its key is available, preserving implementation/local checks and keeping P2 open; C/D — accept all six design proposals and expanded MAY EDIT paths. Specific Cloudflare deferral constrains the general parsing proposal: its native parser/pagination/profile delivery is deferred, not mandatory in T-007.
- Review follow-up: AC-12 explicitly verifies memory-only listing. Version 1.1.0 records the owner's scoped live deferral without calling it a pass or weakening required Groq/NVIDIA evidence.

$START_DOCUMENT
PURPOSE: Make configured providers actually discover models and safely contribute eligible candidates to resilient free inference.
SCOPE: Shared background discovery, viable provider catalog profiles, explicit eligibility, exact model identity, provider-diverse bounded cascade and related diagnostic safety.
KEYWORDS: discovery, provider, catalog, free eligibility, canonical model, failover, P2
$START_DOCUMENT_PLAN
$DOCUMENT_PLAN
GOAL Discover configured providers and route eligible models across them => GOAL_MULTI_PROVIDER_DISCOVERY
$END_DOCUMENT_PLAN
$START_SECTION_FEATURE
$START_ARTIFACT_GOAL_MULTI_PROVIDER_DISCOVERY
TYPE: GOAL
KEYWORDS: scheduler, discovery profiles, registry, cascade, credentials
$START_CONTRACT
PURPOSE: Close the hidden gap between configured manifests and actual background discovery.
DESCRIPTION: The application polls every eligible configured catalog, isolates failures, admits only eligible chat models, and can fail over to a distinct provider while retaining OpenAI-compatible responses.
RATIONALE: A universal completion adapter and a YAML entry do not discover or activate a provider. The owner explicitly requires search for other providers, not an OpenRouter-only worker.
ACCEPTANCE_CRITERIA: AC-1 through AC-12 below.
$END_CONTRACT
$START_BODY

## Done when / Stop and ask when

Done when the shared scheduler and in-scope bundled catalog profiles work, admission/routing are verified, baseline regressions pass, and required real socket plus OpenRouter/Groq/NVIDIA external evidence is recorded against the delivered candidate. Gemini implementation and local checks remain required, while its external live generation is owner-deferred and remains UNVERIFIED until a key is available. This recorded exception permits T-007 result review but does not close P2 or prove Gemini live activation. Cloudflare must report unsupported_profile with zero calls; it is not a successful catalog probe. Any further live deferment requires its own explicit owner decision.

Do not implement until this exact scope is approved. Stop dependent profile work for an undocumented catalog shape, changed endpoint entitlement, need for paid usage or a key/plan prerequisite not supplied. Continue independent approved work; do not invent fields or replace automatic discovery with a manual list without approval. Scope, dependencies, persistence, deployment and changed public API behavior outside the exceptions below require a new decision.

## Context / sources

VISION requires dynamic free-model discovery and resilience. ROADMAP P2 promises heterogeneous providers. DEC-002 requires declarative configuration; DEC-003 requires same-model-first routing and name masking. Input RECON identifies the actual OpenRouter-only worker, lack of eligibility guard, raw-ID mapping gap, provider starvation within three attempts and unsanitized runtime error paths.

Owner-settled: Cerebras excluded from T-007 and revisited separately. GitHub Models is retired according to its current primary documentation. Neither is replaced with a paid service. Generic scheduler logic must not contain an OpenRouter-only dispatch condition.

## Considered options and owner-agreed decisions (2026-10-22)

| Question | Alternatives / consequences | Owner-agreed choice |
|---|---|---|
| Coverage | One Groq adapter is smaller but leaves the reported discovery gap; simultaneous provider-specific engines duplicate lifecycle/error logic. | One shared scheduler, declarative profiles for all viable bundled providers. Implement in small steps, accept the whole stated scope, not just the first provider. |
| Parsing | Assume every endpoint returns data/id, or describe native envelopes explicitly. | Support verified OpenAI data profiles in T-007; preserve the profile abstraction for other envelopes. Cloudflare native envelope/pagination is deferred by the more specific owner decision A; built-in Cloudflare always reports unsupported_profile without I/O. Unknown custom profile is a reported unsupported_profile. |
| Free admission | Assume all_available means free, or require evidence/explicit account policy. | Zero-price rule for OpenRouter; local configured models allowed; other cloud providers need explicit operator confirmation of free access plus chat-model allowlist. Discovery itself still runs without routing confirmation. |
| Identity | Heuristically strip version/size/instruct suffixes, or maintain exact aliases. | Versioned exact (provider_id, raw_id) aliases; unmapped new-provider IDs stay provider-qualified and distinct. No speculative same-model merges. |
| Cascade bounds | Increase the ceiling silently, or preserve it with provider diversity. | Preserve default three attempts, add configurable bounded ceiling and round-robin provider diversity within each tier. A budget stop is reported honestly. |
| Adaptive breaker | Fold exponential state/recovery into this already broad discovery change, or retain its P2 obligation separately. | Keep fixed cooldown semantics here; propose separate T-009 for adaptive breaker and auth-recovery policy. P2 cannot close without that obligation. |

An independent read-only architectural assessment supports these choices and verified the relevant runtime gaps. Owner subsequently accepted all six proposals and the expanded edit boundaries, with explicit Cloudflare and Gemini-live exceptions above. Owner explicitly approved v1.1.0 and authorized implementation on 2026-10-22.

## Functional contract

### Shared discovery lifecycle

Replace main.py's OpenRouter-only scheduling with one orchestrator over the registry's manifests. Startup schedules a nonblocking initial cycle; refresh every existing discovery_interval_seconds. At most one cycle overlaps none: a slow cycle is completed before the next begins. At most four providers are fetched concurrently. GET-only catalog discovery never performs a completion or calls T-006 validation to activate models. Manual rules use their configured IDs without I/O and are explicitly marked manual, not evidence of remote discovery.

For each manifest retain a bounded current status keyed by provider ID: outcome, safe code, last attempt time, last success time, catalog count, admitted count. Outcomes: succeeded, failed, disabled, missing_credentials, retired, excluded, unsupported_profile. Codes/messages are fixed safe values; no keys, arbitrary exception text, raw model metadata, prompt or response bodies in diagnostics. Status is internal service state, not a new public admin API in this slice.

Evaluate exclusion/retirement/unsupported-profile policy before enabled/key/template checks and before any I/O. Cerebras is excluded, GitHub Models retired, and Cloudflare unsupported_profile for this delivery, even if keys or enabled flags are later supplied. Keep their manifest IDs for compatibility and record why they are disabled. For viable providers, disabled manifests and missing keys/templates are skipped without network calls. A provider key permits its catalog GET; it does not assert free inference. Do not persist or rewrite keys/settings at runtime.

Use selected manifest auth, resolved account placeholders and endpoint-specific catalog URL. Client ignores ambient proxies and follows no redirects. Credentials go only to the manifest's own catalog destination, never response-supplied links. Each provider cycle has a real 15-second wall-clock network deadline, including all pages and trickle; decoded body cap is 4 MiB aggregate per provider cycle, checked incrementally. Failure of one provider never cancels others. Clients/responses/tasks close on failure, cancellation and application shutdown.

On a complete valid catalog, atomically replace that provider's admitted models, including purging removed models and clearing on a valid empty eligible set. Transport/auth/status/schema/incomplete-pagination failure preserves that provider's prior snapshot, never another provider's. Last successful snapshot remains usable for at most twice discovery_interval_seconds after success; afterwards it is omitted from routing and /v1/models until successful refresh. Missing credentials, disabling, retired, excluded or unsupported_profile status removes routing eligibility immediately. HTTP 401/403 marks discovery failed; persistent provider-level auth recovery is separate T-009 scope.

### Catalog profiles and model records

Add only backward-compatible manifest/schema fields for catalog envelope selection, literal model ID/context fields, chat admission policy and exact alias configuration. Existing manifest fields/defaults and T-006 request behavior remain compatible. No eval, JSONPath program execution, untrusted code or LLM parsing.

OpenAI envelope: object with data list. Missing/wrong envelope is schema failure. Cloudflare native success/result parsing and its item mapping are deferred; do not implement an unverified catalog profile or call the endpoint in T-007. Skip malformed model entries; deduplicate raw IDs per provider. Valid IDs are nonempty strings up to 512 characters. Context extraction accepts positive numeric values, otherwise the existing 4096 fallback; it is metadata, not a new P3 context guard.

Existing openrouter_free, all_available, regex and manual filters remain available. Regex is trusted operator configuration with the T-006 length/compile safety policy, including overflow/recursion failure. Filters do not bypass chat/free admission. Cloudflare's documented page traversal is retained as recon evidence only; its parser/pagination is outside T-007 implementation scope. For in-scope profiles, an explicit has_more, next cursor or result_info.total_pages > current page indicates unsupported pagination: fail as incomplete rather than publish a partial catalog; require a measured bounded traversal contract before calling that profile complete. Never follow a response-supplied arbitrary URL.

Provider profiles required for discovery:

| Provider | Required treatment |
|---|---|
| OpenRouter | Preserve zero prompt/completion filtering, dynamic availability and existing canonical names; migrate lifecycle to shared orchestration without duplicate polling. |
| Groq | Documented OpenAI catalog; catalog may include audio/guard/system workloads, so all_available alone cannot admit a chat model. |
| Google Gemini | Documented OpenAI catalog and chat base; exclude non-chat and unsupported/free-unknown models from routing while retaining discovery counts. |
| NVIDIA hosted | Hosted catalog was directly observed with OpenAI object/data/id shape; use that endpoint/profile. The observed list does not prove every item is chat-capable or entitled to free inference. Completion/key prerequisites remain separate. |
| Hugging Face | Correct the bundle to the documented router catalog/chat base; do not infer free use from a listed provider or advertised paid pricing. |
| Mistral | Documented models endpoint; use verified chat capability metadata and explicit free-access policy. |
| Cloudflare | Owner-deferred: outcome/code unsupported_profile, zero requests and zero routing candidates regardless of keys, account ID or enabled flag. Keep manifest ID for compatibility; return to native envelope, item identity and pagination in a separate approved scope. |
| local_ollama | OpenAI-compatible local catalog, isolated failure if runtime absent. No assertion that a local runtime is installed. |
| Cerebras / GitHub Models | Explicit excluded / retired status, zero calls. Retain IDs; do not promise active discovery or silently substitute another service. |

Never hardcode availability in Python. Alias/admission configuration is distinct from catalog discovery: only currently discovered IDs may be admitted. An allowlist can narrow an observed catalog but cannot create an available model.

### Eligibility and identity

For cloud all_available/regex/manual profiles, new manifest fields free_access_confirmed (default false) and chat_model_allowlist (default empty) gate inference. Their exact API names are part of the owner-agreed design contract. The operator sets them only after verifying the actual account/plan and supported chat IDs. Default empty/false still permits catalog discovery but admits no cloud inference model. No billing-account API or automatic paid upgrade is introduced. OpenRouter's existing zero-price policy and local auth-none profile retain their established admission behavior. In every routing path enforce is_free, current provider eligibility and snapshot freshness; unknown/paid/disabled models must not reach /v1/models or auto:free.

Add a versioned model_aliases.yaml mapping exact provider/raw IDs to canonical names with source notes. Existing OpenRouter names remain unchanged. Unknown new-provider IDs default to `provider:<provider_id>/<raw_id>`, preventing an unproven identity merge. Never strip versions, quantization, sizes or instruct suffixes heuristically. Seeds must have primary model-identity evidence; a model appearing in provider docs does not prove a free entitlement.

Incoming exact raw ID first resolves to canonical identity. If it matches multiple different canonical identities, return a safe HTTP 400 ambiguity error rather than guessing. Explicit canonical names remain valid. Model field in buffered/SSE output always matches what the client requested, including raw IDs. Aliases apply to identity, not generated response rewriting beyond this existing masking contract.

### Agreed configuration schema and admission rechecks

New fields only (existing schema semantics preserved):

| Owner | Field | Type / default / validation |
|---|---|---|
| DiscoveryRule | catalog_format | String, default openai. Only openai is supported in T-007; any other value gives unsupported_profile before I/O. Built-in Cloudflare is unsupported regardless of the default field value. |
| DiscoveryRule | pagination | Literal none, default none. No paginated profile is delivered in this scope; detected continuation yields incomplete_catalog. |
| ProviderManifest | free_access_confirmed | Strict boolean, default false; cloud all_available/regex/manual profiles only gain admission when true. |
| ProviderManifest | chat_model_allowlist | List of nonempty strings of at most 512 characters, default empty; deduplicate exact IDs. |
| Settings | routing_provider_priority | List of registered provider IDs, default empty; reject duplicate/unknown IDs with a safe configuration error. |
| Settings | max_failover_attempts | Strict integer 1..10, default 3. |
| model_aliases.yaml | aliases | List of records with provider_id, raw_id, canonical_name and source (provenance text). All required; identifier strings nonempty and at most 512 characters. Duplicate provider/raw pairs rejected; no alias chaining or heuristic matching. |

Manifest/YAML/Settings files are read at startup: external file/environment edits require restart; no watcher or config-write API is introduced. When current in-process manifest/key policy changes (including tests or a future authorized control path), every eligible-snapshot read recomputes admission. Revoking free_access_confirmed, removing an allowlisted ID, disabling a provider or losing its resolved credential immediately removes cached admission, without waiting for successful polling. Refresh success never overrides current operator policy. Invalid per-provider profile configuration yields failed/invalid_configuration before I/O while other profiles continue. Invalid global attempt/priority configuration is rejected at startup with a fixed safe error, without values or credentials.

Discovery safe failure/skip codes are fixed: invalid_configuration, unsupported_profile, missing_credentials, unresolved_template, disabled, retired, excluded, upstream_auth_error (401/403), rate_limited (429), upstream_unavailable (5xx), upstream_http_error (other non-200), connection_error, timeout, response_too_large, invalid_catalog, incomplete_catalog. Complete valid empty catalog is succeeded with zero counts, not invalid_catalog. Never copy provider error text into a code/message.

Before admitting any raw ID or canonical alias, exclude values containing a nonempty resolved configured provider credential or proxy master key as a substring. Recheck this on eligible snapshot reads as well as refresh, so key changes cannot expose a previously cached identifier. The same boundary applies before /v1/models, inference dispatch, telemetry and ordinary logs; library HTTP diagnostics in discovery/inference contexts must not expose credentials or raw bodies. As in T-006, accidental substring matches favor privacy over completeness. New tests must include reflected-secret raw IDs and aliases, plus policy revocation after a successful cache population.

### Cascade and diagnostic safety

Retain Tier 1 same-model candidates before Tier 2 alternatives. Within each tier group by provider, order providers by optional routing_provider_priority (default empty means alphabetical), order candidates by raw ID, then round-robin one candidate per provider until exhausted. auto:free uses the same provider-diverse ordering across eligible candidates. This prevents a catalog's first provider from consuming the entire attempt ceiling.

Add max_failover_attempts integer 1..10, default 3; preserve the existing three-attempt regression. Count actual upstream candidate attempts only; skipped candidates do not consume budget. Try each provider/model candidate at most once. Stop at success, exhaustion or budget. Both stop conditions return OpenAI-compatible HTTP 503 but distinguish a fixed safe budget-reached message from exhausted; never claim every provider was exhausted if the budget stopped first.

Preserve buffered and first-content SSE failover, correlation IDs and fail-safe telemetry. Retry 429/5xx/network failures using existing fixed cooldown; no exponential breaker in this slice. Repair existing adapter exception/log/terminal-error paths so raw upstream bodies and secrets cannot leak through normal logs or 503 diagnostics. Do not remove useful status/correlation metadata. Unexpected non-JSON successful responses become sanitized provider failures instead of unhandled crashes. T-006 remains non-mutating and does not activate providers.

## Business requirements

- **BR-1 — Compatibility:** sources VISION, accepted T-006, PROJECT-PROCESS. Preserve existing endpoint formats, T-006 behavior, OpenRouter canonical IDs, memory-only model listing, SSE/correlation/privacy and original test scenarios. Explicit owner-agreed exceptions: reject ambiguous raw IDs; omit noneligible/stale providers from model listing; provider-diverse order; safe budget/exhaustion diagnostics; additive optional config; disabled excluded/retired/unsupported profiles and corrected in-scope current endpoints.
- **BR-2 — Actual multi-provider discovery:** source owner's hidden-gap report, DEC-002. Every viable configured profile participates in common startup/periodic discovery; terminal skip/error states are visible internally. Adding a supported manifest does not require a new scheduler branch.
- **BR-3 — No silent paid/non-chat admission:** source VISION zero-cost value, primary-source catalog/plan distinctions. Discovery and inference admission are separate; uncertainty never silently becomes free. Cerebras excluded and Cloudflare deferred/unsupported per owner; retired GitHub skipped.
- **BR-4 — Snapshot consistency and availability:** source existing per-provider registry semantics and resilience goal. Failure isolation, atomic replacement, bounded staleness and cleanup preserve other providers and local listing responsiveness.
- **BR-5 — Correct bounded cross-provider cascade:** source DEC-003, ROADMAP P2. Exact identity mapping and raw-ID resolution preserve same-model-first ordering; provider diversity and explicit bounded attempts avoid starvation and misleading exhaustion claims.
- **BR-6 — Confidentiality and truthful delivery:** source DEC-003 and PROJECT-PROCESS. Credentials/inputs/provider bodies remain private; controlled and real external evidence are distinguished; missing prerequisites remain unverified.

## Expected architecture / stack

Existing FastAPI/Pydantic/httpx/YAML stack, no new packages. Shared orchestrator owns discovery lifecycle and per-provider status; catalog profiles normalize responses; registry owns admitted snapshots/freshness; router consumes only eligible snapshots; existing adapter performs inference. New generic discovery does not reuse the mutating OpenRouter worker as a per-provider special case. Keep its public interface/tests compatible through a wrapper if needed, with only one actual scheduler.

Profile MIXED means a new discovery subsystem in an existing application; BR-1 names preserved consumers. Concrete code layout within the named files may be refined without changing public contracts. Do not introduce a mandatory DevPlan or fixed agent cycle.

## Scope / boundaries

MAY EDIT — owner-approved v1.1.0 implementation boundaries:

- `backend/app/core/discovery/` — shared orchestration, parsers, status, compatibility wrapper.
- `backend/app/core/providers/models.py`, `registry.py`, `providers.yaml`, new `model_aliases.yaml` — additive declarative profiles, safe admission, exact aliases, per-provider atomic freshness metadata; update endpoints and explicit retired/excluded state.
- `backend/app/core/adapters/openai_client.py`, `backend/app/core/balancer/router.py` — related failure hygiene, canonical resolution, free/fresh filters, provider diversity, configurable budget.
- `backend/app/main.py`, `config.py`, `.env.example` — common lifecycle and documented non-secret configuration defaults; wire existing fixed cooldown setting.
- `backend/app/api/v1/models.py`, `chat.py` — memory-only eligible listing, safe ambiguity/budget/exhaustion envelopes and settings wiring, preserving other contracts.
- `backend/tests/` — new multi-provider discovery/routing/real-socket tests; retain existing scenarios. Existing expectation changes only for the explicit BR-1 exceptions.
- `scripts/probe_multi_provider.py` — reproducible safe provider discovery/activation probe, specified below.
- `notes/T-007-results.md`, `ARCHITECTURE.md`, `TASKS.md`, `HANDOFF.md` — delivered evidence, as-built changes and continuation.

DO NOT TOUCH: T-006 validation implementation/admin contracts, telemetry data schema/store behavior, accepted decisions, benchmark implementation, frontend, database/dependency files, real .env or keys. Shared schema changes must pass all accepted T-006 tests. No key persistence, account signups, paid plan change, external deployment, commit or push authorized by this draft.

Excluded/deferred: Cerebras and Cloudflare profile/parser/pagination (owner decisions); GitHub Models activation (retired); T-008 onboarding, P3 quality/context routing, P4 UI, P5 distribution; adaptive breaker/provider-auth recovery proposed as T-009, not silently removed from P2.

## Acceptance criteria

Criteria below define the approved verification contract. Delivered results, named conditional prerequisites and the Gemini owner-deferred live exception are traced in [T-007 results](../notes/T-007-results.md).

| AC | BR | Input / method / exact expected evidence |
|---|---|---|
| AC-1 | BR-1 | Full `.venv/bin/pytest backend/tests -q`; accepted T-006 candidate hashes/tests are the starting regression identity. Preserve scenarios; audit all changed/untracked paths against scope and enumerate BR-1 exception updates. |
| AC-2 | BR-2 | Fixture catalogs for every viable profile plus a newly added custom OpenAI manifest. Startup/periodic workers reach all configured eligible catalogs; no hardcoded OpenRouter dispatch, no duplicate poll, at most four concurrent requests, no overlapping cycles; disabled/missing/retired/excluded/unsupported profiles have explicit outcomes and zero calls; Cloudflare stays unsupported even with credentials and enabled=true. |
| AC-3 | BR-2, BR-4 | Valid/empty/malformed/partial catalogs, per-provider HTTP/auth/timeout/trickle/oversize errors and cancellation. Only complete valid results replace the targeted snapshot; failures leave other providers progressing. Freshness expires after twice the configured interval; disable/key removal removes eligibility immediately. Response/client/task cleanup verified. |
| AC-4 | BR-2, BR-3 | Profile fixtures tied to primary documentation or sanitized actual catalog response: OpenAI data profiles, literal ID/context mapping, dedup, invalid entries, zero-price, all_available, regex/manual behavior. Cloudflare and unknown format values return unsupported_profile with zero network requests, including manual configuration attempts to bypass the built-in deferral. No unsupported profile is called supported and no partial paginated list called complete. |
| AC-5 | BR-3 | Paid/unknown/non-chat/disabled/stale models cannot enter /v1/models, auto:free or explicit routing; configured cloud key alone permits discovery but not inference without policy+allowlist. T-006 validation never changes admission policy. Revoke confirmation/remove allowlist entry after cache population: next eligible read excludes the model before any successful refresh. |
| AC-6 | BR-5 | Exact same-model aliases across distinct provider IDs, negative similar-size/version/quantization cases, raw-ID request and ambiguous raw ID. Same model at another provider is Tier 1; unrelated alternatives wait; requested model masking preserved for JSON/SSE. |
| AC-7 | BR-5 | Provider A supplies many failing candidates, B can succeed; provider-diverse queue reaches B within budget. Default three-attempt test preserved; 1/10 limits accepted, 0/11 rejected; budget-stop vs true exhaustion distinguished; no duplicate candidate calls. |
| AC-8 | BR-1, BR-6 | Buffered/SSE with 429/5xx/connection/invalid-JSON failures, including error after role-only SSE chunk. Trace request ID spans providers, metadata safe, one downstream DONE for successful stream; sentinel prompt/key/upstream-body cannot leak via library logs, warnings or 503/500 envelopes. Reflected-secret raw IDs and aliases are excluded before listing/dispatch/telemetry, including after key changes. |
| AC-9 | BR-4, BR-6 | Real loopback app plus at least two distinct upstream servers on ephemeral ports: discovery populates registry, first server returns controlled 429, second succeeds for buffered/SSE; /v1/models still serves local snapshots and /health progresses during slow polling; shutdown stops fixture-owned resources. No mock/ASGI-only substitution. |
| AC-10 | BR-2, BR-6 | Real catalog probes for every in-scope cloud profile with configured prerequisites and local profile if runtime installed; required external minimum is OpenRouter, Groq and NVIDIA. Record every profile status/count/contract and limitation. For other in-scope profiles without prerequisites, record UNVERIFIED without claiming live delivery. Excluded/retired/unsupported outcomes are expected SKIPPED with zero calls; Cloudflare item identification is deferred, not an acceptance blocker for this scope. |
| AC-11 | BR-5, BR-6 | Required real local proxy completions (buffered/SSE) for Groq and NVIDIA in an isolated configured runtime per provider, plus cross-provider controlled socket failover. Save sanitized telemetry confirming actual upstream provider. Owner explicitly deferred Gemini external live generation until its key is available; record it as owner-deferred/UNVERIFIED and preserve all Gemini implementation, discovery-profile and local routing tests. Groq/NVIDIA missing free-tier account/key/policy/model blocks their live criterion; willingness to supply keys is not evidence that they are configured. Natural live 429 is not required. T-007 may be reviewed with the named Gemini exception; P2 must remain open. |
| AC-12 | BR-1, BR-4 | Populate admitted snapshots, warm normal application configuration, then instrument outbound HTTP and filesystem reads to fail during GET /v1/models. Listing and admission-revocation cases must still succeed using in-memory state only. Record repeated-request timing (median/p95, fixture size, environment) separately from the zero-I/O assertions; timing observations do not substitute for the no-network/no-file checks. No synchronous provider validation or config-file reload may be introduced into eligible-snapshot reads. |

## Delivery / real probes

Required future commands (not implemented by spec preparation):

```bash
.venv/bin/pytest backend/tests -q
.venv/bin/python scripts/probe_multi_provider.py --provider-id groq --mode catalog
.venv/bin/python scripts/probe_multi_provider.py --provider-id groq --mode proxy
```

Use the same probe for other viable provider IDs. Catalog mode invokes the actual shared discovery service using existing local credentials, does no inference and prints only safe outcome/count/latency. Proxy mode starts a probe-owned real loopback app using an isolated registry containing only the selected registered provider and its explicit local free-access policy; its normal shared lifespan discovers models, then actual HTTP model listing and buffered/SSE requests verify routing. Isolation must use ordinary constructor/configuration injection, never a fake response transport or replacement routing algorithm. Probe closes only its own server/client; no user server is terminated and no live config files are rewritten. Missing credentials, consented free-account policy or an eligible model prints a fixed safe prerequisite code and exits nonzero. Excluded/retired/unsupported profiles produce a fixed SKIPPED result without requests. Cloudflare mode always skips; Gemini proxy mode with no key records the owner-deferred live check as UNVERIFIED and exits nonzero, never as a mock pass.

Output excludes keys, raw IDs, bodies, generated text, account IDs and arbitrary exception messages. Record commands, revision/working-tree identity, exit status, per-profile outcome and sanitized metadata in notes/T-007-results.md. Controlled loopback failover and actual external completion are separate evidence. No runtime flags may be left unnamed: report every free_access_confirmed/allowlist gate's effective state for each tested environment and what enables it.

## Risks / open evidence / deviations

- Cloudflare native item-ID mapping remains unverified, but owner explicitly deferred the entire profile/parser/pagination as unsupported_profile with zero I/O. Resolving it is a future scope, not a blocker to final approval of this version. NVIDIA hosted catalog envelope was directly observed; credentialed inference still needs required live evidence.
- At recon only OpenRouter was configured. Owner subsequently stated that Groq and NVIDIA keys can be supplied; their presence and free-access policy were subsequently confirmed for implementation/live probes; no values are recorded. Use GROQ_API_KEY and NVIDIA_API_KEY in local .env for the required live probes. This document does not authorize writing secrets or creating/upgrading accounts. Gemini live generation is explicitly owner-deferred; its software/local tests remain required. Other missing-prerequisite catalog probes stay conditional/UNVERIFIED as specified in AC-10.
- Discovery of all models is broader than admission to a zero-cost chat pool. Owner-agreed operator-confirmed account policy and explicit allowlists trade automatic admission for reliable cost boundaries. They do not prove provider billing state; account changes must be reflected in local policy.
- Aliases/allowlists are versioned configuration, never hardcoded availability. Newly discovered but unconfirmed models remain catalog observations; they do not silently gain inference eligibility.
- Requiring complete pagination may reveal further profile-specific work. Add a measured bounded pagination contract before approving an affected profile; do not hide incomplete catalogs.
- Existing raw-body leakage and missing free guards are included for repair because broad runtime activation exposes those paths. No runtime fixes made during spec preparation.
- Fixed cooldown is not the promised adaptive breaker. Proposed T-009 remains a P2 obligation awaiting separate scope approval.
- Approved scope exceptions and deferred evidence: Cloudflare deferred as unsupported_profile (zero requests); Cerebras excluded; Gemini external live generation deferred until a key is available, UNVERIFIED, P2 remains open. These are named owner decisions, not successful checks. Six design choices and expanded MAY EDIT accepted; owner approved v1.1.0 implementation. Delivered results and the named conditional live limitations are recorded in [T-007 results](../notes/T-007-results.md). No additional scope deviation.

$END_BODY
$START_LINKS
IMPLEMENTS: [DEC-002](../docs/decisions/DEC-002-declarative-provider-schema.md), declarative providers/discovery; [DEC-003](../docs/decisions/DEC-003-canonical-model-mapping-and-harness-interop.md), Decision sections 1–5 (credential boundary, same-model failover, model catalog, masking, pre-buffering).
IMPACTS: [TASKS](../TASKS.md), T-007; [ARCHITECTURE](../ARCHITECTURE.md), discovery and cascade components.
REQUIRES: [Input RECON](../docs/recon/T-007-multi-provider-discovery.md); [accepted T-006 evidence](../notes/T-006-validation-results.md).
$END_LINKS
$END_ARTIFACT_GOAL_MULTI_PROVIDER_DISCOVERY
$END_SECTION_FEATURE
$END_DOCUMENT

<!-- Execution record: Owner approved v1.1.0, supplied Groq/NVIDIA keys locally and explicitly confirmed free access for both on 2026-10-22. No key values recorded. -->
