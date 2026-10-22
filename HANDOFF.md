# Project State Handoff (HANDOFF)

## Blocked on the owner
Owner review of Debug-fixed T-005 implementation (BUG_REPORT findings resolved).

## State
* **Active Phase:** P2 (Adaptive Circuit Breaker, Cross-Provider Cascade, Structured Telemetry, and Validation API) — active.
* **Active Work Package:** B-002 (B-001 archived in `notes/batch-B-001.md`).
* **Active Task:** `T-005` (Structured Request Telemetry and Correlation ID Cascades) — Debug-fixed, in `review`.
* **Completed Work:**
  * Configured `max_telemetry_records: int = 500` in `backend/app/config.py`.
  * Built thread-safe bounded in-memory circular buffer `TelemetryStore` in `backend/app/core/telemetry/`.
  * Implemented structured JSON hop logging (`backend.app.telemetry`) and trace recording across multi-candidate failovers in `CascadeRouter`.
  * Implemented client correlation ID ingestion (`X-Request-ID`) and response reflection across all HTTP responses (200/SSE/400/401/404/500/503) in `backend/app/api/v1/chat.py`.
  * Implemented admin telemetry endpoints with master-key protection in `backend/app/api/admin/telemetry.py`.
  * **Debug fixes (BUG_REPORT):**
    * Added `_record_trace_safely()` wrapper around all 5 `record_trace` call sites in `router.py` (AC-9).
    * Rewrote `test_telemetry_fail_safe_execution` to use real router + mocked upstream + failing store (no longer vacuous).
    * Added `_sanitize_error()` to strip raw upstream response bodies from telemetry traces and hop logs (privacy, Never Do).
    * Removed dead `get_all_models()` alias from `registry.py` (out-of-scope, corrected spec reference).
* **Actual Environment State:**
  * Git: `main` branch, uncommitted changes (pending review).
  * Local Git user: `dm-uy`.
  * Open-source license: MIT.

## Queue
* **Active Batch:** B-002 (Phase P2: T-005 in review, T-006 Provider Validation API, T-007 Multi-provider live activation, T-008 Provider Onboarding Agent).
* **Next Permitted Step:** Owner acceptance of T-005 debug fixes; then author specification for `T-006`.
* **Deferred Scope:** P3 (Benchmarks & quality pools), P4 (React UI), P5 (Docker & releases).

## Traps
* **Dynamic Model Availability:** OpenRouter frequently introduces and deprecates free models (suffix `:free`). Hardcoding model identifiers will lead to silent breakages; the dynamic discovery engine is mandatory.
* **Streaming Failover Timing:** During Server-Sent Events (`stream: true`), an upstream 429 error may occur either on initial HTTP handshake (prior to headers/body) or during the first chunk. The proxy must pre-buffer the initial upstream response before sending SSE byte chunks to the downstream client to allow transparent retries.
* **Credential Hygiene:** Never commit or hardcode upstream API keys in repository files; all provider authentication must use `.env` or local runtime configuration.
* **Correlation ID Propagation:** For multi-candidate failover hops, the incoming client `X-Request-ID` (or generated UUID) must be propagated through all candidate attempts so operators can trace the complete cascade trajectory in logs and admin telemetry.
* **Telemetry Fail-Safety:** `_record_trace_safely` in `CascadeRouter` is the sole enforcement of BR-4/AC-9. Future telemetry write points must use this wrapper, never bare `await store.record_trace()`.
