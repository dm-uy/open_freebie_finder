# SPEC-T-004 — OpenAI Proxy Endpoints and Cascade Failover Router

- **Record:** `specs/T-004-openai-proxy-and-failover.md`
- **Profile:** MIXED (Adding OpenAI-compatible proxy endpoints, two-tier failover engine, and streaming safe-router to existing FastAPI app)
- **Version:** 1.1.0
- **Status:** done
- **Approval:** approved (Approved by owner on 2026-10-22)
- **Roadmap:** Phase P1 "Core OpenAI Proxy, Declarative Provider Registry, and OpenRouter Integration"
- **Task:** `TASKS.md` -> T-004 "OpenAI Proxy Endpoints and Cascade Failover Router"
- **Input RECON:** Embedded section below (Commit: `2ee5666`, Date: 2026-10-22)
- **Implementation Status:** VERIFIED / 24 TESTS PASSED / ALL PROBES CONFIRMED
- **Governance:** [PROJECT-PROCESS.md](../PROJECT-PROCESS.md), [AGENTS.md](AGENTS.md)

$START_DOCUMENT
PURPOSE: Expose standard OpenAI endpoints (/v1/chat/completions and /v1/models) enabling external developer tools and harnesses (DeepSeek Harness, Cursor, LangChain) to execute zero-cost inference with transparent two-tier cascade failover upon rate limits (429/5xx).
SCOPE: Proxy routing endpoints, request/response models, two-tier failover engine, candidate queue selection, canonical model masking, first-token stream pre-buffering, OpenAI error envelopes, and automated tests.
KEYWORDS: openai proxy, chat completions, models endpoint, cascade failover, two-tier failover, streaming pre-buffer, model masking, deepseek harness

$START_DOCUMENT_PLAN
$DOCUMENT_PLAN
SECTION_FEATURE:
GOAL OpenAI Proxy Endpoints and Two-Tier Cascade Failover => GOAL_PROXY_FAILOVER
SECTION_SCENARIOS:
USE_CASE Fetch Models from DeepSeek Harness => CASE_HARNESS_FETCH_MODELS
USE_CASE Execute Transparent Failover on 429 Rate Limit => CASE_TRANSPARENT_FAILOVER
USE_CASE Stream Tokens with First-Token Pre-buffering => CASE_STREAM_PREBUFFER
$END_DOCUMENT_PLAN

$START_SECTION_FEATURE
$START_ARTIFACT_GOAL_PROXY_FAILOVER
TYPE: GOAL
KEYWORDS: proxy, failover, streaming, circuit breaker, openai spec

$START_CONTRACT
PURPOSE: Provide a 100% OpenAI-compatible drop-in proxy service that automatically routes incoming completions to active free-tier models and executes seamless failover when upstream providers return 429 or 5xx.
DESCRIPTION: Implement `GET /v1/models` (servicing cached models in-memory without network I/O) and `POST /v1/chat/completions` (supporting standard JSON and SSE streams). Implement Two-Tier Failover: Tier 1 tries the exact same model across active providers; Tier 2 falls back to alternative free models up to 3 attempts. Pre-buffer streaming SSE to catch early 429/5xx errors before flushing headers, synthesize usage blocks when missing, and mask response model IDs with the requested canonical name.
RATIONALE: External harnesses require high stability; upstream free models frequently hit rate limits. Transparent retry and canonical name masking protect client applications from disruption.
ACCEPTANCE_CRITERIA: AC-1 through AC-11 covering endpoint contracts, permissive auth, two-tier failover, streaming pre-buffering, model masking, circuit breaker cooldowns, error shapes, and regression safety.
$END_CONTRACT

$START_BODY
## Done when

- AC-1 through AC-11 pass on verified code.
- `GET /v1/models` returns standard OpenAI model list containing `auto:free` and discovered canonical models, resolving entirely in-memory from registry cache without outbound network calls.
- `POST /v1/chat/completions` accepts standard OpenAI payloads (buffered and SSE streaming) using permissive auth (works with arbitrary or empty client API keys, validating against `Settings.proxy_master_key` only if configured).
- Simulated 429 or 5xx on primary candidate triggers transparent failover to secondary candidate, returning 200 OK to the client with canonical model name preserved.
- Streaming requests (`stream: true`) pre-buffer the first chunk: if an upstream error occurs before the first content token, failover executes seamlessly before streaming headers/bytes are committed to the client.
- All errors (400, 401, 404, 503) conform strictly to standard OpenAI JSON error shape `{"error": {"message": ..., "type": ..., "code": ...}}`.
- Regression test suite (`pytest backend/tests`) passes 100% green (all 12 existing tests + new proxy tests).

