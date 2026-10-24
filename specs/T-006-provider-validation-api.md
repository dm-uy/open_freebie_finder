# SPEC-T-006 — Provider Validation Admin API

- Profile: MIXED. Version: 1.0.1. Status: approved. Implementation approval: owner-approved in chat on 2026-10-22.
- Roadmap: P2; task: [T-006 / B-002](../TASKS.md).
- Input RECON: [2026-10-22 baseline](../docs/recon/T-006-provider-validation.md), HEAD `6d49e2a174a111dc0a5bb8745530a97d0e9786da`.
- Preparation authorized by the owner's chat message on 2026-10-22 following confirmed T-005 fixes. Owner explicitly approved version 1.0.1 and authorized implementation under the lightweight process in chat on 2026-10-22.
- Implementation: COMPLETE, owner-accepted in chat on 2026-10-22. AC verification: see notes/T-006-validation-results.md. Result acceptance: owner accepted in chat on 2026-10-22.
- Review: owner-supplied review on 2026-10-22 recommends approval; no substantive gaps reported. Version 1.0.1 addresses non-blocking profile, decision-link and scripts-path comments; no BR/AC or runtime behavior change. This recommendation is not implementation approval.

$START_DOCUMENT
PURPOSE: Let an operator test provider credentials and OpenAI-compatible endpoints before enabling routing.
SCOPE: One non-mutating admin validation operation, isolated credentials, discovery filtering, one micro-completion and safe diagnostics.
KEYWORDS: provider, validation, admin, credentials, OpenAI, diagnostics, P2
$START_DOCUMENT_PLAN
$DOCUMENT_PLAN
GOAL Validate provider configuration without altering live routing => GOAL_PROVIDER_VALIDATION
$END_DOCUMENT_PLAN
$START_SECTION_FEATURE
$START_ARTIFACT_GOAL_PROVIDER_VALIDATION
TYPE: GOAL
KEYWORDS: manifest, model catalog, completion, validation report
$START_CONTRACT
PURPOSE: Diagnose a provider using the same declarative vocabulary as the registry.
DESCRIPTION: An authorized operator submits a registered provider ID or inline manifest and receives ordered configuration, catalog and completion checks without saving keys or activating models.
RATIONALE: T-007 activation and the future dashboard/onboarding flow need a predictable validation primitive independent of live routing state.
ACCEPTANCE_CRITERIA: AC-1 through AC-12 below.
$END_CONTRACT
$START_BODY

## Done when / Stop and ask when

Done when all ACs have evidence tied to the implemented revision, including the real local socket probe and a real configured provider probe, or an explicit owner decision on an unavailable external prerequisite. An unexecuted external probe remains UNVERIFIED; it cannot be reported as passed.

Stop dependent work for changes to manifest compatibility, global routing/adapter behavior, dependencies, credential persistence, provider activation, public deployment, or edits outside MAY EDIT. Ordinary implementation choices inside this contract need no separate decision. Do not begin implementation until this scope is approved.

## Context and scope

Sources: VISION's zero-setup resilient proxy goal; ROADMAP P2; TASKS T-006; DEC-001/002/003; Input RECON above. The current API exposes telemetry but no provider validation route. Registry discovery mutates live state, and the existing completion client reads process credentials. This feature must perform isolated direct HTTP validation rather than route through CascadeRouter or the mutating discovery service.

Profile criterion: use MIXED when a new isolated subsystem is introduced into an existing application and existing consumer contracts must be preserved; use BROWNFIELD when primarily modifying existing behavior, and GREENFIELD for a first implementation without existing behavior to preserve. Here the validation service, schemas and endpoint are new; admin aggregation and all existing proxy/telemetry contracts are the preserved portion. BR-1 remains the explicit regression contract. This follows PROJECT-PROCESS and the earlier T-003/T-005 profile convention without changing their records.

Included: existing and custom OpenAI-compatible providers, all existing discovery rule types, configured or request-scoped credentials, bounded diagnostics and tests.

Excluded: activation, registry writes, key persistence, UI, provider-specific non-OpenAI transports, new provider manifests, cross-provider cascades, adaptive circuit breaker, benchmark ranking and onboarding LLM. T-007 owns live activation; T-008 owns onboarding. These remain deferred until separate specs.

## API contract

`POST /api/admin/providers/validate`, JSON body, exactly one of:

```json
{"provider_id": "openrouter"}
```

