# Project State Handoff (HANDOFF)

## Blocked on the owner
Decision on Phase P1 closure criterion:
- Option A: Owner provides `OPENROUTER_API_KEY` in `.env` to execute live completion probe against a live free model.
- Option B: Owner formally approves closing P1 based on ASGI-level test verification (26 automated unit and integration tests passing).

## State
* **Active Phase:** P1 (Core OpenAI Proxy, Declarative Provider Registry, and OpenRouter Integration) — active, code complete.
* **Active Task:** `T-004` (OpenAI Proxy Endpoints and Cascade Failover Router) is in `review`.
* **Completed Work:**
  * Fixed pre-buffering defect: stream strictly pre-buffers until non-empty `delta.content` is received (protecting against post-role in-stream 429 errors).
  * Switched cooldown tracking to `time.monotonic()`.
  * Added constant-time `hmac.compare_digest` for master key auth.
  * Added `ChatMessage.content: Any` to accept multimodal message payloads.
  * Moved correlation ID request logging to Phase P2 roadmap deliverable.
  * Added unit tests for role-first in-stream failover and max 3 attempts limit (26 passing tests in `backend/tests`).
* **Actual Environment State:**
  * Git: `main` branch.
  * Local Git user: `dm-uy`.
  * Open-source license: MIT.
  * Tests: 26 passed in 0.13s.

## Queue
* **Active Batch:** B-001 (T-001, T-002, T-003 done, T-004 in review).
* **Next Permitted Step:** Owner decision on Option A vs B for P1 completion, then scope Phase P2 work package.
* **Deferred Scope:** P2 (Groq/Nvidia live activation, correlation-ID telemetry, and circuit breaker), P3 (Benchmarks & quality pools), P4 (React UI), P5 (Docker).

## Traps
* **Dynamic Model Availability:** OpenRouter frequently introduces and deprecates free models (suffix `:free`). Hardcoding model identifiers will lead to silent breakages; the dynamic discovery engine is mandatory.
* **Streaming Failover Timing:** During Server-Sent Events (`stream: true`), an upstream 429 error may occur either on initial HTTP handshake (prior to headers/body) or during the first chunk. The proxy must pre-buffer the initial upstream response before sending SSE byte chunks to the downstream client to allow transparent retries.
* **Credential Hygiene:** Never commit or hardcode upstream API keys in repository files; all provider authentication must use `.env` or local runtime configuration.
