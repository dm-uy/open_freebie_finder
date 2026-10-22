# Specification T-005: Structured Telemetry, Correlation ID Cascades, and Admin Observability

- **ID:** T-005
- **Profile:** MIXED
- **Status:** approved
- **Version:** 1.1.0
- **Roadmap Phase:** P2
- **Task ID:** T-005
- **Input RECON:** Embedded (§2)
- **Authorization:** Approved by owner on 2026-10-22

$START_DOCUMENT
PURPOSE: Establish end-to-end request observability across multi-candidate cascade failovers by assigning/propagating correlation IDs (X-Request-ID), emitting single-line structured machine-readable JSON logs for each cascade hop, recording request metrics into an in-memory ring buffer, and exposing administrative observability endpoints.
SCOPE: Ingestion/generation of X-Request-ID, propagation across all candidate attempts in CascadeRouter (route_completion and route_stream_completion), structured JSON hop logging, fail-safe circular buffer for request telemetry, and admin inspection endpoints (GET /api/admin/telemetry/recent and GET /api/admin/telemetry/stats) with master-key authentication enforcement.
KEYWORDS: correlation-id, x-request-id, cascade-telemetry, structured-logging, ring-buffer, admin-telemetry

$START_DOCUMENT_PLAN
$DOCUMENT_PLAN
GOAL [Structured Telemetry and Correlation ID Cascades] => GOAL_CORRELATION_TELEMETRY
USE_CASE [Trace Multi-Hop Failover via Correlation ID] => CASE_TRACE_CASCADE
USE_CASE [Inspect Recent Telemetry via Admin API] => CASE_ADMIN_TELEMETRY
$END_DOCUMENT_PLAN

$START_SECTION_FEATURE
$START_ARTIFACT_GOAL_CORRELATION_TELEMETRY
TYPE: GOAL
KEYWORDS: telemetry, correlation, x-request-id, admin, structured-logging

$START_CONTRACT
PURPOSE: Ensure every inference request routed through Open Freebie Finder carries an immutable correlation identifier, traces candidate attempts with latency and status breakdown, emits machine-readable JSON hop logs, and exposes telemetry for debugging and admin UI dashboard ingestion without leaking prompt contents.
DESCRIPTION: 
Open Freebie Finder handles cascading failovers across multiple upstream model candidates upon HTTP 429 or 5xx errors. Without unified request tracing, operators cannot correlate the original client request with individual upstream hops or measure latency per attempt. T-005 introduces:
1. Header processing: Read `X-Request-ID` from client request or generate a random UUIDv4; reflect this `X-Request-ID` in all proxy HTTP response headers (both success and error envelopes).
2. Structured hop logging: Every candidate attempt in `CascadeRouter.route_completion` and `CascadeRouter.route_stream_completion` emits a single-line JSON log containing `timestamp`, `request_id`, `hop_index`, `provider_id`, `model_id`, `status`, `status_code`, `duration_ms`, and `error`.
3. In-memory ring buffer: Store the last `MAX_TELEMETRY_RECORDS` (default: 500) request records in a thread-safe circular memory buffer (`TelemetryStore`) using `collections.deque(maxlen=max_records)` guarded by `asyncio.Lock`. Ingestion is fail-safe and never raises errors to disrupt client requests.
4. Admin telemetry endpoints: `GET /api/admin/telemetry/recent?limit=50` and `GET /api/admin/telemetry/stats`, protected by `Settings.proxy_master_key` when configured.
RATIONALE: Provides operational visibility for both local debugging and the forthcoming React UI dashboard (Phase P4) without introducing external heavy dependencies (like Elasticsearch or Prometheus).
$END_CONTRACT

$END_ARTIFACT_GOAL_CORRELATION_TELEMETRY
$END_SECTION_FEATURE

---

## 1. Context & Business Requirements

### BR-1 (Zero Regression on Existing Proxy Endpoints)
- Existing endpoints `GET /health`, `GET /v1/models`, and `POST /v1/chat/completions` (both standard buffered and SSE streaming) must retain 100% backward compatibility and OpenAI-compliant response formats.
- All 27 existing tests in `backend/tests` must continue to pass without regression.

### BR-2 (Correlation ID Ingestion & Response Header Reflection)
- If the incoming client request includes an `X-Request-ID` header, the proxy must use that value. If omitted, the proxy must generate a fresh `uuid.uuid4()` string.
- The `X-Request-ID` header must be returned on all HTTP responses emitted by `/v1/chat/completions`, including:
  - Successful buffered responses (`200 OK`)
  - Successful SSE streaming responses (`200 OK` with `text/event-stream`)
  - Error responses (`400 Bad Request`, `401 Unauthorized`, `404 Not Found`, `500 Internal Server Error`, `503 Service Unavailable`)
