# SPEC-T-004 — OpenAI Proxy Endpoints and Cascade Failover Router

- **Record:** `specs/T-004-openai-proxy-and-failover.md`
- **Profile:** MIXED (Adding OpenAI-compatible proxy endpoints, two-tier failover engine, and streaming safe-router to existing FastAPI app)
- **Version:** 1.0.0
- **Status:** draft
- **Approval:** pending
- **Roadmap:** Phase P1 "Core OpenAI Proxy, Declarative Provider Registry, and OpenRouter Integration"
- **Task:** `TASKS.md` -> T-004 "OpenAI Proxy Endpoints and Cascade Failover Router"
- **Input RECON:** Embedded section below (Commit: `db46b03`, Date: 2026-10-22)
- **Implementation Status:** NOT STARTED / NOT RUN / APPROVAL PENDING
- **Governance:** [PROJECT-PROCESS.md](PROJECT-PROCESS.md), [AGENTS.md](AGENTS.md)

$START_DOCUMENT
PURPOSE: Expose standard OpenAI endpoints (/v1/chat/completions and /v1/models) enabling external developer tools and harnesses (DeepSeek Harness, Cursor, LangChain) to execute zero-cost inference with transparent two-tier cascade failover upon rate limits (429/5xx).
SCOPE: Proxy routing endpoints, request/response models, two-tier failover engine, candidate queue selection, canonical model masking, first-token stream pre-buffering, and automated tests.
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
DESCRIPTION: Implement `GET /v1/models` (servicing cached models in < 2ms) and `POST /v1/chat/completions` (supporting standard JSON and SSE streams). Implement Two-Tier Failover: Tier 1 tries the exact same model across active providers; Tier 2 falls back to alternative models. Pre-buffer streaming SSE to catch early 429 errors before flushing headers, and mask response model IDs with the requested canonical name.
RATIONALE: External harnesses require high stability; upstream free models frequently hit rate limits. Transparent retry and canonical name masking protect client applications from disruption.
ACCEPTANCE_CRITERIA: AC-1 through AC-10 covering endpoint contracts, permissive auth, two-tier failover, streaming pre-buffering, model masking, circuit breaker cooldowns, and regression safety.
$END_CONTRACT

$START_BODY
## Done when

- AC-1 through AC-10 pass on verified code.
- `GET /v1/models` returns standard OpenAI model list containing `auto:free` and discovered canonical models, responding in < 2ms from memory without network calls.
- `POST /v1/chat/completions` accepts standard OpenAI payloads (buffered and SSE streaming) using permissive auth (works with arbitrary or empty client API keys).
- Simulated 429/503 on primary candidate triggers transparent failover to secondary candidate, returning 200 OK to the client with canonical model name preserved.
- Streaming requests (`stream: true`) pre-buffer the first chunk: if an upstream error occurs before the first content token, failover executes seamlessly before streaming begins.
- Regression test suite (`pytest backend/tests`) passes 100% green (all 12 existing tests + new proxy tests).

## Stop and ask when

- Implementation requires altering the agreed technology stack (Python 3.11+, FastAPI, Pydantic v2, httpx).
- Modifying previously approved provider schema or OpenRouter discovery logic.
- Adding third-party proxy gateway wrappers (e.g. LiteLLM) rather than lightweight native FastAPI router.

## Context / Input RECON

**Baseline Snapshot:** Git commit `db46b03` (Date: 2026-10-22, working tree clean).

| Area | Verified Baseline State | Evidence Source |
|---|---|---|
| Request | OpenAI proxy (`/v1/chat/completions`, `/v1/models`), Two-Tier Failover, DeepSeek Harness interop, SSE pre-buffering, model masking | User requests; DEC-001, DEC-002, DEC-003; DeepSeek Harness screenshot |
| Registry | `ProviderRegistry` loaded with 10 manifests; in-memory cache supporting `register_models()`, `get_models()`, `get_model_candidates(canonical)` | `backend/app/core/providers/` |
| Discovery | `OpenRouterDiscoveryService` discovers live free models, verified in live probe (20 models) | `backend/app/core/discovery/` |
| Runtime | Python 3.15.0 in `.venv`, FastAPI 0.159.1, Pydantic 2.14.1, httpx 0.28.1 | Verified installed in `.venv` |
| Existing Tests | 12 tests in `backend/tests/` (100% passing in 0.06s) | `pytest backend/tests` execution |

## What we add / build

1. **`backend/app/api/v1/models.py`:**
   - OpenAI-compatible `GET /v1/models` endpoint:
     - Returns JSON `{ "object": "list", "data": [ ... ] }`.
     - Synthesizes `auto:free` model (owned_by: "open-freebie-finder").
     - Iterates discovered models from `ProviderRegistry.get_models()`, deduping by `canonical_name`.
     - Returns within < 2ms directly from in-memory cache with zero network calls.
