# Project State Handoff (HANDOFF)

## Blocked on the owner
Nothing is currently blocking. T-002 (FastAPI backend scaffold) complete and verified with pytest. Ready to proceed to task `T-003` (Declarative Provider Registry, 10 out-of-the-box manifests, and Dynamic Discovery Engine).

## State
* **Active Phase:** P1 (Core OpenAI Proxy and OpenRouter Discovery Integration).
* **Active Task:** Completed `T-001` (Documentation & Architecture) and `T-002` (FastAPI backend scaffold, config, `/health`, and test suite). Next up: `T-003` (Declarative provider schema, 10 manifests bundle, and OpenRouter discovery).
* **Completed Work:**
  * Created Python 3.15 virtualenv `.venv` and installed dependencies (`backend/requirements.txt`).
  * Built application configuration module (`backend/app/config.py`) supporting `.env` and environment variables.
  * Implemented application factory with CORS middleware and `/health` endpoint (`backend/app/main.py`).
  * Configured `pytest.ini` and verified with passing test suite (`backend/tests/test_health.py`).
  * Created `.env.example` documenting all provider keys and settings.
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