- *Note:* The proxy never returns `429 Too Many Requests` downstream because upstream 429 errors are intercepted and cascaded; if all candidates are exhausted, the proxy responds with `503 Service Unavailable`.

### BR-3 (Per-Hop Cascade Tracing in Router)
- In `CascadeRouter.route_completion` and `CascadeRouter.route_stream_completion`, the router must create an internal `RequestTrace` containing:
  - `request_id`: string correlation ID
  - `requested_model`: string (e.g. `auto:free`)
  - `stream`: bool
  - `attempts`: ordered list of candidate attempts, each recording:
    - `hop_index`: int (1-based index)
    - `provider_id`: string
    - `model_id`: string
    - `status`: string ("success" | "cooldown_skipped" | "http_error" | "stream_error")
    - `status_code`: optional int (e.g. 429, 200, 500)
    - `duration_ms`: float (measured with `time.perf_counter()`)
    - `error`: optional string
  - `resolved_candidate`: final candidate if successful, else `None`
  - `total_duration_ms`: float

### BR-4 (Fail-Safe Thread-Safe In-Memory Telemetry Buffer)
- A `TelemetryStore` singleton must maintain a bounded circular FIFO buffer of the last `max_telemetry_records` (default: 500) completed request traces using `collections.deque(maxlen=max_records)` guarded by `asyncio.Lock`.
- **Fail-safe ingestion rule:** `TelemetryStore.record_trace` must never raise an unhandled exception that disrupts client request execution. Any internal store failure must be logged as a warning, allowing the proxy completion to succeed.

### BR-5 (Admin Telemetry Observability & Authentication)
- Expose `GET /api/admin/telemetry/recent?limit=50` returning the latest traces ordered newest-first.
- Expose `GET /api/admin/telemetry/stats` returning aggregate metrics:
  - `total_requests`: int
  - `successful_requests`: int
  - `failed_requests`: int
  - `failover_count`: int (requests requiring >= 2 hops)
  - `total_cached_models`: int (total count of registered models currently in `ProviderRegistry.get_models()`)
- **Authentication rule:** Consistent with DEC-001 and `/v1/chat/completions`:
  - If `Settings.proxy_master_key` is set (non-empty), requests to `/api/admin/*` must include `Authorization: Bearer <master_key>`. Missing or invalid tokens return HTTP 401 in OpenAI error envelope.
  - If `Settings.proxy_master_key` is empty or None, requests to `/api/admin/*` are permitted without authorization (permissive development mode).

### BR-6 (Structured JSON Hop Logging)
- On every candidate hop evaluated in `CascadeRouter` (both successes and errors), the proxy must emit a structured log record formatted as a single-line JSON string containing:
  - `timestamp`: ISO 8601 UTC string
  - `request_id`: string
  - `hop_index`: int
  - `provider_id`: string
  - `model_id`: string
  - `status`: string ("success" | "cooldown_skipped" | "http_error" | "stream_error")
  - `status_code`: optional int
  - `duration_ms`: float
  - `error`: optional string

---

## 2. Input RECON

- **Recon Date:** 2026-10-22
- **HEAD Commit:** `33c9a32865071a3960d8145a122b66e0656f7a44`
- **Working Tree State:**
  - Tracked modifications:
    - `ARCHITECTURE.md`: references newly added DEC-004.
    - `HANDOFF.md`: updated to Phase P2 state.
    - `TASKS.md`: updated with Batch B-002 tasks.
  - Untracked files:
    - `docs/decisions/DEC-004-benchmark-scoring-registry.md`: owner-approved decision record governing Phase P3 benchmark registry design.
    - `notes/batch-B-001.md`: archive of completed and accepted Batch B-001.
    - `specs/T-005-structured-telemetry-and-validation.md`: current working draft.
- **Test Baseline:** 27 passed in 0.11s (`backend/tests/`).
- **Dependencies Available:** `fastapi` 0.159.1, `uvicorn` 0.42.0, `httpx` 0.28.1, `pydantic` 2.14.1, `pydantic-settings` 2.13.1, `pyyaml` 6.0.3, `pytest` 9.1.1, `pytest-asyncio` 1.4.0.
- **Existing Tracing & Telemetry Observations:**
  - `backend/app/api/v1/chat.py` does not inspect or reflect `X-Request-ID`.
  - `CascadeRouter.route_completion` and `route_stream_completion` log unstructured warnings (`logger.warning(...)`) without correlation IDs.
  - No in-memory telemetry buffer or admin telemetry routes exist.
  - `Settings` in `backend/app/config.py` does not contain `max_telemetry_records`.

---

## 3. Boundaries

