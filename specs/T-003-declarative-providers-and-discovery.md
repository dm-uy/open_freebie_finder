# SPEC-T-003 — Declarative Provider Registry and Dynamic Discovery Engine

- **Record:** `specs/T-003-declarative-providers-and-discovery.md`
- **Profile:** MIXED (Adding declarative provider registry, schemas, and OpenRouter discovery to existing FastAPI scaffold)
- **Version:** 1.1.0
- **Status:** done
- **Approval:** approved (Approved by owner on 2026-10-22)
- **Roadmap:** Phase P1 "Core OpenAI Proxy, Declarative Provider Registry, and OpenRouter Integration"
- **Task:** `TASKS.md` -> T-003 "Declarative Provider Registry and Dynamic Discovery Engine"
- **Input RECON:** Embedded section below (Commit: `99bd025`, Date: 2026-10-22)
- **Implementation Status:** VERIFIED / 10 TESTS PASSED / ALL PROBES CONFIRMED (10 manifests loaded, 20 live models discovered)
- **Governance:** [PROJECT-PROCESS.md](PROJECT-PROCESS.md), [AGENTS.md](AGENTS.md)

$START_DOCUMENT
PURPOSE: Provide a declarative, schema-driven provider registry with 10 built-in manifests covering 90%+ free LLM services, and a dynamic discovery worker for OpenRouter zero-cost models.
SCOPE: Manifest schema, registry service, built-in `providers.yaml`, OpenRouter free models crawler, in-memory model cache, and automated tests.
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
DESCRIPTION: Load 10 default provider manifests from `providers.yaml` (OpenRouter, Groq, Nvidia NIM, Google Gemini, GitHub Models, Cerebras, Mistral, HuggingFace, Cloudflare, Local Ollama/vLLM), parse provider configs into Pydantic models, query OpenRouter for dynamic zero-cost models (`pricing.prompt == "0" and pricing.completion == "0"`), map canonical models across providers, and expose an in-memory lookup cache responding instantaneously without blocking I/O.
RATIONALE: Eliminates hardcoded provider logic, allows immediate compatibility with 90%+ free LLM sources, and provides the foundation for DeepSeek Harness and downstream proxy endpoints.
ACCEPTANCE_CRITERIA: AC-1 through AC-9 below covering schema validation, manifest loading, OpenRouter parsing, canonical mapping, caching, error handling, boundaries, and regression.
$END_CONTRACT

$START_BODY
## Done when

- AC-1 through AC-9 pass completely on verified code.
- Declarative provider schema successfully validates all 10 built-in provider manifests from `backend/app/core/providers/providers.yaml`.
- OpenRouter crawler reliably extracts only free models (`pricing.prompt == "0" and pricing.completion == "0"`) and populates token context lengths.
- In-memory registry provides non-blocking model lookups serviced entirely from memory via `asyncio.Lock` without making outbound HTTP calls during lookup.
- Regression test suite (`backend/tests/test_health.py`) continues to pass (100% green).
- Live probe confirms all 10 manifests load cleanly.

## Stop and ask when

- Implementation requires modifying agreed technology stack (Python 3.11+, FastAPI, Pydantic v2, PyYAML, httpx).
- An external dependency outside `backend/requirements.txt` is requested.
- Downstream OpenAI proxy `/v1/chat/completions` logic is touched (belongs to T-004).
- Upstream credentials or secrets are placed into source-controlled files.

## Context / Input RECON

**Baseline Snapshot:** Git commit `99bd025` (Date: 2026-10-22, working tree clean).

| Area | Verified Baseline State | Evidence Source |
|---|---|---|
| Request | Declarative provider schema, 10 out-of-the-box manifests in `providers.yaml`, dynamic OpenRouter discovery, canonical mapping | User request; DEC-002; DEC-003 |
| Decisions | DEC-001 (FastAPI/React/SQLite); DEC-002 (Declarative schema & manifests); DEC-003 (Canonical mapping & harness interop) | `docs/decisions/` |
| Runtime | Python 3.15.0 in `.venv`, FastAPI 0.159.1, Pydantic 2.14.1, PyYAML 6.0.3, httpx 0.28.1 | Verified installed in `.venv` |
| Scaffold | `backend/app/main.py` with `/health`, `backend/app/config.py` with settings singleton | `backend/app/` |
| Existing Tests | `backend/tests/test_health.py` (1 passed in 0.01s) | `pytest backend/tests` execution |
| Remote API | OpenRouter models API at `https://openrouter.ai/api/v1/models` returns JSON `{ "data": [ { "id": "...", "pricing": {"prompt": "0", "completion": "0"}, "context_length": ... } ] }` | Observed live via public HTTP endpoint on 2026-10-22 |

