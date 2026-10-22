# Project State Handoff (HANDOFF)

## Blocked on the owner
Nothing is currently blocking. Git repository initialized with `user.name = "dm-uy"`, MIT License added, initial project documentation complete. Ready to proceed to task `T-002` (FastAPI backend scaffold).

## State
* **Active Phase:** P1 (Core OpenAI Proxy and OpenRouter Discovery Integration).
* **Active Task:** `T-001` (process documentation, architecture design, and open-source setup under MIT) is completed. Next up: `T-002` (FastAPI backend scaffold).
* **Completed Work:**
  * Analyzed user requirements: zero-cost LLM inference via a smart load-balancing proxy with automatic discovery of free models (OpenRouter, Groq, Nvidia, Google), benchmark ranking, and a React web interface.
  * Approved technology stack: Python/FastAPI (backend) + React (frontend) + SQLite.
  * Initialized Git repository, configured local user `dm-uy`, added `.gitignore` and MIT `LICENSE`.
  * Formulated complete English documentation suite: `AGENTS.md`, `VISION.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `TASKS.md`, `HANDOFF.md`, `README.md`, and `docs/decisions/DEC-001-stack-and-architecture.md`.
* **Actual Environment State:**
  * Git: Initialized on `main` branch.
  * Local Git user: `dm-uy`.
  * Open-source license: MIT.

## Queue
* **Active Batch:** B-001
* **Next Permitted Step:** `T-002` — Create base structure for FastAPI backend (`backend/requirements.txt`, `backend/app/main.py`, initial test setup, and health check endpoint).
* **Deferred Scope:** P2 (Groq/Nvidia/Gemini), P3 (Benchmarks and Quality Pools), P4 (React Dashboard), P5 (Docker Packaging and Caching).

## Traps
* **Dynamic Model Availability:** OpenRouter frequently introduces and deprecates free models (suffix `:free`). Hardcoding model identifiers will lead to silent breakages; the dynamic discovery engine is mandatory.
* **Streaming Failover Timing:** During Server-Sent Events (`stream: true`), an upstream 429 error may occur either on initial HTTP handshake (prior to headers/body) or during the first chunk. The proxy must pre-buffer the initial upstream response before sending SSE byte chunks to the downstream client to allow transparent retries.
* **Credential Hygiene:** Never commit or hardcode upstream API keys in repository files; all provider authentication must use `.env` or local runtime configuration.
