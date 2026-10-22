# Project Roadmap (ROADMAP)

**Goal:** Deliver a fully featured, OpenAI-compatible smart proxy for free-tier LLM models with dynamic provider discovery, transparent cascade failover, benchmark-based routing, and a modern React web dashboard (see details in [VISION.md](VISION.md)).

---

### P1 — Core OpenAI Proxy, Declarative Provider Registry, and OpenRouter Integration
* **Deliverable:** A functional FastAPI service exposing `/v1/chat/completions` (supporting standard buffered and SSE streaming responses), a declarative provider schema (`providers.yaml`), out-of-the-box bundle covering 90%+ free providers (OpenRouter, Groq, Google Gemini, Nvidia NIM, GitHub Models, Cerebras, Mistral, HuggingFace, Cloudflare, local Ollama/vLLM), an automated discovery worker polling free models from the OpenRouter API, an in-memory cascade failover engine handling `429`/`5xx` retries, the synthetic `auto:free` routing model, and lightweight request telemetry (structured logging with per-request correlation IDs linking failover hops across candidates).
* **Done When:** An HTTP request dispatched via `curl` or the official OpenAI Python SDK to `http://localhost:8000/v1/chat/completions` receives a valid response from an OpenRouter free model, and an intercepted `429` error on the primary candidate seamlessly fails over to an alternative free candidate without client disruption.
* **Status:** `done` (Proof: 24 passing tests in `backend/tests`, live OpenRouter discovery probe, live model listing and failover verification).

---

### P2 — Provider Validation API, Circuit Breaker, and Onboarding Agent
* **Deliverable:** Live activation across all bundled providers, adaptive Circuit Breaker with exponential cool-off intervals, validation endpoint (`POST /api/admin/providers/validate`), and the prototype for the automated Provider Onboarding Agent (`POST /api/admin/providers/auto-discover`).
* **Done When:** Requests can cascade across heterogeneous providers (e.g., OpenRouter -> Groq -> Google Gemini) upon quota exhaustion, and a new custom provider can be validated via API or analyzed automatically by the onboarding agent.
* **Depends On:** P1
* **Status:** `active` ← **Current Focus**

---

### P3 — Benchmark Engine, Quality Tiering, and Specialized Routing Pools
* **Deliverable:** Integrated benchmark scoring database (Chatbot Arena Elo, MMLU, HumanEval), automated tier classification (S / A / B), virtual routing aliases (`auto:quality`, `auto:fast`, `auto:code`), and strict prompt context window guards.
* **Done When:** A completion request targeting `model="auto:code"` routes automatically to the highest-scoring coding model available in the free pool, and prompts with large token counts (> 32k tokens) bypass models with insufficient context length (e.g., 8k limits).
* **Depends On:** P2
* **Status:** `planned`

---

### P4 — React Web Dashboard
* **Deliverable:** A responsive Single Page Application (SPA) offering real-time model catalog visualization with latency measurements, interactive virtual pool and priority management, live request/response inspection, token and cost savings analytics, and provider key configuration forms. Backed by a minimal internal metrics interface (per-provider/per-model 429 counters, TTFT histograms, failover counts) exposed via `GET /api/admin/stats`.
* **Done When:** A developer can open the dashboard in a web browser, inspect model states in real time, configure API keys, submit test prompts, and observe failover execution paths visually.
* **Depends On:** P1
* **Status:** `planned`

---

### P5 — Docker Packaging, Prompt Caching, and Production Release
* **Deliverable:** Multi-stage `Dockerfile` (compiling the React frontend and packaging it into the FastAPI runtime), single-container distribution, embedded SQLite exact-hash caching for repeated identical prompts to conserve free rate limits, and integration documentation for Cursor, LangChain, and Continue.
* **Done When:** Running `docker run -p 8000:8000 ...` launches the complete application out of the box without requiring local runtime environment dependencies.
* **Depends On:** P3, P4
* **Status:** `planned`

---

### Deferred — OpenTelemetry Exporters
* **Item:** Full OpenTelemetry instrumentation (tracing spans, metrics exporters, collector integration).
* **Reason:** The proxy is a local single-user zero-setup tool; SQLite telemetry plus structured logging cover the actual consumers of metrics. OTel adds heavy dependencies contradicting the zero-setup core value.
* **Return When:** Server-side deployment for a team / multiple proxy instances requiring aggregated monitoring; requires a separate DEC and stack approval.