## Stop and ask when

- Implementation requires altering the agreed technology stack (Python 3.11+, FastAPI, Pydantic v2, httpx).
- Modifying previously approved provider schema or OpenRouter discovery logic.
- Adding third-party proxy gateway wrappers (e.g. LiteLLM) rather than lightweight native FastAPI router.

## Context / Input RECON

**Baseline Snapshot:** Git commit `2ee5666` (Date: 2026-10-22, working tree clean).

| Area | Verified Baseline State | Evidence Source |
|---|---|---|
| Request | OpenAI proxy (`/v1/chat/completions`, `/v1/models`), Two-Tier Failover, DeepSeek Harness interop, SSE pre-buffering, model masking | User requests; DEC-001, DEC-002, DEC-003; DeepSeek Harness screenshot |
| Registry | `ProviderRegistry` loaded with 10 manifests from `providers.yaml`; in-memory cache supporting `register_models()`, `get_models()`, `get_model_candidates(canonical)` | `backend/app/core/providers/` |
| Discovery | `OpenRouterDiscoveryService` discovers live free models, verified in live probe (20 models) | `backend/app/core/discovery/` |
| Runtime | Python 3.15.0 in `.venv`, FastAPI 0.159.1, Pydantic 2.14.1, httpx 0.28.1 | Verified installed in `.venv` |
| Existing Tests | 12 tests in `backend/tests/` (100% passing in 0.07s) | `pytest backend/tests` execution |

## What we add / build

1. **`backend/app/api/v1/models.py`:**
   - OpenAI-compatible `GET /v1/models` endpoint:
     - Returns JSON `{ "object": "list", "data": [ ... ] }`.
     - Synthesizes `auto:free` model (id: `auto:free`, object: `model`, owned_by: `open-freebie-finder`).
     - Gathers discovered models from `ProviderRegistry.get_models()`, deduping by `canonical_name`.
     - Returns immediately directly from in-memory cache without outbound network calls or disk I/O.
2. **`backend/app/api/v1/chat.py`:**
   - OpenAI-compatible `POST /v1/chat/completions` endpoint:
     - Request models: `ChatCompletionRequest` (messages, model, stream, temperature, max_tokens, etc.).
     - Permissive authentication: accepts any `Authorization: Bearer <token>` or missing header. If `Settings.proxy_master_key` is set, validates client token and returns 401 on mismatch.
     - Dispatches request through `CascadeRouter`.
     - Supports buffered response (`ChatCompletionResponse`) and Streaming SSE (`text/event-stream`).
     - Formats all error responses in OpenAI error envelope: `{"error": {"message": str, "type": str, "code": int}}`.
3. **`backend/app/core/balancer/router.py`:**
   - `CascadeRouter` class:
     - Circuit breaker tracking: maintains dictionary of `(provider_id, model_id) -> cooldown_until_timestamp`. Default cooldown: 60 seconds upon 429/5xx.
     - Candidate Resolution Order:
       - Filtering: Candidates are selected exclusively from active providers (`manifest.is_enabled == True` and (`auth.type == "none"` or provider API key is present in settings/env)).
       - **If `model == "auto:free"`:** Gathers all discovered models from active providers, sorted deterministically in Phase P1 by alphabetical order of `(provider_id, canonical_name)` (explicitly noted that Phase P3 will replace this with benchmark-driven scoring).
       - **If specific model requested (e.g. `meta-llama/llama-3.3-70b-instruct`):**
         - **Tier 1 (Same Model):** Finds all active provider instances hosting that exact canonical name (`registry.get_model_candidates(model)`).
         - **Tier 2 (Alternative Model Fallback):** If all Tier 1 candidates fail or are in cooldown, gathers alternative active free models sorted alphabetically.
     - Execution loop:
       - Maximum failover attempts capped at `MAX_FAILOVER_ATTEMPTS = 3`.
       - Per-candidate HTTP request timeout: 15.0 seconds.
       - Tries candidates sequentially. On 429/5xx or timeout, records cooldown and advances to the next candidate.
       - If all candidates are exhausted or fail, raises HTTP 503 with OpenAI error payload (`"All free pool candidates exhausted"`).
