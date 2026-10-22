# Project State Handoff (HANDOFF)

## Blocked on the owner
Nothing is blocking. T-003 is verified and complete. Ready to proceed to task `T-004` (OpenAI Proxy Endpoints, Two-Tier Cascade Failover Router, and Streaming SSE Pre-buffering).

## State
* **Active Phase:** P1 (Core OpenAI Proxy and OpenRouter Discovery Integration).
* **Active Task:** Completed `T-001` (Docs & Architecture), `T-002` (FastAPI backend scaffold), and `T-003` (Declarative Provider Registry and Dynamic Discovery Engine). Next up: `T-004` (OpenAI Proxy Endpoints & Failover Router).
* **Completed Work:**
  * Implemented Pydantic v2 schemas for declarative providers (`backend/app/core/providers/models.py`).
  * Created `backend/app/core/providers/providers.yaml` with 10 default manifests covering 90%+ free services.
  * Implemented `ProviderRegistry` with thread-safe `asyncio.Lock` in-memory cache and non-blocking lookups.
  * Implemented `OpenRouterDiscoveryService` extracting only models with `pricing.prompt == "0" and pricing.completion == "0"`, stripping `:free` to canonical names, and safely extracting context window.
  * Passed all 10 tests in `backend/tests` (0.05s).
  * Executed Live Probe confirming discovery of 20 live zero-cost models from OpenRouter.
* **Actual Environment State:**
  * Git: `main` branch, HEAD `92d7c56` (prior to refinement commit).
  * Local Git user: `dm-uy`.
  * Open-source license: MIT.
  * Tests: 12 passed in 0.07s.

## Queue
* **Active Batch:** B-001
* **Next Permitted Step:** `T-004` — Prepare specification and implement OpenAI proxy endpoints (`/v1/chat/completions` and `/v1/models`), Two-Tier Failover, First-Token stream pre-buffering, and synthetic alias `auto:free`.
* **Deferred Scope:** P2 (Groq/Nvidia live activation & circuit breaker), P3 (Benchmarks & quality pools), P4 (React UI), P5 (Docker).

## Traps
* **Dynamic Model Availability:** OpenRouter frequently introduces and deprecates free models (suffix `:free`). Hardcoding model identifiers will lead to silent breakages; the dynamic discovery engine is mandatory.
* **Streaming Failover Timing:** During Server-Sent Events (`stream: true`), an upstream 429 error may occur either on initial HTTP handshake (prior to headers/body) or during the first chunk. The proxy must pre-buffer the initial upstream response before sending SSE byte chunks to the downstream client to allow transparent retries.
* **Credential Hygiene:** Never commit or hardcode upstream API keys in repository files; all provider authentication must use `.env` or local runtime configuration.