```json
{"manifest": {"id": "example", "name": "Example", "base_url": "http://127.0.0.1:11434/v1", "models_endpoint": "http://127.0.0.1:11434/v1/models", "auth": {"type": "none"}, "discovery": {"type": "all_available"}}, "model_id": "example-model"}
```

Optional fields: `api_key` (nonempty secret string, maximum 8192 characters), `model_id` (nonempty raw model ID, maximum 512 characters). Reject unknown top-level fields. Reject empty selector strings, both/neither selectors and wrong field types with HTTP 422. Preserve existing ProviderManifest ID normalization and fields/defaults for an inline manifest; do not change its global validation policy. Unknown registered provider ID returns HTTP 404 in the existing OpenAI error-envelope style.

Master-key behavior matches existing admin telemetry: configured master key requires exact Bearer authentication; absent/incorrect key returns the existing HTTP 401 envelope. No master key means permissive development access. Authenticate before provider lookup, credential resolution or network work; even a malformed unauthenticated body must not expose input values. Body validation errors must use redacted details without submitted input, body, key or authorization header.

Disabled registered providers may be tested; validation never enables them. Request completion is synchronous from the operator's perspective, but HTTP work must be asynchronous.

### Configuration and credentials

- A supplied `api_key` overrides configured provider credentials for this request only. Never change os.environ, Settings, singleton state or a manifest to carry it. Concurrent validations must not share keys.
- Registered ID: without an override, resolve only that registered manifest's `auth.api_key_env`, environment first then the corresponding Settings field, matching existing behavior.
- Inline manifest: use only the supplied key. Never resolve its `api_key_env`, even when its ID matches a registered provider. This prevents a submitted destination from acquiring a saved key.
- `none` auth sends no credentials; supplying `api_key` with `none` is a configuration failure. Bearer/header auth without a key is `missing_credentials`; header auth requires a valid HTTP header token name. Reject CR/LF in credential values and header names. A custom header cannot override Host, Content-Length, Content-Type, Accept, Connection or Transfer-Encoding (case-insensitive).
- Before I/O, parse URLs as absolute HTTP(S) URLs with a host, valid port, no userinfo, query, fragment or unresolved `{...}` template. Local HTTP endpoints remain supported. For credentialed requests, base_url and models_endpoint must share scheme, host and effective port. Do not follow redirects or use ambient proxy settings/credentials.
- Relative models_endpoint remains unsupported in this version, consistent with the actual shared schema. Do not silently resolve Cloudflare account templates submitted inline; the caller supplies resolved URLs.
- Validate discovery configuration in the configuration stage before any network request: regex requires a nonempty expression of at most 256 characters that compiles under Python `re`; manual requires a nonempty list of nonempty string IDs, each at most 512 characters. Fail these checks with `invalid_configuration`. Catalog then only retrieves and filters an already validated rule.

### Ordered validation

Return checks in this exact order: `configuration`, `catalog`, `completion`. Each has `status` = `passed` / `failed` / `skipped`, `code` (stable code below or null), `http_status` (upstream integer or null), `duration_ms` (nonnegative monotonic duration), and `message` (fixed safe explanatory text). After a failure, later stages are skipped with `code: "previous_check_failed"`; no further I/O occurs.

1. **Configuration:** resolve inputs, auth and URL rules. Codes: `missing_credentials`, `invalid_configuration`. Valid but unsupported configuration produces a failed check, not an exception.
2. **Catalog:** except manual discovery, GET models_endpoint once with the chosen auth. HTTP 200 must decode to an object containing a `data` list. Each retained item must be an object with a nonempty string of at most 512 characters at the literal `model_id_field` key (no JSONPath execution). Apply this ID bound to every discovery type. Skip malformed entries and IDs containing the request's supplied/resolved provider key or configured master key as a substring; deduplicate IDs and sort lexicographically. Apply the same secret exclusion to manual IDs. Missing/wrong `data`, invalid JSON or a nonobject response is `invalid_catalog`; a valid catalog with no eligible IDs is `no_eligible_models`.
   - `all_available`: retain every valid ID; this asserts reachability, not zero pricing.
   - `openrouter_free`: retain only items where pricing is an object and both prompt/completion string representations match `0`, `0.0` or `0.00` after stripping whitespace, matching current discovery semantics. Missing prices never count as zero.
   - `regex`: require a nonempty filter_expression which compiles under Python `re`; retain IDs where `re.search` matches. Treat expressions as configuration, never code. Reject expressions longer than 256 characters and IDs longer than 512 before matching. No owner-independent claim of protection against all expensive regexes is made; see risks.
   - `manual`: require nonempty valid static_models (same ID bounds), deduplicate/sort them without a GET. Catalog reports passed, `code: "manual_catalog"`, `http_status: null`; this explicitly does not claim remote listing connectivity.
   - If model_id is provided, it must belong to the eligible set, else `model_not_eligible`, with no completion request. Otherwise choose the lexicographically first eligible ID. Do not choose by benchmarks or cached routing state.