## What we add / build

1. **`backend/app/core/providers/models.py`:**
   - Pydantic v2 models:
     - `ProviderAuth`: `type` ("bearer" | "header" | "none"), `api_key_env: Optional[str]`, `custom_header_name: Optional[str]`.
     - `DiscoveryRule`:
       - `type`: Literal["openrouter_free", "all_available", "regex", "manual"].
       - `filter_expression: Optional[str]` (Semantics: for `openrouter_free`, checks `pricing.prompt == "0" and pricing.completion == "0"`; for `all_available`, accepts all returned models; for `regex`, compiles as Python regex matching `model.id`; for `manual`, ignored).
       - `model_id_field: str = "id"`.
       - `context_length_field: str = "context_length"`.
       - `static_models: list[str] = []` (used when `type == "manual"`).
     - `ProviderManifest`:
       - `id: str`
       - `name: str`
       - `base_url: str`
       - `models_endpoint: str`
       - `auth: ProviderAuth`
       - `discovery: DiscoveryRule`
       - `is_enabled: bool = True`
       - `description: Optional[str] = None`
     - `DiscoveredModel`:
       - `id: str` (raw provider ID, e.g. `meta-llama/llama-3.3-70b-instruct:free`)
       - `canonical_name: str` (normalized alias, e.g. `meta-llama/llama-3.3-70b-instruct`)
       - `provider_id: str` (e.g. `openrouter`)
       - `context_window: int = 4096`
       - `is_free: bool = True`
       - `metadata: dict = {}`

2. **`backend/app/core/providers/providers.yaml`:**
   - 10 pre-configured manifests matching DEC-002:
     1. `openrouter`: `https://openrouter.ai/api/v1`, dynamic free discovery (`openrouter_free`).
     2. `groq`: `https://api.groq.com/openai/v1`, all available models on free-tier key (`all_available`).
     3. `nvidia_nim`: `https://integrate.api.nvidia.com/v1`, hosted free open weights (`all_available`).
     4. `google_gemini`: `https://generativelanguage.googleapis.com/v1beta/openai/`, 15 RPM free tier (`all_available`).
     5. `github_models`: `https://models.inference.ai.azure.com`, GitHub PAT free tier (`all_available`).
     6. `cerebras`: `https://api.cerebras.ai/v1`, ultra-fast free tier (`all_available`).
     7. `mistral`: `https://api.mistral.ai/v1`, experiment tier (`all_available`).
     8. `huggingface`: `https://api-inference.huggingface.co/v1`, serverless models (`all_available`).
     9. `cloudflare`: `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1`, 10k daily neurons (replaces `{account_id}` with `Settings.cloudflare_account_id` or disables if empty).
     10. `local_ollama`: `http://localhost:11434/v1`, local offline fallback (`all_available`, auth: none).

3. **`backend/app/core/providers/registry.py`:**
   - `ProviderRegistry` class:
     - `__init__(manifests_path: Optional[Path] = None)`
     - `load_manifests() -> None`: Reads `providers.yaml`, validates via Pydantic.
     - `get_manifests() -> list[ProviderManifest]`: Returns all loaded manifests.
     - `get_manifest(provider_id: str) -> Optional[ProviderManifest]`: Looks up manifest by ID.
     - `get_active_providers() -> list[ProviderManifest]`: Filters providers with present API keys or `auth.type == "none"`.
     - `register_models(models: list[DiscoveredModel]) -> None`: Updates in-memory cache protected by `asyncio.Lock`.
     - `get_models() -> list[DiscoveredModel]`: Returns all discovered models from cache.
     - `get_model_candidates(canonical_name: str) -> list[DiscoveredModel]`: Returns all discovered models matching `canonical_name` across active providers.
   - Singleton factory:
     - `get_registry() -> ProviderRegistry`: Module-level cached singleton.