4. **`backend/app/core/adapters/openai_client.py`:**
   - `OpenAIProviderClient` class:
     - Formats outbound payload: maps client's canonical model name to provider's raw `id`.
     - Injects provider credentials: `Authorization: Bearer <key>` (or custom header per manifest).
     - Non-streaming execution:
       - Sends POST to provider's completions endpoint.
       - If response lacks `usage`, synthesizes default `usage: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}`.
       - Masks `model` in response JSON with client's originally requested canonical model name.
     - Streaming execution:
       - Connects via `httpx.AsyncClient.stream`.
       - Pre-buffers chunks until the first valid content delta (`choices[0].delta.content`) or error.
       - If HTTP status != 200 (e.g. 429/5xx) or in-stream JSON error occurs prior to the first content delta, raises `UpstreamRateLimitError` or `UpstreamProviderError` before sending any bytes downstream, allowing router to cascade.
       - Once first content chunk is verified, flushes `text/event-stream` headers to client and streams subsequent chunks, rewriting `model` field to requested canonical name.
5. **App Wiring (`backend/app/main.py`):**
   - Mounts `/v1` router with prefixes `/v1/chat/completions` and `/v1/models`.
6. **Config (`backend/app/config.py`, `.env.example`):**
   - Adds optional `proxy_master_key: Optional[str] = None` setting.
7. **Tests (`backend/tests/test_openai_proxy.py`, `backend/tests/test_cascade_failover.py`):**
   - Unit and integration tests covering buffered completion, streaming SSE, two-tier failover, in-stream 429 failover, error shapes, and model name masking.

## Stack / Dependencies

- **Profile:** MIXED (Extending existing backend without adding external dependencies).
- **Existing Stack:** Python 3.15.0, FastAPI 0.159.1, Pydantic 2.14.1, PyYAML 6.0.3, httpx 0.28.1, aiosqlite 0.22.1, pytest 9.1.1, pytest-asyncio 1.4.0.
- **Proposed Changes:** No changes to dependencies.

## Business Requirements

- **BR-1 — Regression Safety (DEC-001):** Existing `/health` endpoint and 12 existing tests must remain 100% passing.
- **BR-2 — OpenAI API Compatibility (DEC-001):** Endpoints `/v1/chat/completions` and `/v1/models` must strictly adhere to the OpenAI REST specification.
- **BR-3 — DeepSeek Harness Interoperability (DEC-003):** External harnesses must be able to query `/v1/models` and receive immediate responses (< 2ms typical) without upstream credential configuration on the harness side.
- **BR-4 — Two-Tier Cascade Failover (DEC-003):** 429/5xx errors must trigger failover first across same-model providers (Tier 1), then across alternative backup models (Tier 2), up to 3 candidate attempts.
- **BR-5 — First-Token Stream Safety (DEC-003):** In streaming mode (`stream: true`), failures occurring before the first content token must be caught and failed over before headers/bytes are committed to the client.
- **BR-6 — Canonical Model Name Masking (DEC-003):** Client responses must always reflect the requested canonical model identifier in the `model` field, even if served by an alternative Tier 2 fallback model.

## Boundaries

**Always do:**
- Mask internal provider IDs with requested canonical model names in both buffered and streaming responses.
- Enforce circuit breaker cooldowns (60s) on models returning 429 or 5xx.
- Hold streaming response connection until the first content token is verified.
- Return 503 in standard OpenAI error envelope only when all candidate models in the failover pool are exhausted.
- Synthesize default `usage` block if upstream provider response omits it.

**Ask first:**
- Modifying authentication requirements from permissive to strictly enforced tokens by default.
- Adding third-party proxy orchestration frameworks.

**Never do:**
- Forward raw upstream 429/5xx errors directly to the client if untried candidates remain in the pool.
- Stream corrupted or mismatched model IDs to external harnesses.
- Make outbound network calls during `GET /v1/models` execution.