3. **Completion:** POST once to base_url with trailing slashes removed plus `/chat/completions`, unless already ending in `/chat/completions`. Body: selected raw model ID, `messages: [{"role":"user","content":"Reply OK."}]`, `stream: false`, `max_tokens: 16`. No retries, fallbacks or operator-controlled prompts/tools. A response passes only for HTTP 200 with a JSON object, no top-level error, and nonempty choices list whose first item has a message object with role assistant and a content field of string or null. Null content is allowed for a constrained reasoning response; passing proves protocol reachability, not answer quality. Other shapes are `invalid_completion`. Never synthesize missing fields to make a probe pass.

Use a total wall-clock deadline of 20 seconds covering both network stages; enforce it even for a trickling response. Each HTTP stage timeout is at most 10 seconds and at most remaining deadline. A deadline/HTTP timeout gives `timeout` at the active stage. Limit each decoded response body to 1 MiB, checking incrementally before JSON parsing; oversize is `response_too_large`. Network/connect errors give `connection_error`. Non-200 responses map 401/403 to `upstream_auth_error`, 429 to `rate_limited`, 5xx to `upstream_unavailable`, and other statuses including 3xx to `upstream_http_error`. Always close response/client resources on success, error, timeout and cancellation.

### Diagnostic response

For a syntactically valid known request, return HTTP 200 for either a successful or failed validation report:

```json
{
  "provider_id": "example",
  "valid": true,
  "model_id": "example-model",
  "eligible_model_count": 1,
  "model_ids": ["example-model"],
  "checks": [
    {"name":"configuration","status":"passed","code":null,"http_status":null,"duration_ms":0.1,"message":"Configuration accepted."},
    {"name":"catalog","status":"passed","code":null,"http_status":200,"duration_ms":2.0,"message":"Eligible models found."},
    {"name":"completion","status":"passed","code":null,"http_status":200,"duration_ms":4.0,"message":"Completion protocol verified."}
  ],
  "total_duration_ms": 6.1
}
```

`valid` is true only if every check passed. `model_id` is null until a candidate is selected. eligible_model_count is the full deduplicated eligible count; model_ids is its sorted first 100 IDs, empty if catalog did not pass. No manifest echo, URLs, keys, auth headers, raw upstream body, prompt, completion text, exception text or traceback in reports/logs. Messages come from a fixed safe vocabulary per code. If provider_id itself contains a nonempty supplied/resolved provider key or configured master key, replace those substrings with `[REDACTED]` in the report; never log the raw identifier. Submitted descriptions, catalog metadata and provider responses are untrusted data, never instructions; they cannot alter destinations, auth or the fixed prompt. Validation never writes chat telemetry or affects its counters.

## Business requirements

- **BR-1 — Preserve existing contracts.** Source: VISION compatibility, T-005 acceptance, PROJECT-PROCESS. Existing health, models, chat buffered/SSE, telemetry and shared manifest semantics remain compatible; preserve all baseline test scenarios. Only add the validation endpoint and scoped new types/service.
- **BR-2 — Operator validation.** Source: TASKS T-006, DEC-002. Accept one registered ID or inline manifest; validate configuration, eligible catalog and one micro-completion; return deterministic structured stage diagnostics including failures.
- **BR-3 — Credential isolation and admin access.** Source: DEC-003 credential boundary, existing admin policy. Apply master-key protection, request-local overrides, no saved-key resolution for inline manifests, safe transport/auth handling and secret-free errors.
- **BR-4 — No runtime mutation.** Source: T-006 pre-activation purpose; T-007 activation boundary. Do not save keys, register models, change cooldowns/enablement, alter registry/settings/environment or write completion telemetry, regardless of outcome or concurrency.
- **BR-5 — Bounded resource usage.** Source: VISION lightweight async service; proposed detail for this version. Bound network count, deadline, response size and returned model list, preserve event-loop progress during network waits, and close resources.
- **BR-6 — Demonstrable delivery.** Source: PROJECT-PROCESS real-path checks. Exercise the route over actual HTTP sockets and record external provider evidence separately from mock evidence; no claim of provider-wide compatibility or zero cost from one probe.

