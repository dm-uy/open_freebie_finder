# SPEC-T-003 — Declarative Provider Registry and Dynamic Discovery Engine

- **Record:** `specs/T-003-declarative-providers-and-discovery.md`
- **Profile:** MIXED (Adding provider registry, declarative schemas, and OpenRouter discovery to existing FastAPI scaffold)
- **Version:** 1.0.0
- **Status:** draft
- **Approval:** pending
- **Roadmap:** Phase P1 "Core OpenAI Proxy, Declarative Provider Registry, and OpenRouter Integration"
- **Task:** `TASKS.md` -> T-003 "Declarative Provider Registry and Dynamic Discovery Engine"
- **Input RECON:** Embedded section below (Commit: `cb75501`)
- **Implementation Status:** NOT STARTED / NOT RUN / APPROVAL PENDING
- **Governance:** [PROJECT-PROCESS.md](PROJECT-PROCESS.md), [AGENTS.md](AGENTS.md)

$START_DOCUMENT
PURPOSE: Provide a declarative, schema-driven provider registry with 10 built-in manifests covering 90%+ free LLM services, and a dynamic discovery worker for OpenRouter zero-cost models.
SCOPE: Manifest schema, registry service, built-in manifests, OpenRouter free models dynamic crawler, in-memory model cache, and automated tests.
KEYWORDS: declarative schema, provider registry, OpenRouter discovery, free models, canonical mapping, non-blocking cache

$START_DOCUMENT_PLAN
$DOCUMENT_PLAN
SECTION_FEATURE:
GOAL Declarative Provider Registry and Free Model Discovery => GOAL_PROVIDER_DISCOVERY
SECTION_SCENARIOS:
USE_CASE Query Cached Free Models for External Harnesses => CASE_QUERY_MODELS
USE_CASE Crawl and Filter Zero-Cost OpenRouter Models => CASE_CRAWL_OPENROUTER
$END_DOCUMENT_PLAN

$START_SECTION_FEATURE
$START_ARTIFACT_GOAL_PROVIDER_DISCOVERY
TYPE: GOAL
KEYWORDS: providers, manifest, openrouter, discovery, schema, cache

$START_CONTRACT
PURPOSE: Enable zero-code provider additions via YAML manifests and maintain an in-memory registry of free LLM models dynamically refreshed from upstream sources.
DESCRIPTION: Load 10 default provider manifests (OpenRouter, Groq, Nvidia NIM, Google Gemini, GitHub Models, Cerebras, Mistral, HuggingFace, Cloudflare, Local Ollama/vLLM), parse provider configs, query OpenRouter for dynamic zero-cost models (`pricing.prompt == 0 and pricing.completion == 0`), map canonical models across providers, and expose an in-memory lookup cache responding in < 2ms.
RATIONALE: Eliminates hardcoded provider logic, allows immediate compatibility with 90%+ free LLM sources, and provides the foundation for DeepSeek Harness and downstream proxy endpoints.
ACCEPTANCE_CRITERIA: AC-1 through AC-8 below covering schema validation, manifest loading, OpenRouter parsing, canonical mapping, caching, error handling, boundaries, and regression.
$END_CONTRACT

$START_BODY
## Done when

- AC-1 through AC-8 pass completely on verified code.
- Declarative provider schema successfully validates all 10 built-in provider manifests.
- OpenRouter crawler reliably extracts only free models (`pricing.prompt == 0 and pricing.completion == 0`) and populates token context lengths.
- In-memory registry provides instant non-blocking model lookups (< 2ms) without making outbound HTTP calls during lookup.
- Regression test suite (`backend/tests/test_health.py`) continues to pass (100% green).

## Stop and ask when

- Implementation requires modifying agreed technology stack (Python 3.11+, FastAPI, Pydantic v2, PyYAML, httpx).
- An external dependency outside `backend/requirements.txt` is requested.
- Downstream OpenAI proxy `/v1/chat/completions` logic is touched (belongs to T-004).
- Upstream credentials or secrets are placed into source-controlled files.

## Context / Input RECON

**Baseline Snapshot:** Git commit `cb75501` (clean working tree).

| Area | Verified Baseline State | Evidence Source |
|---|---|---|
| Request | Declarative provider schema, 10 out-of-the-box manifests, dynamic OpenRouter discovery, canonical mapping | User request; DEC-002; DEC-003 |
| Decisions | DEC-001 (FastAPI/React/SQLite); DEC-002 (Declarative schema & manifests); DEC-003 (Canonical mapping & harness interop) | `docs/decisions/` |
| Runtime | Python 3.15.0 in `.venv`, FastAPI 0.159.1, Pydantic 2.14.1, PyYAML 6.0.3, httpx 0.28.1 | Verified installed in `.venv` |
| Scaffold | `backend/app/main.py` with `/health`, `backend/app/config.py` with settings singleton | `backend/app/` |
| Existing Tests | `backend/tests/test_health.py` (1 passed in 0.01s) | `pytest backend/tests` execution |
| Remote API | OpenRouter models API at `https://openrouter.ai/api/v1/models` returns JSON `{ "data": [ { "id": "...", "pricing": {"prompt": "0", "completion": "0"}, "context_length": ... } ] }` | OpenRouter public API documentation |