## Expected Architecture

```
Client (DeepSeek Harness / Cursor / LangChain)
           │
           ├── GET /v1/models ─────────────► [ In-Memory Registry Cache ] (< 2ms)
           │
           └── POST /v1/chat/completions
                     │
                     ▼
             [ CascadeRouter ]
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
    [ Tier 1: Same Model ]   [ Tier 2: Backup Model ]
    (Groq -> Nvidia -> OR)   (Alternative models)
         │                       │
         └───────────┬───────────┘
                     │ (First-Token Buffer & Failover Catch)
                     ▼
          [ OpenAIProviderClient ]
                     │
                     ▼
       Upstream Free Cloud Providers
```

## Scope / MVP

### MAY EDIT
- `backend/app/api/v1/__init__.py` (New: Router aggregation)
- `backend/app/api/v1/models.py` (New: GET /v1/models)
- `backend/app/api/v1/chat.py` (New: POST /v1/chat/completions)
- `backend/app/core/balancer/router.py` (New: Two-tier failover & circuit breaker)
- `backend/app/core/balancer/__init__.py` (New: Package exports)
- `backend/app/core/adapters/openai_client.py` (New: Outbound client & stream pre-buffering)
- `backend/app/core/adapters/__init__.py` (New: Package exports)
- `backend/app/config.py` (Add optional `proxy_master_key` setting)
- `.env.example` (Add `PROXY_MASTER_KEY` documentation)
- `backend/app/main.py` (Mount /v1 router)
- `backend/tests/test_openai_proxy.py` (New: Proxy endpoints & harness interop tests)
- `backend/tests/test_cascade_failover.py` (New: Two-tier failover & stream buffer tests)
- `TASKS.md`, `HANDOFF.md` (Update: Progress tracking)

### DO NOT TOUCH
- `backend/app/main.py` `/health` endpoint behavior.
- `backend/app/core/providers/models.py`, `registry.py` (reuse without breaking contracts).
- `backend/app/core/discovery/openrouter.py` (reuse without breaking contracts).
- `docs/decisions/` records.

## Acceptance Criteria

- **AC-1 (Models Listing Format):** `GET /v1/models` returns HTTP 200 with `{ "object": "list", "data": [ ... ] }` containing `auto:free` and registered canonical models with `id`, `object="model"`, and `owned_by`.
- **AC-2 (Models In-Memory Determinism):** `GET /v1/models` resolves entirely from in-memory registry cache without outbound network requests or disk I/O (typical response latency < 2ms under local probe).
- **AC-3 (Permissive Authentication):** `POST /v1/chat/completions` accepts requests with arbitrary `Authorization: Bearer <any>` or without auth headers when `PROXY_MASTER_KEY` is unset; returns 401 with OpenAI error envelope if master key is set and mismatch occurs.
- **AC-4 (Non-Streaming Chat Completion):** Valid completion request to a working candidate returns standard OpenAI completion object with `choices[0].message.content`, `id`, `created`, `usage`, and canonical `model`. If upstream omits `usage`, default zeroed usage is synthesized.
- **AC-5 (Streaming SSE Chat Completion):** Valid streaming completion (`stream: true`) returns `Content-Type: text/event-stream` with valid `data: {...}\n\n` chunks ending with `data: [DONE]\n\n`.
- **AC-6 (Model Name Masking):** In both buffered and streaming responses, the `model` property in the payload strictly matches the canonical name requested by the client (even if served by a different provider ID or an alternative Tier 2 fallback model).
- **AC-7 (Tier 1 Same-Model Failover):** When a specific model is requested and Provider A returns HTTP 429/5xx, the router immediately transparently dispatches to Provider B hosting the same canonical model, returning 200 OK without client error.
- **AC-8 (First-Token Stream Failover):** During streaming (`stream: true`), if Candidate 1 returns 429/5xx or an error chunk before the first content token, the proxy catches the error, discards Candidate 1, and streams from Candidate 2 seamlessly.
- **AC-9 (Circuit Breaker Cooldown):** A provider/model that triggered a 429/5xx error is placed on cooldown (60s) and excluded from subsequent candidate queues during the cooldown period.
- **AC-10 (Full Regression Safety):** All 12 existing tests plus new proxy tests pass (100% green).
- **AC-11 (OpenAI Error Payload Shape):** All error responses (400 validation error, 401 auth error, 404 model not found, 503 exhausted pool) conform to standard OpenAI JSON structure `{"error": {"message": str, "type": str, "code": int}}`.

