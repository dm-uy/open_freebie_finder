# Project State Handoff (HANDOFF)

## Blocked on the owner
Awaiting review and approval of updated specification `specs/T-003-declarative-providers-and-discovery.md` (v1.1.0 addressing all review points) to proceed with implementation of task T-003.

## State
* **Active Phase:** P1 (Core OpenAI Proxy and OpenRouter Discovery Integration).
* **Active Task:** Completed `T-001` (Docs & Architecture) and `T-002` (FastAPI backend scaffold). Prepared updated specification `specs/T-003-declarative-providers-and-discovery.md` (v1.1.0, Approval: pending) for task `T-003`.
* **Completed Work:**
  * Updated `PROJECT-PROCESS.md` with the feature specification protocol and added `SPEC-EXAMPLE.md`.
  * Addressed all 10 review findings: added missing USE_CASE artifacts (`CASE_QUERY_MODELS`, `CASE_CRAWL_OPENROUTER`), added mandatory Stack / Dependencies section, updated and dated Input RECON to commit `99bd025` (2026-10-22), aligned Delivery Probe contracts with `get_registry()` and `get_manifests()`, standardized manifest filename to `providers.yaml`, defined `filter_expression` semantics, resolved Cloudflare `account_id` via `Settings`, added Traceability Matrix (BR -> AC -> Test), added `AC-9` for candidate lookup, and added optional live OpenRouter probe.
* **Actual Environment State:**
  * Git: Clean working tree.
  * Tests: 1 passed in 0.01s.

## Queue
* **Active Batch:** B-001
* **Next Permitted Step:** `T-003` — Declarative provider models, 10 built-in provider manifests (`providers.yaml`), `GenericOpenAIProviderAdapter`, OpenRouter discovery service, and unit tests.
* **Deferred Scope:** P2 (Groq/Nvidia live validation & circuit breaker), P3 (Benchmarks & quality pools), P4 (React UI), P5 (Docker).

## Traps
* **Dynamic Model Availability:** OpenRouter frequently introduces and deprecates free models (suffix `:free`). Hardcoding model identifiers will lead to silent breakages; the dynamic discovery engine is mandatory.
* **Streaming Failover Timing:** During Server-Sent Events (`stream: true`), an upstream 429 error may occur either on initial HTTP handshake (prior to headers/body) or during the first chunk. The proxy must pre-buffer the initial upstream response before sending SSE byte chunks to the downstream client to allow transparent retries.
* **Credential Hygiene:** Never commit or hardcode upstream API keys in repository files; all provider authentication must use `.env` or local runtime configuration.