## What we add / build

1. **`backend/app/core/providers/models.py`:**
   - Pydantic v2 models:
     - `ProviderAuth`: `type` (bearer, header), `api_key_env`, `custom_header_name`.
     - `DiscoveryRule`: `type` (openrouter_free, all_available, regex, manual), `filter_expression`, `model_id_field`, `context_length_field`.
     - `ProviderManifest`: `id`, `name`, `base_url`, `models_endpoint`, `auth`, `discovery`, `is_enabled`, `description`.
     - `DiscoveredModel`: `id`, `canonical_name`, `provider_id`, `context_window`, `is_free`, `metadata`.
2. **`backend/app/core/providers/manifests.yaml` (or Python equivalent):**
   - 10 pre-configured manifests:
     1. `openrouter`: `https://openrouter.ai/api/v1`, dynamic free discovery.
     2. `groq`: `https://api.groq.com/openai/v1`, all available models on free-tier key.
     3. `nvidia_nim`: `https://integrate.api.nvidia.com/v1`, hosted free open weights.
     4. `google_gemini`: `https://generativelanguage.googleapis.com/v1beta/openai/`, 15 RPM free tier.
     5. `github_models`: `https://models.inference.ai.azure.com`, GitHub PAT free tier.
     6. `cerebras`: `https://api.cerebras.ai/v1`, ultra-fast free tier.
     7. `mistral`: `https://api.mistral.ai/v1`, experiment tier.
     8. `huggingface`: `https://api-inference.huggingface.co/v1`, serverless models.
     9. `cloudflare`: `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1`, 10k daily neurons.
     10. `local_ollama`: `http://localhost:11434/v1`, local offline fallback.
3. **`backend/app/core/providers/registry.py`:**
   - `ProviderRegistry` class:
     - Loads manifests from YAML/defaults.
     - Resolves active providers based on available keys or enabled flags.
     - Maintains thread-safe in-memory cache of `DiscoveredModel` instances.
     - Provides instant lookup methods: `get_models()`, `get_model_candidates(canonical_name)`.
4. **`backend/app/core/discovery/openrouter.py`:**
   - `OpenRouterDiscoveryService` class:
     - Asynchronously fetches `https://openrouter.ai/api/v1/models` using `httpx.AsyncClient`.
     - Filters items where `pricing.prompt == "0"` and `pricing.completion == "0"`.
     - Maps raw IDs (e.g. `meta-llama/llama-3.3-70b-instruct:free`) to canonical names (`meta-llama/llama-3.3-70b-instruct`).
     - Extracts `context_length`.
5. **Unit & Integration Tests:**
   - `backend/tests/test_provider_manifests.py`: Validates all 10 manifests match schema.
   - `backend/tests/test_openrouter_discovery.py`: Mocks upstream OpenRouter API responses (including free, paid, empty, and rate-limited scenarios).

## Business Requirements

- **BR-1 — Regression Safety (DEC-001):** The existing `/health` endpoint and test suite must remain 100% operational with identical responses and zero degradation.
- **BR-2 — Declarative Provider Schema (DEC-002):** Providers must be fully expressible in declarative YAML/JSON format without requiring custom Python subclasses for standard OpenAI-compatible endpoints.
- **BR-3 — Out-of-the-Box Coverage (DEC-002):** The system must bundle the 10 agreed provider manifests covering 90%+ of free inference services out-of-the-box.
- **BR-4 — Dynamic Zero-Cost Discovery (VISION):** The OpenRouter discovery engine must dynamically extract all models where prompt and completion costs are strictly zero, discarding paid models.
- **BR-5 — Canonical Model Mapping (DEC-003):** Models with provider-specific suffixes (e.g. `:free`) must be registered under their clean canonical names, linking the specific provider endpoint to the canonical alias.
- **BR-6 — Non-blocking In-Memory Lookups (DEC-003):** Model listing queries must be serviced from the internal registry cache in < 2ms without initiating external HTTP round-trips.

## Boundaries

**Always do:**
- Validate all incoming provider manifests against Pydantic schema before inserting into registry.
- Maintain thread-safe read access to the in-memory model cache.
- Extract and record token context windows for each model.
- Keep credentials isolated (load from environment / config, never store secrets in manifests).

**Ask first:**
- Adding additional heavy third-party dependencies.
- Modifying the public `/health` response structure.
- Changing the schema format of `providers.yaml`.