## Traceability Matrix (BR -> AC -> Verification)

| Business Requirement | Acceptance Criteria | Verification Target |
|---|---|---|
| BR-1 (Regression Safety) | AC-10 | `backend/tests/test_health.py`, `test_provider_manifests.py`, `test_openrouter_discovery.py` |
| BR-2 (OpenAI Compatibility) | AC-1, AC-4, AC-5, AC-11 | `test_openai_proxy.py::test_models_endpoint`, `test_chat_completions_buffered`, `test_chat_completions_streaming`, `test_openai_error_shapes` |
| BR-3 (DeepSeek Harness Interop) | AC-2, AC-3 | `test_openai_proxy.py::test_models_instant_lookup`, `test_permissive_auth` |
| BR-4 (Two-Tier Failover) | AC-7, AC-9 | `test_cascade_failover.py::test_tier1_same_model_failover`, `test_circuit_breaker_cooldown` |
| BR-5 (First-Token Stream Safety) | AC-8 | `test_cascade_failover.py::test_streaming_first_token_failover` |
| BR-6 (Canonical Model Masking) | AC-6 | `test_openai_proxy.py::test_canonical_model_name_masking` |

## Delivery / Live Probe

1. **Unit and Integration Tests Execution:**
   - Command: `.venv/bin/pytest backend/tests/test_openai_proxy.py backend/tests/test_cascade_failover.py`
   - Expected Output: All tests pass with exit code 0.
2. **Full Regression Execution:**
   - Command: `.venv/bin/pytest backend/tests`
   - Expected Output: All tests pass with exit code 0 (minimum 18 passing tests).
3. **Live `/v1/models` Query Probe:**
   - Command: `.venv/bin/python -c "import asyncio, httpx; from backend.app.main import app; c = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test'); r = asyncio.run(c.get('/v1/models')); print(f'Status: {r.status_code}, Models count: {len(r.json()[\"data\"])}')"`
   - Expected Output: `Status: 200, Models count: N` (where N >= 1, containing `auto:free`).
4. **Live `/v1/chat/completions` Failover Simulation Probe:**
   - Command: `.venv/bin/python -c "from backend.app.main import app; import httpx, asyncio; c = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test'); r = asyncio.run(c.post('/v1/chat/completions', json={'model': 'non-existent-model-xyz', 'messages': [{'role': 'user', 'content': 'hi'}]})); print(f'Status: {r.status_code}, Error type: {r.json()[\"error\"][\"type\"]}')"`
   - Expected Output: `Status: 404, Error type: invalid_request_error`.

## Risks / Deficiencies / Deviations

- **Risk:** Client disconnects mid-stream.
  - *Mitigation:* The async generator catches `httpx.RemoteProtocolError` / disconnect and terminates gracefully.
- **Risk:** All providers exhausted for all models.
  - *Mitigation:* Returns standard OpenAI error payload with HTTP 503 and clear explanation.
- **Deficiencies:** Prompt context-guard length counting is deferred to Phase P3.
- **Deviations:** None from roadmap.

$END_BODY

$START_LINKS
IMPLEMENTS: DEC-001, DEC-002, DEC-003, P1-ROADMAP
IMPACTS: backend/app/api/v1, backend/app/core/balancer, backend/app/core/adapters
REQUIRES: backend/app/core/providers/registry.py, backend/app/config.py
$END_LINKS
$END_ARTIFACT_GOAL_PROXY_FAILOVER

$START_SECTION_SCENARIOS

$START_ARTIFACT_CASE_HARNESS_FETCH_MODELS
TYPE: USE_CASE
KEYWORDS: deepseek harness, fetch models, dropdown, instant

