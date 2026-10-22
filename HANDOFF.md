# Project State Handoff (HANDOFF)

## Blocked on the owner
Awaiting review and approval of specification `specs/T-004-openai-proxy-and-failover.md` (v1.0.0) to proceed with implementation of task T-004.

## State
* **Active Phase:** P1 (Core OpenAI Proxy and OpenRouter Discovery Integration).
* **Active Task:** Completed `T-001` (Docs & Architecture), `T-002` (FastAPI backend scaffold), and `T-003` (Declarative Provider Registry and Discovery Engine). Prepared specification `specs/T-004-openai-proxy-and-failover.md` (v1.0.0, Approval: pending) for task `T-004`.
* **Completed Work:**
  * Resolved all review findings from T-003 (purging empty models, explicit exceptions, float context, clean HANDOFF, 12 passing tests).
  * Authored complete specification for T-004 [specs/T-004-openai-proxy-and-failover.md](specs/T-004-openai-proxy-and-failover.md) adhering to all Section 4 requirements (MIXED profile, Input RECON at commit `db46b03`, BR-1..6, Boundaries, Expected Architecture, Scope MAY EDIT/DO NOT TOUCH, AC-1..10, Traceability Matrix, Delivery Probes, Scenarios for DeepSeek Harness, failover, and streaming pre-buffer).
* **Actual Environment State:**
  * Git: `main` branch, HEAD `db46b03` (prior to T-004 spec commit).
  * Local Git user: `dm-uy`.
  * Open-source license: MIT.
  * Tests: 12 passed in 0.06s.

## Queue
* **Active Batch:** B-001
* **Next Permitted Step:** `T-004` — Implementation of OpenAI proxy endpoints (`/v1/chat/completions` and `/v1/models`), CascadeRouter with Two-Tier Failover, and streaming pre-buffering.
* **Deferred Scope:** P2 (Groq/Nvidia live activation & circuit breaker), P3 (Benchmarks & quality pools), P4 (React UI), P5 (Docker).

## Traps
* **Dynamic Model Availability:** OpenRouter frequently introduces and deprecates free models (suffix `:free`). Hardcoding model identifiers will lead to silent breakages; the dynamic discovery engine is mandatory.
* **Streaming Failover Timing:** During Server-Sent Events (`stream: true`), an upstream 429 error may occur either on initial HTTP handshake (prior to headers/body) or during the first chunk. The proxy must pre-buffer the initial upstream response before sending SSE byte chunks to the downstream client to allow transparent retries.
* **Credential Hygiene:** Never commit or hardcode upstream API keys in repository files; all provider authentication must use `.env` or local runtime configuration.