**Never do:**
- Hardcode dynamic free model IDs in Python source code.
- Block the API event loop during external network polling.
- Commit private provider API keys to the repository.

## Expected Architecture

```
[ FastAPI App Lifespan / Admin Task ]
                 │
                 ▼ (Calls background discovery)
    [ OpenRouterDiscoveryService ] ──(HTTP GET)──► [ OpenRouter API ]
                 │
                 ▼ (Emits DiscoveredModel items)
    [ ProviderRegistry (In-Memory Cache) ]
                 ▲
                 │ (Loads manifests at startup)
      [ providers.yaml (10 Manifests) ]
```

## Scope / MVP

### MAY EDIT
- `backend/app/core/providers/models.py` (New: Schema definitions)
- `backend/app/core/providers/manifests.yaml` (New: 10 provider definitions)
- `backend/app/core/providers/registry.py` (New: Registry & caching)
- `backend/app/core/providers/__init__.py` (New: Package exports)
- `backend/app/core/discovery/openrouter.py` (New: OpenRouter discovery worker)
- `backend/app/core/discovery/__init__.py` (New: Package exports)
- `backend/tests/test_provider_manifests.py` (New: Manifest & schema tests)
- `backend/tests/test_openrouter_discovery.py` (New: Discovery unit tests)
- `backend/app/config.py` (Update: Add manifests path setting if needed)
- `TASKS.md`, `HANDOFF.md` (Update: Task progress tracking)

### DO NOT TOUCH
- `backend/app/main.py` `/health` endpoint behavior (must remain invariant).
- `docs/decisions/` existing records (read-only references).
- Project documentation in `AGENTS.md`, `VISION.md` (must preserve established principles).

## Acceptance Criteria

- **AC-1 (Schema Validation):** `ProviderManifest` and `DiscoveryRule` Pydantic models validate valid configs and raise `ValidationError` on missing `id`, invalid URLs, or unknown discovery types.
- **AC-2 (10 Built-in Manifests):** All 10 default provider manifests in `manifests.yaml` deserialize cleanly into valid `ProviderManifest` objects without errors.
- **AC-3 (OpenRouter Zero-Cost Filter):** Given an OpenRouter API response containing mixed free (`pricing: {"prompt": "0", "completion": "0"}`) and paid (`pricing: {"prompt": "0.000001", "completion": "0.000002"}`) models, `OpenRouterDiscoveryService` extracts ONLY the free models.
- **AC-4 (Context Window Extraction):** For each discovered model, `context_length` is accurately extracted as `context_window` (integer); if missing, defaults to 4096.
- **AC-5 (Canonical Name Extraction):** Models with `:free` suffixes (e.g. `meta-llama/llama-3.3-70b-instruct:free`) are mapped to clean canonical names (`meta-llama/llama-3.3-70b-instruct`).
- **AC-6 (In-Memory Registry Query):** `ProviderRegistry.get_models()` returns the list of registered models in < 2ms without invoking external network requests.
- **AC-7 (Discovery Resilience):** If OpenRouter API returns an HTTP 500 error or network timeout, discovery gracefully handles the exception, logs a warning, and retains previously cached models without crashing the application.
- **AC-8 (Regression Verification):** Running `pytest backend/tests` executes both new tests and `test_health.py`, resulting in 100% passing tests.

## Delivery / Live Probe

1. **Unit Test Execution:**
   - Command: `.venv/bin/pytest backend/tests/test_provider_manifests.py backend/tests/test_openrouter_discovery.py`
   - Expected Output: All tests pass with exit code 0.
2. **Full Regression Execution:**
   - Command: `.venv/bin/pytest backend/tests`
   - Expected Output: All tests pass with exit code 0.
3. **Manual CLI Probe:**
   - Command: `.venv/bin/python -c "from backend.app.core.providers.registry import get_registry; r = get_registry(); print(f'Loaded {len(r.get_manifests())} manifests')"`
   - Expected Output: `Loaded 10 manifests`.

## Risks / Deficiencies / Deviations

- **Risk:** OpenRouter API changes its JSON schema for `/api/v1/models`.
  - *Mitigation:* The discovery service uses safe dictionary getters and validates presence of `pricing` block before parsing.
- **Risk:** Upstream OpenRouter API rate-limits unauthenticated calls.
  - *Mitigation:* The discovery service supports optional `OPENROUTER_API_KEY` header from settings.
- **Deficiencies:** Cloudflare requires an account ID in URL; manifest provides template placeholder `{account_id}`.
- **Deviations:** None from roadmap.

$END_BODY

$START_LINKS
IMPLEMENTS: DEC-002, DEC-003, P1-ROADMAP
IMPACTS: backend/app/core/providers, backend/app/core/discovery
REQUIRES: backend/app/config.py
$END_LINKS
$END_ARTIFACT_GOAL_PROVIDER_DISCOVERY
$END_SECTION_FEATURE
$END_DOCUMENT
