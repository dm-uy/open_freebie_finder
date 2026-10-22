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
- **Status:** `todo`
- **Why:** Establish the Python backend runtime environment for Phase P1 (FastAPI, uvicorn, httpx, pydantic v2, pytest).
- **Deliverable and "Done When":** Directory `backend/` created, containing dependency specification (`backend/pyproject.toml` or `backend/requirements.txt`), main application entrypoint `backend/app/main.py` with an active `/health` endpoint, and an executable passing `pytest` test suite.
- **Allowed Paths:** `backend/`
- **Execution and Verification:** Run `pytest backend/tests` and verify `curl http://localhost:8000/health`.

---

## T-003 — OpenRouter Free Model Discovery Engine
- **Status:** `todo`
- **Why:** Dynamically discover active free models on OpenRouter (`pricing.prompt == 0 and pricing.completion == 0`), extracting token limits and metadata without hardcoded model identifiers.
- **Deliverable and "Done When":** Service implementation in `backend/app/core/discovery/openrouter.py`, fully covered by unit tests using mocked OpenRouter API responses.
- **Allowed Paths:** `backend/app/core/discovery/`, `backend/tests/`

---

## T-004 — OpenAI Proxy Endpoints and Cascade Failover Router
- **Status:** `todo`
- **Why:** Ingest `/v1/chat/completions` requests, forward them to active free-tier models, and execute transparent cascade failover upon receiving `429 Too Many Requests` or `5xx` errors (buffered and SSE streaming).
- **Deliverable and "Done When":** Operational `POST /v1/chat/completions` handling model alias `auto:free`; unit and integration tests simulating upstream 429 errors confirm seamless transparent failover with zero errors surfaced to the client.
- **Allowed Paths:** `backend/app/api/v1/`, `backend/app/core/balancer/`, `backend/tests/`