## Boundaries / stack / expected architecture

Always preserve private credentials, explicit stage outcomes and the existing app contracts. Ask first for scope expansion or changed acceptance criteria. Never log raw inputs/responses, modify persistent settings, commit keys, push or deploy as part of this task.

Existing Python/FastAPI/Pydantic/httpx stack; no dependency or version changes. New request/report types and isolated validation service under core/providers; new admin router mounted through api/admin/__init__.py. Reuse compatible auth behavior without coupling validation to telemetry internals. Code details are the implementer's choice. The existing OpenAIProviderClient and OpenRouterDiscoveryService are observations, not required reuse targets; do not modify them for this feature.

### MAY EDIT after approval

- `backend/app/api/admin/providers.py` — new endpoint, safe request validation and admin auth.
- `backend/app/api/admin/__init__.py` — mount provider router.
- `backend/app/core/providers/validation.py`, `backend/app/core/providers/validation_models.py` — new isolated service and schemas.
- `backend/tests/test_provider_validation.py`, `backend/tests/test_provider_validation_live.py` — new behavioral and real-socket checks with isolated fixtures; existing tests remain untouched.
- `scripts/probe_provider_validation.py` — reproducible external-provider socket probe; reads locally configured credentials, never prints or writes them.
- `notes/T-006-validation-results.md` — implementation verification, AC evidence and deviations.
- `ARCHITECTURE.md` — describe only the implemented validation component and its non-mutating boundary; retain proposal status for future components.
- `TASKS.md`, `HANDOFF.md` — task status and continuation, maintained by the session's record owner.

### DO NOT TOUCH

Shared `models.py`, `registry.py`, providers.yaml, existing adapter/router/discovery/telemetry modules, main.py, config.py, requirements, .env files, frontend, ROADMAP scope and accepted decisions. These are existing contracts or unrelated future phases. Probe tooling may read a configured key through existing Settings without modifying its source.

## Acceptance criteria and traceability

Contractual expectations follow; execution results and candidate identity are recorded in [T-006 results](../notes/T-006-validation-results.md).

| AC | BR | Scenario and expected evidence |
|---|---|---|
| AC-1 | BR-1 | Run `.venv/bin/pytest backend/tests -q`; preserve the baseline scenarios from recon and pass new tests. Review all changed paths and shared contracts against MAY EDIT/DO NOT TOUCH. |
| AC-2 | BR-2 | Registered ID and inline manifest each succeed against controlled upstreams; disabled registered provider may validate without activation. Both/neither selectors, unknown fields, bad types give redacted 422; unknown provider gives 404. |
| AC-3 | BR-3 | Configured master key: absent/wrong gives 401, correct permits work; unset permits work. Malformed unauthorized bodies leak no submitted values. Assert no outbound requests, provider lookup or credential resolution on unauthorized calls. |
| AC-4 | BR-2 | Table-driven catalog tests cover all_available, strict zero-price filtering (including missing/paid/malformed prices), regex valid/invalid/empty, manual no-GET, custom literal ID key, duplicates, malformed entries/JSON/shape, empty eligible set and explicit model mismatch. Assert stable order/count/selection and skipped completion. |
| AC-5 | BR-2 | Upstream request spy verifies exactly one fixed micro-completion, correct URL/raw ID/auth/body and no retries. Valid string/null-content shapes pass; missing message/content, wrong role/type, empty choices, top-level error and invalid JSON fail as specified. |
| AC-6 | BR-2, BR-5 | Stage matrix covers 401/403/429/5xx/3xx/other HTTP errors, connection errors, per-stage timeout, total-deadline trickle and oversize bodies; verify fixed codes, stage statuses, upstream status, bounded request count and closure on cancellation. |
| AC-7 | BR-3, BR-4 | Concurrent overrides carry distinct keys; saved-key fallback works only for registered IDs; inline api_key_env cannot read environment secrets. Snapshot settings/environment/registry/cooldowns/telemetry and local config bytes before/after successful and failed validation: unchanged. |
| AC-8 | BR-3 | Invalid URL/userinfo/query/fragment/template, credentialed cross-origin catalog, header injection and reserved headers fail before I/O. Local HTTP succeeds. Redirect target receives no request; ambient proxy configuration does not redirect probe traffic. |
| AC-9 | BR-3 | Sentinel secrets in request keys, invalid fields, URL, auth header, upstream body and exception text never appear in captured reports/logs, including 401/404/422 and transport failures. Include keys reflected in model IDs and provider_id: secret-bearing model IDs are excluded; provider_id is redacted. Hostile descriptions/provider text cannot change fixed prompt, destinations or credentials. |
| AC-10 | BR-2, BR-5 | More than 100 eligible IDs returns first 100 sorted with full count; duplicates removed. Delayed upstream allows a concurrent health request to complete before validation ends. Response/report times nonnegative. |
| AC-11 | BR-6 | Run `.venv/bin/pytest backend/tests/test_provider_validation_live.py -q`: start actual loopback upstream and app HTTP servers using ephemeral ports, exercise success and upstream 429 via real sockets; verify report and no mutation. This is transport delivery evidence, not external-provider evidence. |
| AC-12 | BR-6 | Run external probe command below against a real locally running app and registered OpenRouter configuration; record revision, command, sanitized stage/status/count/durations and outcome. Passing requires valid=true with catalog and completion passed against the actual provider. Missing credentials/network/quota are recorded as UNVERIFIED or failed evidence with reason, never converted to a mock pass. |

