# Project State Handoff (HANDOFF)

## Blocked on the owner
Awaiting review and approval of specification `specs/T-003-declarative-providers-and-discovery.md` to proceed with code generation and implementation for task T-003.

## State
* **Active Phase:** P1 (Core OpenAI Proxy and OpenRouter Discovery Integration).
* **Active Task:** Completed `T-001` (Docs & Architecture) and `T-002` (FastAPI backend scaffold). Prepared specification `specs/T-003-declarative-providers-and-discovery.md` (Approval: pending) for task `T-003`.
* **Completed Work:**
  * Updated `PROJECT-PROCESS.md` with the feature specification protocol and added `SPEC-EXAMPLE.md`.
  * Authored complete formal specification [specs/T-003-declarative-providers-and-discovery.md](specs/T-003-declarative-providers-and-discovery.md) adhering to all Section 4 requirements (MIXED profile, Input RECON, BR-1..6, Boundaries, Expected Architecture, Scope MAY EDIT/DO NOT TOUCH, AC-1..8, Delivery/Live Probe, Risks/Deficiencies).
* **Actual Environment State:**
  * Git: Clean on `main` branch (HEAD: `cb75501`).
  * Tests: 1 passed in 0.01s.

## Queue
* **Active Batch:** B-001
* **Next Permitted Step:** `T-003` — Declarative provider models, 10 built-in provider manifests (`providers.yaml`), `GenericOpenAIProviderAdapter`, OpenRouter discovery service, and unit tests.
* **Deferred Scope:** P2 (Groq/Nvidia live validation & circuit breaker), P3 (Benchmarks & quality pools), P4 (React UI), P5 (Docker).

## Traps
* **Dynamic Model Availability:** OpenRouter frequently introduces and deprecates free models (suffix `:free`). Hardcoding model identifiers will lead to silent breakages; the dynamic discovery engine is mandatory.
* **Streaming Failover Timing:** During Server-Sent Events (`stream: true`), an upstream 429 error may occur either on initial HTTP handshake (prior to headers/body) or during the first chunk. The proxy must pre-buffer the initial upstream response before sending SSE byte chunks to the downstream client to allow transparent retries.
* **Credential Hygiene:** Never commit or hardcode upstream API keys in repository files; all provider authentication must use `.env` or local runtime configuration.
