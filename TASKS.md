# Active Work Package B-002: Provider Validation, Cross-Provider Cascade, and Structured Telemetry

**Phase:** P2 (Provider Validation API, Adaptive Circuit Breaker, Structured Telemetry, and Onboarding Agent)  
**Status:** Active  
**History Archive:** Previous work package B-001 archived in [notes/batch-B-001.md](notes/batch-B-001.md).  
**Permission:** Authorized transition to Phase P2 following verified completion of Phase P1 (2026-10-22).

---

## T-005 — Structured Request Telemetry and Correlation ID Cascades
- **Status:** `review`
- **Why:** Every inference request entering `/v1/chat/completions` must carry a traceable request correlation ID (`X-Request-ID` header or generated UUID) across all cascade failover hops, recording candidate attempt sequence, latency per candidate, failure reasons, and synthetic usage.
- **Specification:** [specs/T-005-structured-telemetry-and-validation.md](specs/T-005-structured-telemetry-and-validation.md) (Version 1.1.0, Approval: approved by owner on 2026-10-22)
- **Deliverable and "Done When":** Incoming requests receive or generate an `X-Request-ID` header; logs emit structured JSON with correlation IDs linking all failover hops; completed and failed request telemetry is recorded for in-memory admin queries (`GET /api/admin/telemetry/recent`, `GET /api/admin/telemetry/stats`).
- **Allowed Paths:** `backend/app/config.py`, `backend/app/api/`, `backend/app/core/telemetry/`, `backend/app/core/balancer/`, `backend/app/main.py`, `backend/tests/`
- **Execution and Verification:**
  - Automated tests: `pytest backend/tests` — 37 passed in 0.25s (AC-1..10).
  - AC-1: Zero regression confirmed across all existing 27 test cases.
  - AC-2, AC-3: Custom client and auto-generated `X-Request-ID` headers verified.
  - AC-4: Error envelopes (401, 404) confirmed to reflect `X-Request-ID`.
  - AC-5: Multi-hop cascade test verifies 2 attempts recorded with respective latencies and error descriptions.
  - AC-6: Structured single-line JSON log emission verified for `backend.app.telemetry` logger.
  - AC-7: `GET /api/admin/telemetry/recent` and `/stats` return structured traces and metrics.
  - AC-8: `TelemetryStore` circular buffer bounds memory and evicts oldest traces.
  - AC-9: Telemetry store exceptions fail safely without breaking completions.
  - AC-10: Master-key authorization enforced for `/api/admin/telemetry/*`.
- **Evidence:** 37 passing unit/integration tests in `backend/tests/test_telemetry.py` and existing suites.

---

## T-006 — Provider Validation Admin API
- **Status:** `todo`
- **Why:** Enable operators and the React dashboard to validate new or existing provider credentials without restarting the service or manually inspecting logs.
- **Specification:** To be drafted following T-005.
- **Deliverable and "Done When":** `POST /api/admin/providers/validate` accepts a provider manifest and optional test key, validates connectivity, parses available models, performs an in-band micro-completion test, and returns structured diagnostics.
- **Allowed Paths:** `backend/app/api/admin/`, `backend/app/core/providers/`, `backend/tests/`
- **Dependencies:** T-003, T-005.

---

## T-007 — Heterogeneous Cross-Provider Cascade Activation
- **Status:** `todo`
- **Why:** Deliver true resilience against single-provider quota exhaustion by enabling cross-provider failovers (e.g. OpenRouter -> Groq -> Google Gemini -> Cerebras) for shared models (e.g., Llama 3, Mistral) and backup candidates.
- **Specification:** To be drafted in Phase P2.
- **Deliverable and "Done When":** Adapters verify and route live requests to Groq, Google AI Studio (Gemini), Nvidia NIM, and Cerebras when keys are configured; automated test verifies cross-provider failover sequence.
- **Allowed Paths:** `backend/app/core/adapters/`, `backend/app/core/balancer/`, `backend/tests/`
- **Dependencies:** T-004, T-006.

---

## T-008 — Automated Provider Onboarding Agent Prototype
- **Status:** `todo`
- **Why:** Accelerate zero-cost provider expansion by taking arbitrary provider documentation text / endpoints and automatically synthesizing valid YAML manifests for `providers.yaml`.
- **Specification:** To be drafted in Phase P2.
- **Deliverable and "Done When":** Endpoint `POST /api/admin/providers/auto-discover` processes provider docs and emits a validated `ProviderManifest` ready for registry inclusion.
- **Allowed Paths:** `backend/app/core/onboarding/`, `backend/app/api/admin/`, `backend/tests/`
- **Dependencies:** T-003, T-006.
