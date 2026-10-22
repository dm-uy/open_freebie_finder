# Project State Handoff (HANDOFF)

## Blocked on the owner
Nothing is currently blocking. DEC-003 (Canonical Model Mapping, Credential Encapsulation, and Harness Interoperability) documented and committed. Ready to execute `T-003` (Declarative Provider Registry, 10-provider manifests bundle, and Dynamic Discovery Engine).

## State
* **Active Phase:** P1 (Core OpenAI Proxy and OpenRouter Discovery Integration).
* **Active Task:** Completed `T-001` (Docs & Architecture) and `T-002` (FastAPI backend scaffold). Next up: `T-003` (Declarative provider schema, 10 manifests bundle, and OpenRouter discovery).
* **Completed Work:**
  * Created Python 3.15 virtualenv `.venv` and installed dependencies (`backend/requirements.txt`).
  * Built application configuration module (`backend/app/config.py`) supporting `.env` and environment variables.
  * Implemented application factory with CORS middleware and `/health` endpoint (`backend/app/main.py`).
  * Configured `pytest.ini` and verified with passing test suite (`backend/tests/test_health.py`).
  * Created `.env.example` documenting all provider keys and settings.
  * Recorded DEC-003 specifying DeepSeek Harness interop, non-blocking `/v1/models`, upstream credential encapsulation, canonical model masking, two-tier failover, and superposition brainstorming protocol.
* **Actual Environment State:**
  * Git: Initialized on `main` branch.
  * Local Git user: `dm-uy`.
  * Open-source license: MIT.
  * Tests: 1 passed in 0.01s.

## Queue
* **Active Batch:** B-001
* **Next Permitted Step:** `T-003` — Declarative provider models, 10 built-in provider manifests (`providers.yaml`), `GenericOpenAIProviderAdapter`, OpenRouter discovery service, and unit tests.
* **Deferred Scope:** P2 (Groq/Nvidia live validation & circuit breaker), P3 (Benchmarks & quality pools), P4 (React UI), P5 (Docker).

## Traps
* **Dynamic Model Availability:** OpenRouter frequently introduces and deprecates free models (suffix `:free`). Hardcoding model identifiers will lead to silent breakages; the dynamic discovery engine is mandatory.
* **Streaming Failover Timing:** During Server-Sent Events (`stream: true`), an upstream 429 error may occur either on initial HTTP handshake (prior to headers/body) or during the first chunk. The proxy must pre-buffer the initial upstream response before sending SSE byte chunks to the downstream client to allow transparent retries.
* **Credential Hygiene:** Never commit or hardcode upstream API keys in repository files; all provider authentication must use `.env` or local runtime configuration.