2. **`backend/app/api/v1/chat.py`:**
   - OpenAI-compatible `POST /v1/chat/completions` endpoint:
     - Request models: `ChatCompletionRequest` (messages, model, stream, temperature, max_tokens, etc.).
     - Permissive authentication: accepts any `Authorization: Bearer <token>` or none; optionally enforces `Settings.proxy_master_key` if configured.
     - Dispatches request through `CascadeRouter`.
     - Supports buffered response (`ChatCompletionResponse`) and Streaming SSE (`text/event-stream`).
3. **`backend/app/core/balancer/router.py`:**
   - `CascadeRouter` class:
     - Circuit breaker tracking: maintains dictionary of `(provider_id, model_id) -> cooldown_until_timestamp`. Default cooldown: 60 seconds upon 429/5xx.
     - Two-Tier Candidate Resolution:
       - If `model == "auto:free"`: gathers all active free models across all enabled providers, sorted by priority/health.
       - If specific model requested (e.g. `meta-llama/llama-3.3-70b-instruct`):
         - **Tier 1:** Finds all provider instances for that exact canonical name (`registry.get_model_candidates(model)`).
         - **Tier 2:** If all Tier 1 candidates fail or are in cooldown, falls back to alternative models in registry.
     - Execution loop: tries candidates in order; on 429/5xx/timeout, records cooldown and advances to next candidate.
     - If all candidates exhausted, raises HTTP 503 ("All free pool candidates exhausted").
