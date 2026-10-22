# DEC-001: Technology Stack and Architecture Pattern Selection

## Context and Problem
The project requires building a lightweight, intelligent proxy and load balancer for zero-cost LLM inference across multiple cloud providers (OpenRouter, Groq, Google AI Studio, Nvidia NIM). The system must support transparent cascade failover upon receiving `429 Too Many Requests` or `5xx` errors, failover-safe response streaming, benchmark scoring, and an intuitive web management dashboard.
An optimal backend runtime, frontend framework, communication protocol, and persistence mechanism must be selected to balance velocity, ecosystem alignment, and operational simplicity.

## Considered Options

### Backend Runtime & Framework:
1. **Python / FastAPI + httpx (Selected)**:
   * *Pros:* Native fit for the modern AI/LLM ecosystem, rich asynchronous I/O capabilities (`asyncio`, `httpx`), robust payload validation with Pydantic v2, streamlined integration with Python-based AI benchmark datasets, and strong developer familiarity.
   * *Cons:* Slightly higher memory footprint compared to compiled languages like Go or Rust, but well within lightweight container limits (50–100MB).
2. **Node.js / TypeScript (Bun / Hono / Fastify)**:
   * *Pros:* Excellent streaming throughput, minimal runtime footprint.
   * *Cons:* More cumbersome integration with Python-centric AI evaluation tooling and benchmark data pipelines.
3. **Go**:
   * *Pros:* Ultra-low memory usage, native concurrency, single static binary.
   * *Cons:* Slower initial prototyping speed and verbose handling of heterogeneously structured, evolving provider JSON schemas.

### Frontend Framework:
1. **React + Vite + Tailwind CSS (Selected)**:
   * *Pros:* Rich component ecosystem (Lucide icons, data tables, latency graphs), lightning-fast Vite build times, and the capability to serve compiled production static assets directly from FastAPI.
2. **Server-Side Rendered HTML (Jinja2 / HTMX)**:
   * *Pros:* No separate frontend compilation pipeline.
   * *Cons:* Suboptimal for real-time interactive dashboards requiring live SSE request inspectors and drag-and-drop pool priority organizers.

### Communication Protocol:
1. **OpenAI Chat Completions API (`/v1/chat/completions`) (Selected)**:
   * De-facto industry standard. Any existing client application (OpenAI SDK, LangChain, Cursor, LibreChat) integrates immediately by altering `OPENAI_BASE_URL`.

### Persistence Store:
1. **SQLite (aiosqlite) (Selected)**:
   * Requires no external database daemon (unlike PostgreSQL or Redis), stores data locally in a single file, and delivers zero-configuration deployment in self-contained Docker environments.

## Decision
1. Implement the backend in **Python 3.11+ / FastAPI** using the asynchronous `httpx` HTTP client.
2. Implement the frontend dashboard as a **React (Vite) + Tailwind CSS** Single Page Application.
3. Expose an external API strictly adhering to the standard OpenAI `/v1/chat/completions` and `/v1/models` specifications.
4. Utilize embedded **SQLite** for storing local configuration, telemetry, request logs, and cooldown states.

## Consequences
* Guarantees 100% plug-and-play drop-in compatibility with standard AI tooling, libraries, and IDEs.
* Enables dual execution workflows: developer mode (two local concurrent dev servers) and standalone production mode (FastAPI serving compiled React SPA static files from a single container).
