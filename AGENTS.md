# Project Operations: Open Freebie Finder

## Goal and Project Profile
Open Freebie Finder is a local/server-side smart proxy and load balancer for zero-cost LLM inference powered by free-tier models across multiple providers (OpenRouter, Groq, Google AI Studio, Nvidia NIM, etc.). The implemented backend exposes an OpenAI-compatible text-chat subset (`/v1/chat/completions`, `/v1/models`), dynamic eligible-model discovery, bounded cascade failover, telemetry and adaptive recovery. Task-specific embeddings/rerank/decisions/speech support, benchmark ranking and the React dashboard are planned; follow TASKS/ROADMAP for actual authorization and status.

## Session Startup Reading Order
1. `AGENTS.md` (this file)
2. `PROJECT-PROCESS.md` (self-contained lightweight project/documentation process)
3. `VISION.md` (goals, scope boundaries, success criteria)
4. `ROADMAP.md` (phases, current milestone focus)
5. `HANDOFF.md` (current state, blockers, next steps)
6. `TASKS.md` (active work package)
7. `ARCHITECTURE.md` (system design, data flow diagrams)
8. Relevant `docs/decisions/`, specifications and notes.

Read `PROJECT-PROCESS.md` in full at the beginning of each new session or context-restored continuation. Consult its relevant sections before changing project records, preparing specifications or handing off work. It need not be reread before every message/tool call while its instructions remain in context. Follow this lightweight process rather than importing a full framework merely because one is installed.

## Documentation Map
* **Goals & Scope:** `VISION.md`
* **Architecture:** `ARCHITECTURE.md`
* **Roadmap & Phases:** `ROADMAP.md`
* **Active Tasks:** `TASKS.md`
* **State Handoff:** `HANDOFF.md`
* **Architectural Decisions:** `docs/decisions/`
* **Specifications:** `specs/`
* **Notes & Reports:** `notes/`
* **Process Governance:** `PROJECT-PROCESS.md` (public, self-contained English instructions).

## Records and Allowed Paths
* **Documentation & Specifications:** `AGENTS.md`, `VISION.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `TASKS.md`, `HANDOFF.md`, `docs/`, `specs/`, `notes/`.
* **Backend:** `backend/` (FastAPI, Python 3.11+)
* **Frontend:** `frontend/` (React, Vite, Tailwind CSS)
* **Operational Tools:** `scripts/` (scoped probes and maintenance utilities; each tool requires its own authorized task/specification).
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
* **Language rule:** All project documentation (`AGENTS.md`, `VISION.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `TASKS.md`, `HANDOFF.md`, `docs/`, `specs/`, `notes/`) and codebase MUST strictly be maintained in English. User communication in chat may be conducted in Russian or other languages, but all written project artifacts, specifications, and code must remain in English. (Note: `SPEC-EXAMPLE.md` remains in its original Russian form as an intentional teaching-template exception; `PROJECT-PROCESS.md` is maintained in English).
* Restore context from repository files rather than relying on ephemeral chat history.
* Link every task to a phase in `ROADMAP.md` and core value in `VISION.md`.
* Distinguish between proposed design (`proposal`) and actual working implementation (`as-built`).
* Update only affected records during significant changes.
* Record blockers and verifications in `HANDOFF.md` prior to completing any turn.