4. **`backend/app/core/adapters/openai_adapter.py`:**
   - `OpenAIProviderClient` class:
     - Formats outbound payload (mapping canonical model name to provider's raw `id`).
     - Injects appropriate upstream credentials (`Authorization: Bearer <key>`).
     - Non-streaming execution via `httpx.AsyncClient.post`.
     - Streaming execution via `httpx.AsyncClient.stream`:
       - First-token buffer: reads chunks until first valid delta content or error.
       - If 429 status or in-stream error occurs before first content chunk, raises `UpstreamRateLimitError` for router to catch and failover.
       - Overwrites `model` field in streamed chunks with client-requested canonical name.
5. **App Wiring (`backend/app/main.py`):**
   - Mounts `/v1` router into FastAPI application.
6. **Tests (`backend/tests/test_openai_proxy.py`, `backend/tests/test_cascade_failover.py`):**
   - Unit and integration tests covering buffered completion, streaming SSE, two-tier failover, in-stream 429 failover, and model name masking.

## Stack / Dependencies

- **Profile:** MIXED (Extending existing backend without adding external dependencies).
- **Existing Stack:** Python 3.15.0, FastAPI 0.159.1, Pydantic 2.14.1, PyYAML 6.0.3, httpx 0.28.1, aiosqlite 0.22.1, pytest 9.1.1, pytest-asyncio 1.4.0.
- **Proposed Changes:** No changes.

## Business Requirements

- **BR-1 — Regression Safety (DEC-001):** Existing `/health` endpoint and 12 existing tests must remain 100% passing.
- **BR-2 — OpenAI API Compatibility (DEC-001):** Endpoints `/v1/chat/completions` and `/v1/models` must strictly adhere to the OpenAI REST specification.
- **BR-3 — DeepSeek Harness Interoperability (DEC-003):** External harnesses must be able to query `/v1/models` and receive immediate responses (< 2ms) without upstream credential configuration on the harness side.
- **BR-4 — Two-Tier Cascade Failover (DEC-003):** 429/5xx errors must trigger failover first across same-model providers (Tier 1), then across alternative backup models (Tier 2).
- **BR-5 — First-Token Stream Safety (DEC-003):** In streaming mode (`stream: true`), failures occurring before the first content token must be caught and failed over before headers/bytes are committed to the client.
- **BR-6 — Canonical Model Name Masking (DEC-003):** Client responses must always reflect the requested canonical model identifier in the `model` field.

## Boundaries

**Always do:**
- Mask internal provider IDs with requested canonical model names in both buffered and streaming responses.
- Enforce circuit breaker cooldowns (60s) on models returning 429 or 5xx.
- Hold streaming response connection until the first token is verified.
- Return 503 only when all candidate models in the failover pool are exhausted.

**Ask first:**
- Modifying authentication requirements from permissive to strictly enforced tokens by default.
- Adding third-party proxy orchestration frameworks.

**Never do:**
- Forward raw upstream 429 errors directly to the client if untried candidates remain in the pool.
- Stream corrupted or mismatched model IDs to external harnesses.
- Make outbound network calls during `GET /v1/models` execution.

## Expected Architecture

```
Client (DeepSeek Harness / Cursor)
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
- **AC-2 (Models Latency Determinism):** `GET /v1/models` resolves entirely in-memory in < 2ms without initiating outbound HTTP calls.
- **AC-3 (Permissive Authentication):** `POST /v1/chat/completions` accepts requests with arbitrary `Authorization: Bearer <any>` or without auth headers when master key is unconfigured.
- **AC-4 (Non-Streaming Chat Completion):** Valid completion request to a working candidate returns standard OpenAI completion object with `choices[0].message.content`, `id`, `created`, `usage`, and canonical `model`.
- **AC-5 (Streaming SSE Chat Completion):** Valid streaming completion (`stream: true`) returns `Content-Type: text/event-stream` with valid `data: {...}\n\n` chunks ending with `data: [DONE]\n\n`.
- **AC-6 (Model Name Masking):** In both buffered and streaming responses, the `model` property in the payload strictly matches the canonical name requested by the client (even if the upstream returned an internal provider ID).
- **AC-7 (Tier 1 Same-Model Failover):** When a specific model is requested and Provider A returns HTTP 429, the router immediately transparently dispatches to Provider B hosting the same canonical model, returning 200 OK without client error.
- **AC-8 (First-Token Stream Failover):** During streaming (`stream: true`), if Candidate 1 returns 429 or an error chunk before the first content token, the proxy catches the error, discards Candidate 1, and streams from Candidate 2 seamlessly.
- **AC-9 (Circuit Breaker Cooldown):** A provider/model that triggered a 429 error is placed on cooldown (60s) and excluded from subsequent candidate queues during the cooldown period.
- **AC-10 (Full Regression Safety):** All 12 existing tests plus new proxy tests pass (100% green).

## Traceability Matrix (BR -> AC -> Verification)

| Business Requirement | Acceptance Criteria | Verification Target |
|---|---|---|
| BR-1 (Regression Safety) | AC-10 | `backend/tests/test_health.py`, `test_provider_manifests.py`, `test_openrouter_discovery.py` |
| BR-2 (OpenAI Compatibility) | AC-1, AC-4, AC-5 | `test_openai_proxy.py::test_models_endpoint`, `test_chat_completions_buffered`, `test_chat_completions_streaming` |
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
   - Simulated test verifying that an injected 429 on Candidate 1 results in HTTP 200 from Candidate 2 with 0 errors to client.

## Risks / Deficiencies / Deviations

- **Risk:** Client disconnects mid-stream.
  - *Mitigation:* The async generator catches `httpx.RemoteProtocolError` / disconnect and terminates gracefully.
- **Risk:** All providers exhausted for all models.
  - *Mitigation:* Returns standard OpenAI error payload with HTTP 503 and clear explanation.
- **Deficiencies:** Advanced prompt token counting for context window guard is simplified to length estimation in Phase P1; full token counting will be refined in P3.
- **Deviations:** None from roadmap.

$END_BODY

$START_LINKS
IMPLEMENTS: DEC-001, DEC-002, DEC-003, P1-ROADMAP
IMPACTS: backend/app/api/v1, backend/app/core/balancer, backend/app/core/adapters
REQUIRES: backend/app/core/providers/registry.py
$END_LINKS
$END_ARTIFACT_GOAL_PROXY_FAILOVER

$START_SECTION_SCENARIOS

$START_ARTIFACT_CASE_HARNESS_FETCH_MODELS
TYPE: USE_CASE
KEYWORDS: deepseek harness, fetch models, dropdown, instant

$START_CONTRACT
PURPOSE: Provide instant model listing when external harness clicks "Fetch available models".
DESCRIPTION: DeepSeek Harness -> GET /v1/models -> Returns 200 OK with model list in < 2ms.
RATIONALE: External harnesses timeout quickly if model fetching triggers remote requests.
ACCEPTANCE_CRITERIA: AC-1, AC-2, AC-3
$END_CONTRACT

$START_BODY
### Scenario Description
1. DeepSeek Harness configured with `Base URL: http://localhost:8000/v1` and arbitrary API key.
2. User clicks "Fetch available models" button.
3. Harness dispatches `GET http://localhost:8000/v1/models`.
4. Proxy immediately retrieves cached canonical models from `ProviderRegistry` without outbound network calls.
5. Harness receives JSON with `object: "list"` and populates model selector dropdown within 1-2 milliseconds.
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
DESCRIPTION: Client -> POST /v1/chat/completions -> Primary hits 429 -> Router calls Secondary -> Client gets 200 OK.
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
3. Primary candidate returns HTTP 429 or in-stream JSON error before any valid delta content token is emitted.
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