4. **`backend/app/core/discovery/openrouter.py`:**
   - `OpenRouterDiscoveryService` class:
     - `__init__(registry: ProviderRegistry, http_client: Optional[httpx.AsyncClient] = None)`
     - `discover_free_models() -> list[DiscoveredModel]`: Fetches `https://openrouter.ai/api/v1/models`, parses models, filters `pricing.prompt == "0" and pricing.completion == "0"`, normalizes canonical name (strips `:free`), updates registry cache via `register_models`.
     - Error handling: Catches `httpx.HTTPStatusError` (429, 500) and `httpx.RequestError` (timeout, connect), logs warning, and leaves existing cache intact.

5. **Unit & Integration Tests:**
   - `backend/tests/test_provider_manifests.py`: Validates all 10 manifests against Pydantic schema and tests registry lookups.
   - `backend/tests/test_openrouter_discovery.py`: Tests discovery with mocked OpenRouter responses (free, paid, mixed, empty, 429, and 500 errors).

## Stack / Dependencies

- **Profile:** MIXED (Extending existing backend without adding external dependencies).
- **Existing Stack:** Python 3.15.0, FastAPI 0.159.1, Pydantic 2.14.1, PyYAML 6.0.3, httpx 0.28.1, aiosqlite 0.22.1, pytest 9.1.1, pytest-asyncio 1.4.0.
- **Proposed Changes:** No changes. All required packages are already installed in `.venv` and specified in `backend/requirements.txt`.

## Business Requirements

- **BR-1 — Regression Safety (DEC-001):** The existing `/health` endpoint and test suite must remain 100% operational with identical responses and zero degradation.
- **BR-2 — Declarative Provider Schema (DEC-002):** Providers must be fully expressible in declarative YAML format (`providers.yaml`) without requiring custom Python subclasses for standard OpenAI-compatible endpoints.
- **BR-3 — Out-of-the-Box Coverage (DEC-002):** The system must bundle the 10 agreed provider manifests covering 90%+ of free inference services out-of-the-box.
- **BR-4 — Dynamic Zero-Cost Discovery (VISION):** The OpenRouter discovery engine must dynamically extract all models where prompt and completion costs are strictly zero (`pricing.prompt == "0" and pricing.completion == "0"`), discarding paid models.
- **BR-5 — Canonical Model Mapping (DEC-003):** Models with provider-specific suffixes (e.g. `:free`) must be registered under clean canonical names, linking specific provider endpoints to the canonical alias.
- **BR-6 — Non-blocking In-Memory Lookups (DEC-003):** Model listing queries must be serviced from the internal registry cache in-memory using `asyncio.Lock` without initiating external HTTP round-trips.

## Boundaries

**Always do:**
- Validate all incoming provider manifests against Pydantic schema before inserting into registry.
- Protect in-memory cache mutations with `asyncio.Lock`.
- Extract and record token context windows for each model.
- Keep credentials isolated (load from environment / config, never store secrets in manifests).

**Ask first:**
- Adding additional third-party dependencies to `requirements.txt`.
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
    [ ProviderRegistry (In-Memory Cache with asyncio.Lock) ]
                 ▲
                 │ (Loads manifests at startup)
      [ providers.yaml (10 Manifests) ]