$START_CONTRACT
PURPOSE: Provide instant model listing when external harness clicks "Fetch available models".
DESCRIPTION: DeepSeek Harness -> GET /v1/models -> Returns 200 OK with model list in-memory without remote requests.
RATIONALE: External harnesses timeout quickly if model fetching triggers remote requests.
ACCEPTANCE_CRITERIA: AC-1, AC-2, AC-3
$END_CONTRACT

$START_BODY
### Scenario Description
1. DeepSeek Harness configured with `Base URL: http://localhost:8000/v1` and arbitrary API key.
2. User clicks "Fetch available models" button.
3. Harness dispatches `GET http://localhost:8000/v1/models`.
4. Proxy immediately retrieves cached canonical models from `ProviderRegistry` without outbound network calls.
5. Harness receives JSON with `object: "list"` and populates model selector dropdown immediately.
$END_BODY

$START_LINKS
IMPLEMENTS: BR-2, BR-3
IMPACTS: backend/app/api/v1/models.py
REQUIRES: GOAL_PROXY_FAILOVER
$END_LINKS
$END_ARTIFACT_CASE_HARNESS_FETCH_MODELS

$START_ARTIFACT_CASE_TRANSPARENT_FAILOVER
TYPE: USE_CASE
KEYWORDS: rate limit, 429, failover, two-tier, retry

$START_CONTRACT
PURPOSE: Protect client from rate limits by silently rerouting to alternative providers.
DESCRIPTION: Client -> POST /v1/chat/completions -> Primary hits 429/5xx -> Router calls Secondary -> Client gets 200 OK.
RATIONALE: Zero-cost models have aggressive rate limits; transparent retry ensures uninterrupted client experience.
ACCEPTANCE_CRITERIA: AC-4, AC-6, AC-7, AC-9
$END_CONTRACT

$START_BODY
### Scenario Description
1. Client requests completion for `meta-llama/llama-3.3-70b-instruct`.
2. Router resolves candidate queue: Candidate 1 (Groq), Candidate 2 (Nvidia NIM), Candidate 3 (OpenRouter).
3. Candidate 1 returns HTTP 429 (Rate Limit Exceeded).
4. Router records Candidate 1 in circuit breaker cooldown (60s).
5. Router automatically dispatches the exact same request to Candidate 2.
6. Candidate 2 returns HTTP 200 with completion text.
7. Proxy masks response `model` to `meta-llama/llama-3.3-70b-instruct` and returns HTTP 200 to client.
8. Client experiences zero errors.
$END_BODY

$START_LINKS
IMPLEMENTS: BR-4, BR-6
IMPACTS: backend/app/core/balancer/router.py
REQUIRES: GOAL_PROXY_FAILOVER
$END_LINKS
$END_ARTIFACT_CASE_TRANSPARENT_FAILOVER

$START_ARTIFACT_CASE_STREAM_PREBUFFER
TYPE: USE_CASE
KEYWORDS: sse, streaming, first-token buffer, failover

$START_CONTRACT
PURPOSE: Catch early streaming errors before committing SSE bytes to the client.
DESCRIPTION: Client requests stream -> Primary fails on chunk 0 -> Discard stream -> Connect Secondary -> Stream tokens.
RATIONALE: Once HTTP 200 chunked headers are sent to client, failover cannot be executed invisibly.
ACCEPTANCE_CRITERIA: AC-5, AC-6, AC-8
$END_CONTRACT

$START_BODY
### Scenario Description
1. Client dispatches `POST /v1/chat/completions` with `stream: true`.
2. Proxy opens connection to primary candidate and buffers initial response.
3. Primary candidate returns HTTP 429/5xx or in-stream JSON error before any valid delta content token is emitted.
4. Proxy catches error before sending any SSE handshake to the client.
5. Primary candidate placed in cooldown; proxy connects to secondary candidate.
6. Secondary candidate emits first valid token chunk (`choices[0].delta.content`).
7. Proxy flushes HTTP 200 `text/event-stream` headers and begins streaming tokens downstream with masked model name.
$END_BODY

$START_LINKS
IMPLEMENTS: BR-5, BR-6
IMPACTS: backend/app/core/adapters/openai_client.py
REQUIRES: GOAL_PROXY_FAILOVER
$END_LINKS
$END_ARTIFACT_CASE_STREAM_PREBUFFER

$END_SECTION_SCENARIOS

$END_DOCUMENT
