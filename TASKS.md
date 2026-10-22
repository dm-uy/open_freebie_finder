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
- **Status:** `todo`
- **Why:** Provide a flexible schema for configuring inference providers without code changes (DEC-002), ship with 10 out-of-the-box manifests covering 90%+ of free services, and dynamically discover active free models.
- **Specification:** [specs/T-003-declarative-providers-and-discovery.md](specs/T-003-declarative-providers-and-discovery.md) (Version 1.1.0)
- **Deliverable and "Done When":** Declarative schema (`providers.yaml` & Pydantic models), 10 pre-configured manifests, `ProviderRegistry` with in-memory non-blocking caching, OpenRouter discovery service (`pricing.prompt == "0" and pricing.completion == "0"`), and unit tests confirming AC-1 to AC-9.
- **Allowed Paths:** `backend/app/core/providers/`, `backend/app/core/discovery/`, `backend/tests/`

---

## T-004 — OpenAI Proxy Endpoints and Cascade Failover Router
- **Status:** `todo`
- **Why:** Ingest `/v1/chat/completions` and `/v1/models` requests from external harnesses (DeepSeek Harness, Cursor, etc.), forward them to active free-tier models with Two-Tier Failover (Tier 1: same model cross-provider; Tier 2: alternative model fallback), model name masking, and first-token stream pre-buffering (DEC-003).
- **Deliverable and "Done When":** Operational `POST /v1/chat/completions` and non-blocking `GET /v1/models`; tests simulating upstream 429 and in-stream errors confirm seamless transparent failover with canonical model name preservation.
- **Allowed Paths:** `backend/app/api/v1/`, `backend/app/core/balancer/`, `backend/tests/`