```

## Scope / MVP

### MAY EDIT
- `backend/app/core/providers/models.py` (New: Schema definitions)
- `backend/app/core/providers/providers.yaml` (New: 10 provider definitions)
- `backend/app/core/providers/registry.py` (New: Registry & caching)
- `backend/app/core/providers/__init__.py` (New: Package exports)
- `backend/app/core/discovery/openrouter.py` (New: OpenRouter discovery worker)
- `backend/app/core/discovery/__init__.py` (New: Package exports)
- `backend/tests/test_provider_manifests.py` (New: Manifest & schema tests)
- `backend/tests/test_openrouter_discovery.py` (New: Discovery unit tests)
- `TASKS.md`, `HANDOFF.md` (Update: Task progress tracking)

### DO NOT TOUCH
- `backend/app/main.py` `/health` endpoint behavior (must remain invariant).
- `docs/decisions/` existing records (read-only references).
- Project documentation in `AGENTS.md`, `VISION.md` (must preserve established principles).

## Acceptance Criteria

- **AC-1 (Schema Validation):** `ProviderManifest` and `DiscoveryRule` Pydantic models validate valid configs and raise `ValidationError` on missing `id`, invalid URLs, or unknown discovery types.
- **AC-2 (10 Built-in Manifests):** All 10 default provider manifests in `backend/app/core/providers/providers.yaml` deserialize cleanly into valid `ProviderManifest` objects without errors.
- **AC-3 (OpenRouter Zero-Cost Filter):** Given an OpenRouter API response containing mixed free (`pricing: {"prompt": "0", "completion": "0"}`) and paid (`pricing: {"prompt": "0.000001", "completion": "0.000002"}`) models, `OpenRouterDiscoveryService` extracts ONLY the models where both prompt and completion are `"0"`.
- **AC-4 (Context Window Extraction):** For each discovered model, `context_length` is accurately extracted as `context_window` (integer); if missing or zero, defaults to 4096.
- **AC-5 (Canonical Name Extraction):** Models with `:free` suffixes (e.g. `meta-llama/llama-3.3-70b-instruct:free`) are mapped to clean canonical names (`meta-llama/llama-3.3-70b-instruct`).
- **AC-6 (In-Memory Registry Query Determinism):** `ProviderRegistry.get_models()` resolves entirely from internal memory structures without performing network I/O or disk operations.
- **AC-7 (Discovery Resilience on 429/500/Timeout):** When the upstream OpenRouter API returns an HTTP 429, HTTP 500, or connection timeout, discovery catches the error, logs a warning, and retains previously cached models without crashing.
- **AC-8 (Regression Verification):** Running `pytest backend/tests` executes both new tests and `test_health.py`, resulting in 100% passing tests.
- **AC-9 (Candidate Lookup Resolution):** `ProviderRegistry.get_model_candidates("meta-llama/llama-3.3-70b-instruct")` returns all discovered model records across registered providers mapped to that canonical name.

## Traceability Matrix (BR -> AC -> Verification)

| Business Requirement | Acceptance Criteria | Verification Target |
|---|---|---|
| BR-1 (Regression Safety) | AC-8 | `backend/tests/test_health.py` passes |
| BR-2 (Declarative Schema) | AC-1 | `test_provider_manifests.py::test_manifest_schema_validation` |
| BR-3 (Out-of-the-Box Coverage) | AC-2 | `test_provider_manifests.py::test_load_all_ten_builtin_manifests` |
| BR-4 (Dynamic Zero-Cost Discovery) | AC-3, AC-4 | `test_openrouter_discovery.py::test_filter_zero_cost_models` |
| BR-5 (Canonical Model Mapping) | AC-5, AC-9 | `test_openrouter_discovery.py::test_canonical_name_mapping`, `test_provider_manifests.py::test_model_candidates_lookup` |
| BR-6 (Non-blocking In-Memory Lookups) | AC-6, AC-7 | `test_provider_manifests.py::test_in_memory_lookup_zero_network`, `test_openrouter_discovery.py::test_resilience_on_errors` |

## Delivery / Live Probe

1. **Unit Test Execution:**
   - Command: `.venv/bin/pytest backend/tests/test_provider_manifests.py backend/tests/test_openrouter_discovery.py`
   - Expected Output: All tests pass with exit code 0.
2. **Full Regression Execution:**
   - Command: `.venv/bin/pytest backend/tests`
   - Expected Output: All tests pass with exit code 0 (minimum 5 passing tests).
3. **Registry Manifests CLI Probe:**
   - Command: `.venv/bin/python -c "from backend.app.core.providers.registry import get_registry; r = get_registry(); print(f'Loaded {len(r.get_manifests())} manifests: {[m.id for m in r.get_manifests()]}')"`
   - Expected Output: `Loaded 10 manifests: ['openrouter', 'groq', 'nvidia_nim', 'google_gemini', 'github_models', 'cerebras', 'mistral', 'huggingface', 'cloudflare', 'local_ollama']`.
4. **Optional Live OpenRouter Discovery Probe:**
   - Command: `.venv/bin/python -c "import asyncio, httpx; from backend.app.core.providers.registry import get_registry; from backend.app.core.discovery.openrouter import OpenRouterDiscoveryService; r = get_registry(); s = OpenRouterDiscoveryService(r); m = asyncio.run(s.discover_free_models()); print(f'Discovered {len(m)} live free models on OpenRouter')"`
   - Expected Output: `Discovered N live free models on OpenRouter` (where N > 0 if internet is accessible, or logs warning and returns 0 if offline).

## Risks / Deficiencies / Deviations

- **Risk:** OpenRouter API changes its JSON schema for `/api/v1/models`.
  - *Mitigation:* The discovery service uses safe dictionary getters and validates presence of `pricing` block before parsing.
- **Risk:** Upstream OpenRouter API rate-limits unauthenticated calls.
  - *Mitigation:* The discovery service supports optional `OPENROUTER_API_KEY` header from settings.
- **Deficiencies:** Cloudflare requires an account ID in URL; manifest provides template placeholder `{account_id}` resolved from `Settings.cloudflare_account_id`.
- **Scope Note:** `backend/app/config.py` and `.env.example` were augmented with `cloudflare_account_id` in commit `99bd025` to support clean Cloudflare `{account_id}` manifest template resolution.
- **Deviations:** None from roadmap.

$END_BODY

$START_LINKS
IMPLEMENTS: DEC-002, DEC-003, P1-ROADMAP
IMPACTS: backend/app/core/providers, backend/app/core/discovery
REQUIRES: backend/app/config.py
$END_LINKS
$END_ARTIFACT_GOAL_PROVIDER_DISCOVERY

$START_SECTION_SCENARIOS

$START_ARTIFACT_CASE_QUERY_MODELS
TYPE: USE_CASE
KEYWORDS: external harness, lookup, non-blocking, canonical

$START_CONTRACT
PURPOSE: Allow external harnesses (DeepSeek Harness, Cursor) to instantly retrieve available free models without delay.
DESCRIPTION: External harness -> GET /v1/models (or registry lookup) -> Returns cached DiscoveredModel items with canonical names.
RATIONALE: External tools have short connection timeouts when fetching models; queries must resolve purely from in-memory cache.
ACCEPTANCE_CRITERIA: AC-6, AC-9
$END_CONTRACT

$START_BODY
### Scenario Description
1. External harness or downstream proxy invokes `registry.get_models()`.
2. Registry reads from local in-memory model collection without triggering any outbound network calls.
3. Collection contains canonical names (e.g. `meta-llama/llama-3.3-70b-instruct`) alongside provider IDs and context window tokens.
4. If harness requests candidates for a specific model via `registry.get_model_candidates("meta-llama/llama-3.3-70b-instruct")`, registry returns all matching provider instances.
$END_BODY

$START_LINKS
IMPLEMENTS: BR-5, BR-6
IMPACTS: backend/app/core/providers/registry.py
REQUIRES: GOAL_PROVIDER_DISCOVERY
$END_LINKS
$END_ARTIFACT_CASE_QUERY_MODELS

$START_ARTIFACT_CASE_CRAWL_OPENROUTER
TYPE: USE_CASE
KEYWORDS: openrouter, crawler, filtering, zero-cost, resilience

$START_CONTRACT
PURPOSE: Periodically crawl OpenRouter models endpoint and register only active zero-cost models.
DESCRIPTION: Discovery worker -> GET https://openrouter.ai/api/v1/models -> Filter pricing.prompt == "0" and pricing.completion == "0" -> Register models.
RATIONALE: OpenRouter free models fluctuate continuously; automated crawling prevents hardcoding and stale registries.
ACCEPTANCE_CRITERIA: AC-3, AC-4, AC-5, AC-7
$END_CONTRACT

$START_BODY
### Scenario Description
1. Background task or initialization invokes `OpenRouterDiscoveryService.discover_free_models()`.
2. Service dispatches HTTP GET to `https://openrouter.ai/api/v1/models`.
3. For each returned model object, service inspects `pricing.prompt` and `pricing.completion`.
4. Only models where both pricing values strictly equal `"0"` are retained; all commercial/paid models are discarded.
5. Suffix `:free` is stripped to form the `canonical_name`.
6. Discovered models are registered into `ProviderRegistry` via thread-safe async lock.
7. If upstream service responds with HTTP 429 or 500, existing cached models remain preserved.
$END_BODY

$START_LINKS
IMPLEMENTS: BR-4, BR-5
IMPACTS: backend/app/core/discovery/openrouter.py
REQUIRES: GOAL_PROVIDER_DISCOVERY
$END_LINKS
$END_ARTIFACT_CASE_CRAWL_OPENROUTER

$END_SECTION_SCENARIOS

$END_DOCUMENT