### Always Do
- Always preserve OpenAI-compatible JSON responses and SSE streaming bytes for `/v1/chat/completions`.
- Always return the `X-Request-ID` in the response headers (for 200, 400, 401, 404, 500, 503).
- Always use monotonic high-resolution timers (`time.perf_counter()`) for accurate millisecond latency measurements.
- Always guard the telemetry buffer with bounded sizing (`collections.deque(maxlen=...)`) to prevent unbounded memory growth.
- Always emit hop log entries as valid single-line JSON strings to `logging.getLogger("backend.app.telemetry")`.

### Ask First
- Adding external database drivers (e.g., PostgreSQL or Redis) is forbidden; the in-memory circular buffer satisfies Phase P2 requirements.

### Never Do
- Never block or fail `/v1/chat/completions` execution if telemetry recording or logging encounters an unexpected exception.
- Never log or store raw prompt texts or completion contents in the telemetry store or log files (privacy and memory footprint protection). Only operational metadata (model IDs, latencies, tokens if provided, status codes, error messages) is retained.
- Never expose unauthenticated `/api/admin/*` endpoints when `Settings.proxy_master_key` is configured.

---

## 4. Stack & Dependencies
- **Language / Runtime:** Python 3.11+ / Python 3.15.0 (.venv).
- **Web Framework:** FastAPI, Starlette.
- **Data Validation:** Pydantic v2.
- **Logging:** Standard library `logging` with structured JSON emission.
- **Storage:** Thread-safe in-memory ring buffer (`collections.deque` with `asyncio.Lock`).
- **External Dependencies:** No new pip packages required.

---

## 5. Expected Architecture

```
Client Request
      │
      ▼
[/v1/chat/completions]
      │
      ├─► Extract or generate X-Request-ID
      │
      ▼
[CascadeRouter]
      │
      ├─► Candidate 1 ──(429)──► Log JSON Hop 1 ──► Trace Attempt 1
      ├─► Candidate 2 ──(200)──► Log JSON Hop 2 ──► Trace Attempt 2
      │
      ├─► TelemetryStore.record_trace(trace) [Fail-Safe Ring Buffer]
      │
      ▼
Client Response (Headers: X-Request-ID: ...)

Admin Request -> [/api/admin/telemetry/*] -> TelemetryStore -> JSON Response
```

---

## 6. Scope & Allowed Paths

### MAY EDIT
- `backend/app/config.py`: Add `max_telemetry_records: int = 500`.
- `backend/app/api/v1/chat.py`: Ingest `X-Request-ID`, propagate to router, return in response headers (success and error paths).
- `backend/app/core/balancer/router.py`: Accept `request_id`, trace candidate attempts in `route_completion` and `route_stream_completion`, emit structured JSON hop logs, record trace in `TelemetryStore`.
- `backend/app/core/telemetry/`: Create `models.py` (RequestTrace, CandidateAttempt, TelemetryStats) and `store.py` (`TelemetryStore` singleton).
- `backend/app/api/admin/`: Create `telemetry.py` admin router with `/recent` and `/stats`.
- `backend/app/main.py`: Mount admin router at `/api/admin`.
- `backend/tests/`: Add `test_telemetry.py` and update existing tests as necessary to verify headers.

### DO NOT TOUCH
- `backend/app/core/providers/providers.yaml`: Out-of-the-box manifests must remain unchanged.
- `docs/decisions/`: All ADRs remain binding.

---

## 7. Business Requirements to Acceptance Criteria Traceability Matrix

| Business Requirement | Acceptance Criteria | Verification Target |
|---|---|---|
| **BR-1** (Zero Regression) | **AC-1** | All 27 existing tests in `backend/tests` pass without errors |
| **BR-2** (Correlation Ingestion & Reflection) | **AC-2**, **AC-3**, **AC-4** | Custom and auto-generated `X-Request-ID` present on 200, streaming, and 401/404/503 responses |
| **BR-3** (Cascade Tracing in Router) | **AC-5** | Multi-hop cascade records ordered attempt array with status, latency, and candidate info |
| **BR-4** (Fail-Safe Ring Buffer) | **AC-8**, **AC-9** | Store enforces `max_telemetry_records` capacity eviction; store failures do not break completions |
| **BR-5** (Admin Telemetry & Auth) | **AC-7**, **AC-10** | `GET /api/admin/telemetry/recent` and `/stats` return valid payloads; master-key auth enforced |
| **BR-6** (Structured JSON Hop Logging) | **AC-6** | Logger emits valid single-line JSON with required correlation fields for each candidate hop |

---

## 8. Acceptance Criteria

