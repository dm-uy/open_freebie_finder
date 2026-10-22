# Project Operations: Open Freebie Finder

## Goal and Project Profile
Open Freebie Finder is a local/server-side smart proxy and load balancer for zero-cost LLM inference powered by free-tier models across multiple providers (OpenRouter, Groq, Google AI Studio, Nvidia NIM, etc.). It exposes an OpenAI-compatible API (`/v1/chat/completions`, `/v1/models`), transparent cascade failover upon 429/5xx errors, auto-discovery of active free models, benchmark-based model ranking, and an intuitive React web dashboard.

## Session Startup Reading Order
1. `AGENTS.md` (this file)
2. `VISION.md` (goals, scope boundaries, success criteria)
3. `ROADMAP.md` (phases, current milestone focus)
4. `HANDOFF.md` (current state, blockers, next steps)
5. `TASKS.md` (active work package)
6. `ARCHITECTURE.md` (system design, data flow diagrams)
7. `docs/decisions/` (formal architectural decisions)

## Documentation Map
* **Goals & Scope:** `VISION.md`
* **Architecture:** `ARCHITECTURE.md`
* **Roadmap & Phases:** `ROADMAP.md`
* **Active Tasks:** `TASKS.md`
* **State Handoff:** `HANDOFF.md`
* **Architectural Decisions:** `docs/decisions/`
* **Specifications:** `specs/`
* **Notes & Reports:** `notes/`
* **Process Governance:** `PROJECT-PROCESS.md`

## Records and Allowed Paths
* **Documentation & Specifications:** `AGENTS.md`, `VISION.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `TASKS.md`, `HANDOFF.md`, `docs/`, `specs/`, `notes/`.
* **Backend:** `backend/` (FastAPI, Python 3.11+)
* **Frontend:** `frontend/` (React, Vite, Tailwind CSS)
* **Configuration & Environment:** `.env.example`, `docker-compose.yml`, `Dockerfile`

## Execution and Verification Commands
* **Git Status:** `git status --short`
* **Backend Tests:** `pytest backend/tests`
* **Backend Dev Server:** `uvicorn backend.app.main:app --reload --port 8000`
* **Frontend Dev Server:** `npm run dev --prefix frontend`
* **Frontend Lint/Build:** `npm run build --prefix frontend`

## Constraints and Actions Requiring Owner Approval
* Adding real private provider API keys to repository files — strictly forbidden (use `.env`, never commit secrets).
* Modifying the agreed technology stack (Python/FastAPI + React).
* Deploying to external hosting or remote servers.
* Pushing commits to remote repositories without approval.

## Agent Operating Rules
* **Language rule:** All project documentation (`AGENTS.md`, `VISION.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `TASKS.md`, `HANDOFF.md`, `docs/`, `specs/`, `notes/`) MUST strictly be maintained in English. User communication in chat may be conducted in other languages, but all written project artifacts and documentation must remain in English.
* Restore context from repository files rather than relying on ephemeral chat history.
* Link every task to a phase in `ROADMAP.md` and core value in `VISION.md`.
* Distinguish between proposed design (`proposal`) and actual working implementation (`as-built`).
* Update only affected records during significant changes.
* Record blockers and verifications in `HANDOFF.md` prior to completing any turn.
