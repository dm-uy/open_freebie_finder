# Project State Handoff (HANDOFF)

## Blocked on the owner
None. Phase P1 is completed, verified on real socket (see `notes/T-004-live-probe.md`), and closed. Ready to begin Phase P2 scoping.

## State
* **Active Phase:** P2 (Adaptive Circuit Breaker, Cross-Provider Cascade, Structured Telemetry, and Validation API) — active, preparing Batch B-002.
* **Active Task:** None (Batch B-001 completed). Next task to be specified: `T-005` (Structured Telemetry & Correlation IDs).
* **Completed Work:**
  * **P1 Complete:** Operational `/v1/chat/completions` (buffered + SSE streaming) and `/v1/models` proxy.
  * Declarative provider registry (`providers.yaml` with 10 manifests) and dynamic OpenRouter free-tier discovery crawler wired into FastAPI lifespan.
  * Two-tier cascade failover with canonical model masking (`auto:free`) and first-token stream pre-buffering.
  * Real-socket live probe verified on `localhost:8000` (live OpenRouter completion, 21 models served from cache, 47 SSE chunks).
  * 27 automated unit and integration tests passing (`pytest backend/tests`).
* **Actual Environment State:**
  * Git: `main` branch.
  * Local Git user: `dm-uy`.
  * Open-source license: MIT.
  * Tests: 27 passed in 0.12s.

## Queue
* **Active Batch:** B-002 (Phase P2: T-005 Telemetry & Correlation ID, T-006 Provider Validation API, T-007 Multi-provider live activation, T-008 Provider Onboarding Agent).
* **Next Permitted Step:** Author specification `specs/T-005-structured-telemetry-and-validation.md` according to `PROJECT-PROCESS.md` rules.
* **Deferred Scope:** P3 (Benchmarks & quality pools), P4 (React UI), P5 (Docker & releases).

## Traps
* **Dynamic Model Availability:** OpenRouter frequently introduces and deprecates free models (suffix `:free`). Hardcoding model identifiers will lead to silent breakages; the dynamic discovery engine is mandatory.
* **Streaming Failover Timing:** During Server-Sent Events (`stream: true`), an upstream 429 error may occur either on initial HTTP handshake (prior to headers/body) or during the first chunk. The proxy must pre-buffer the initial upstream response before sending SSE byte chunks to the downstream client to allow transparent retries.
* **Credential Hygiene:** Never commit or hardcode upstream API keys in repository files; all provider authentication must use `.env` or local runtime configuration.
* **Correlation ID Propagation:** For multi-candidate failover hops, the incoming client `X-Request-ID` (or generated UUID) must be propagated through all candidate attempts so operators can trace the complete cascade trajectory in logs and admin telemetry.
