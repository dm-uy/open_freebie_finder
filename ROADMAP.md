# Project Roadmap (ROADMAP)

**Goal:** Deliver a fully featured, OpenAI-compatible smart proxy for free-tier LLM models with dynamic provider discovery, transparent cascade failover, benchmark-based routing, and a modern React web dashboard (see details in [VISION.md](VISION.md)).

---

### P1 — Core OpenAI Proxy and OpenRouter Discovery Integration
* **Deliverable:** A functional FastAPI service exposing `/v1/chat/completions` (supporting standard buffered and SSE streaming responses), an automated discovery worker polling free models from the OpenRouter API, an in-memory cascade failover engine handling `429`/`5xx` retries, and the synthetic `auto:free` routing model.
* **Done When:** An HTTP request dispatched via `curl` or the official OpenAI Python SDK to `http://localhost:8000/v1/chat/completions` receives a valid response from an OpenRouter free model, and an intercepted `429` error on the primary candidate seamlessly fails over to an alternative free candidate without client disruption.
* **Status:** `active` ← **Current Focus**

---

### P2 — Additional Cloud Providers (Groq, Google AI Studio, Nvidia NIM) and Circuit Breaker
* **Deliverable:** Integration adapters for Groq (ultra-low latency free tier), Google Gemini API (Google AI Studio free tier up to 15 RPM), and Nvidia NIM API. Implementation of an adaptive Circuit Breaker with exponential cool-off intervals and upstream availability tracking.
* **Done When:** Requests can cascade across heterogeneous providers (e.g., OpenRouter -> Groq -> Google Gemini) when one provider hits quota exhaustion.
* **Depends On:** P1
* **Status:** `planned`

---

### P3 — Benchmark Engine, Quality Tiering, and Specialized Routing Pools
* **Deliverable:** Integrated benchmark scoring database (Chatbot Arena Elo, MMLU, HumanEval), automated tier classification (S / A / B), virtual routing aliases (`auto:quality`, `auto:fast`, `auto:code`), and strict prompt context window guards.
* **Done When:** A completion request targeting `model="auto:code"` routes automatically to the highest-scoring coding model available in the free pool, and prompts with large token counts (> 32k tokens) bypass models with insufficient context length (e.g., 8k limits).
* **Depends On:** P2
* **Status:** `planned`

---

### P4 — React Web Dashboard
* **Deliverable:** A responsive Single Page Application (SPA) offering real-time model catalog visualization with latency measurements, interactive virtual pool and priority management, live request/response inspection, token and cost savings analytics, and provider key configuration forms.
* **Done When:** A developer can open the dashboard in a web browser, inspect model states in real time, configure API keys, submit test prompts, and observe failover execution paths visually.
* **Depends On:** P1
* **Status:** `planned`

---

### P5 — Docker Packaging, Prompt Caching, and Production Release
* **Deliverable:** Multi-stage `Dockerfile` (compiling the React frontend and packaging it into the FastAPI runtime), single-container distribution, embedded SQLite exact-hash caching for repeated identical prompts to conserve free rate limits, and integration documentation for Cursor, LangChain, and Continue.
* **Done When:** Running `docker run -p 8000:8000 ...` launches the complete application out of the box without requiring local runtime environment dependencies.
* **Depends On:** P3, P4
* **Status:** `planned`
