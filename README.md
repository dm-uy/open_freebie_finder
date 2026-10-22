# Open Freebie Finder 🎯

> **Zero-cost, smart LLM inference proxy and load balancer powered by free-tier models.**

Open Freebie Finder is a lightweight proxy server designed for developers, staging environments, and prototype validation. It aggregates active free-tier AI models across multiple providers (OpenRouter, Groq, Google AI Studio, Nvidia NIM), exposes a standard **OpenAI-compatible API**, and automatically routes requests with seamless cascade failover upon rate limits (`429`) or server errors (`5xx`).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Key Features

- 🔄 **Standard OpenAI Interface:** Drop-in replacement for `https://api.openai.com/v1` (`/v1/chat/completions`, `/v1/models`). Works instantly with Cursor, Continue, LangChain, LlamaIndex, or the OpenAI SDK.
- ⚡ **Auto-Discovery of Free Models:** Automatically discovers available free models from connected providers (e.g. OpenRouter `:free` models) without manual configuration.
- 🛡️ **Cascade Failover & Circuit Breaker:** When a free model returns `429 Too Many Requests` or `5xx`, the proxy transparently reroutes the exact request to the next available model in the queue without surfacing errors to the client.
- 🌊 **Streaming Safe:** First-chunk pre-buffering ensures failover can occur even when SSE streaming is requested.
- 🎯 **Smart Virtual Models:** Use aliases like `auto:free`, `auto:fast`, or `auto:code` to dynamically pick the best performing active model.
- 📊 **Web Dashboard (React):** Real-time monitoring of model statuses, response latency, token usage, and calculated cost savings.
- 🆓 **100% Free & Open Source:** Licensed under the MIT License.

---

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, httpx, aiosqlite, Pydantic v2
- **Frontend:** React, Vite, Tailwind CSS, Lucide icons
- **Database:** SQLite (embedded, zero-configuration)
- **Deployment:** Docker / Docker Compose

---

## Project Documentation

Governance and technical architecture follow the process described in [PROJECT-PROCESS.md](PROJECT-PROCESS.md):

- [AGENTS.md](AGENTS.md) — Operational instructions, commands, and rules
- [VISION.md](VISION.md) — Product vision, scope, and success criteria
- [ARCHITECTURE.md](ARCHITECTURE.md) — System design, contracts, and data flows
- [ROADMAP.md](ROADMAP.md) — Development phases and milestone tracking
- [TASKS.md](TASKS.md) — Active task packages and deliverables
- [HANDOFF.md](HANDOFF.md) — Session state and handover protocol
- [docs/decisions/](docs/decisions/) — Architecture Decision Records (ADRs)

---

## License

This project is licensed under the [MIT License](LICENSE).