- **AC-1 (Zero Regression):** All 27 existing tests in `backend/tests` pass without regression.
- **AC-2 (Client Correlation ID Reflection):** Client sending `X-Request-ID: test-custom-id-123` to `/v1/chat/completions` receives `X-Request-ID: test-custom-id-123` in the HTTP response headers.
- **AC-3 (Auto-Generated Correlation ID):** Client omitting `X-Request-ID` receives a valid UUID4 in the `X-Request-ID` HTTP response header.
- **AC-4 (Error Envelope Correlation ID):** When `/v1/chat/completions` returns an error status (e.g. 401 Unauthorized or 404 Model Not Found), the response headers still contain the `X-Request-ID`.
- **AC-5 (Cascade Hop Tracing):** When a cascade occurs (simulated upstream 429 on Candidate 1 followed by 200 on Candidate 2), the recorded trace contains exactly 2 candidate attempts with their respective durations, status codes, and error reasons.
- **AC-6 (Structured JSON Hop Logging):** For each evaluated hop, `logging.getLogger("backend.app.telemetry")` logs a single line that can be parsed as JSON containing `timestamp`, `request_id`, `hop_index`, `provider_id`, `model_id`, `status`, `duration_ms`.
- **AC-7 (Admin Telemetry Endpoints):** `GET /api/admin/telemetry/recent` returns an array of recent traces ordered newest-first. `GET /api/admin/telemetry/stats` returns `total_requests`, `successful_requests`, `failed_requests`, `failover_count`, and `total_cached_models`.
- **AC-8 (Ring Buffer Eviction):** When the number of recorded requests exceeds `max_telemetry_records`, oldest entries are silently evicted without raising memory or exceptions.
- **AC-9 (Telemetry Fail-Safe Execution):** If `TelemetryStore.record_trace` raises an unhandled exception (simulated via mock), `/v1/chat/completions` catches the error, logs a warning, and still returns the completed HTTP 200 response to the client.
- **AC-10 (Admin Master Key Authentication):** If `Settings.proxy_master_key` is set, requests to `/api/admin/telemetry/*` without `Authorization: Bearer <key>` return HTTP 401. If `proxy_master_key` is empty, requests succeed without authorization.

---

## 9. Delivery & Live Probe

### Automated Test Probe
```bash
.venv/bin/pytest backend/tests/test_telemetry.py -v
```

### Live HTTP Probes (Requires Lifespan Warmup)
*Prerequisite:* FastAPI server running with lifespan discovery warm-up (`uvicorn backend.app.main:app --port 8000`).

```bash
# 1. Dispatch chat completion with custom correlation ID
curl -i -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: probe-corr-id-001" \
  -d '{"model": "auto:free", "messages": [{"role": "user", "content": "hi"}]}'
# Expected: HTTP response headers contain X-Request-ID: probe-corr-id-001

# 2. Query recent telemetry from Admin API
curl -s http://localhost:8000/api/admin/telemetry/recent?limit=1 | jq .
# Expected: JSON array containing trace with request_id: "probe-corr-id-001"

# 3. Query telemetry stats from Admin API
curl -s http://localhost:8000/api/admin/telemetry/stats | jq .
# Expected: JSON object with total_requests >= 1 and total_cached_models >= 1
```

$START_SECTION_SCENARIOS
$START_ARTIFACT_CASE_TRACE_CASCADE
TYPE: USE_CASE
KEYWORDS: cascade, correlation, trace

$START_CONTRACT
PURPOSE: Trace multi-hop failovers across candidates under a single correlation ID.
DESCRIPTION:
1. Incoming request arrives at `/v1/chat/completions` with `X-Request-ID: hop-test-999`.
2. Router selects Candidate 1 (e.g., OpenRouter `model-A`).
3. Candidate 1 responds with HTTP 429. Attempt 1 is recorded with `status: "http_error"`, `status_code: 429`, and a single-line structured JSON hop log is emitted.
4. Router triggers Tier 2 fallback to Candidate 2 (`model-B`).
5. Candidate 2 responds with HTTP 200. Attempt 2 is recorded with `status: "success"`, `status_code: 200`, and a single-line structured JSON hop log is emitted.
6. Client receives HTTP 200 response with `X-Request-ID: hop-test-999` in response headers.
7. Telemetry record is persisted in `TelemetryStore` containing both hops and total latency.
$END_CONTRACT
$END_ARTIFACT_CASE_TRACE_CASCADE

$START_ARTIFACT_CASE_ADMIN_TELEMETRY
TYPE: USE_CASE
KEYWORDS: admin, telemetry, query

$START_CONTRACT
PURPOSE: Allow administrative query of recent requests and cascade telemetry with optional master-key protection.
DESCRIPTION:
1. Admin or React dashboard client sends `GET /api/admin/telemetry/recent?limit=10`.
2. Proxy validates `proxy_master_key` if configured.
3. `TelemetryStore` retrieves the last 10 entries from the circular memory buffer.
4. Proxy returns JSON array of request traces with hop details and timestamps.
$END_CONTRACT
$END_ARTIFACT_CASE_ADMIN_TELEMETRY
$END_SECTION_SCENARIOS

$END_DOCUMENT