## Delivery / Live probe

Local deterministic probe AC-11 requires no external credentials or network beyond loopback. Fixture-owned servers and temp files must be stopped/removed by their owning test even on failure; no user processes are terminated. Disable background external discovery only in the fixture-owned app instance, without modifying production lifespan.

External AC-12 prerequisites: approved implementation, real local app started with `.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`, locally configured OPENROUTER_API_KEY and optional PROXY_MASTER_KEY. Resolve current catalog dynamically, never embed a historical model ID.

Required command (implemented; final probe evidence is linked above):

```bash
.venv/bin/python scripts/probe_provider_validation.py --base-url http://127.0.0.1:8000 --provider-id openrouter
```

The probe reads master key via existing local Settings, authenticates to the local app, sends only provider_id, then prints a sanitized report summary and exits 0 only for a valid report. Nonzero for transport, HTTP or report failure. It must not print keys, request/response bodies or generated text. Save sanitized evidence in notes/T-006-validation-results.md, including the command, revision, environment, actual outcome and limitations. No external hosting, remote deployment, commit or push authorized.

## Risks, deficiencies and deviations

- External provider formats/token parameters may differ; report incompatibility honestly. Broad adapters and provider activation belong to T-007.
- A micro-completion may consume quota and, for a misconfigured provider, money. Validation reports reachability, not proof of free pricing; use a configured free-tier key and the zero-price OpenRouter filter for the required external probe.
- Local endpoint support is intentional. This API is an operator capability; configure the existing master key before exposing the app beyond a trusted local environment. Network allowlists and full DNS-based SSRF protection are outside this slice. Inline manifests cannot obtain process credentials, and redirects are disabled.
- Python regex has no native hard matching deadline. Length bounds alone do not eliminate pathological expressions; patterns are trusted operator configuration under the same boundary as endpoint selection. A sandboxed regex engine requires a separate approved dependency/design if untrusted onboarding needs it.
- Secret-substring exclusion may discard a legitimate model ID that happens to contain a short configured key. This deliberately favors credential privacy over catalog completeness; it does not prove the excluded model is invalid.
- The shared schema's relative-endpoint description conflicts with its actual absolute-only behavior; preserve implementation and document the constraint, rather than expanding shared compatibility incidentally.
- No benchmark, context-window suitability, SSE quality or long-term quota claim follows from validation. No new LLM agent or tools execute provider text; the only LLM call uses the fixed micro-prompt and a protocol check.
- Implementation approval recorded above; external probe passed for the recorded candidate. Result accepted by owner in chat on 2026-10-22. Implementation deviations: none.

$END_BODY
$START_LINKS
IMPLEMENTS: [DEC-002](../docs/decisions/DEC-002-declarative-provider-schema.md), Decision item 4 (Validation Endpoint); [DEC-003](../docs/decisions/DEC-003-canonical-model-mapping-and-harness-interop.md), Decision section 1 (Centralized Credential Encapsulation). These are document/section references; neither decision defines protocol artifact IDs.
IMPACTS: (none)
REQUIRES: [Input RECON](../docs/recon/T-006-provider-validation.md) (baseline and observations); [TASKS.md](../TASKS.md), T-006 (authorization and dependencies).
$END_LINKS
$END_ARTIFACT_GOAL_PROVIDER_VALIDATION
$END_SECTION_FEATURE
$END_DOCUMENT
