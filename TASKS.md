# Active Work Package B-001: Initialization and Architectural Foundation

**Phase:** P1 (Core OpenAI Proxy and OpenRouter Discovery Integration)  
**Permission:** Explicit owner authorization (approved Python/FastAPI + React tech stack, request for architecture design and documentation governance under `PROJECT-PROCESS.md`).

---

## T-001 — Process Governance Documentation and Architectural Foundation
- **Status:** `done`
- **Why:** Establish structured project management adhering to `PROJECT-PROCESS.md`, ensuring any incoming agent can resume work without relying on chat history.
- **Deliverable and "Done When":** Project documentation files created in English: `AGENTS.md`, `VISION.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `TASKS.md`, `HANDOFF.md`, and `docs/decisions/DEC-001-stack-and-architecture.md`.
- **Allowed Paths:** Project root, `docs/`
- **Evidence:** Repository documentation files generated, verified, and aligned with `PROJECT-PROCESS.md`.

---

## T-002 — FastAPI Backend Scaffold and Dependency Management
- **Status:** `done`
- **Why:** Establish the Python backend runtime environment for Phase P1 (FastAPI, uvicorn, httpx, pydantic v2, pytest).
- **Deliverable and "Done When":** Directory `backend/` created, containing dependency specification (`backend/requirements.txt`), main application entrypoint `backend/app/main.py` with an active `/health` endpoint, and an executable passing `pytest` test suite.
- **Allowed Paths:** `backend/`, `pytest.ini`, `.env.example`
- **Execution and Verification:** Passed `.venv/bin/pytest backend/tests` (1 passed in 0.01s).
- **Evidence:** Tested and verified via pytest suite in commit.

---

## T-003 — Declarative Provider Registry and Dynamic Discovery Engine
- **Status:** `done`
- **Why:** Provide a flexible schema for configuring inference providers without code changes (DEC-002), ship with 10 out-of-the-box manifests covering 90%+ of free services, and dynamically discover active free models.
- **Specification:** [specs/T-003-declarative-providers-and-discovery.md](specs/T-003-declarative-providers-and-discovery.md) (Version 1.1.0)
- **Deliverable and "Done When":** Declarative schema (`providers.yaml` & Pydantic models), 10 pre-configured manifests, `ProviderRegistry` with in-memory non-blocking caching, OpenRouter discovery service (`pricing.prompt == "0" and pricing.completion == "0"`), and unit tests confirming AC-1 to AC-9.
- **Allowed Paths:** `backend/app/core/providers/`, `backend/app/core/discovery/`, `backend/tests/`
- **Execution and Verification:**
  - Automated tests: `pytest backend/tests` — 10 passed in 0.05s (AC-1..9).
  - CLI Probe: `Loaded 10 manifests` confirmed.
  - Live Probe: Discovered 20 live free models on OpenRouter (e.g. `liquid/lfm-2.5-2.6b`, `nvidia/nemotron-3.5-super-vl`).
- **Evidence:** Tested, verified, and committed with 10 passing tests.

---

## T-004 — OpenAI Proxy Endpoints and Cascade Failover Router
- **Status:** `review`
- **Why:** Ingest `/v1/chat/completions` and `/v1/models` requests from external harnesses (DeepSeek Harness, Cursor, etc.), forward them to active free-tier models with Two-Tier Failover (Tier 1: same model cross-provider; Tier 2: alternative model fallback), model name masking, and first-token stream pre-buffering (DEC-003).
- **Specification:** [specs/T-004-openai-proxy-and-failover.md](specs/T-004-openai-proxy-and-failover.md) (Version 1.1.0, Approval: approved)
- **Deliverable and "Done When":** Operational `POST /v1/chat/completions` and non-blocking `GET /v1/models`; tests simulating upstream 429 and in-stream errors confirm seamless transparent failover with canonical model name preservation (AC-1..11).
- **Allowed Paths:** `backend/app/api/v1/`, `backend/app/core/balancer/`, `backend/app/core/adapters/`, `backend/app/main.py`, `backend/app/config.py`, `.env.example`, `backend/tests/`
- **Execution and Verification:**
  - Automated tests: `pytest backend/tests` — 26 passed in 0.13s (AC-1..11).
  - Probe 3: `GET /v1/models` returns HTTP 200 with `auto:free` in-memory without remote calls.
  - Probe 4: `POST /v1/chat/completions` with unknown model returns HTTP 404 in standard OpenAI error envelope.
  - Debug fixes: strictly pre-buffers until non-empty `delta.content` is received (protecting against in-stream 429 after role-only chunks); monotonic clock cooldowns; constant-time auth check; max 3 failover attempts limit.
- **Evidence:** 26 passing tests in `backend/tests`. Awaiting owner resolution on live probe vs ASGI closure for P1.
