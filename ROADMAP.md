# Project Roadmap (ROADMAP)

**Goal:** Deliver a fully featured, OpenAI-compatible smart proxy for free-tier LLM models with dynamic provider discovery, transparent cascade failover, benchmark-based routing, and a modern React web dashboard (see details in [VISION.md](VISION.md)).

---

### P1 — Core OpenAI Proxy, Declarative Provider Registry, and OpenRouter Integration
* **Deliverable:** A functional FastAPI service exposing `/v1/chat/completions` (supporting standard buffered and SSE streaming responses), a declarative provider schema (`providers.yaml`), out-of-the-box bundle covering 90%+ free providers (OpenRouter, Groq, Google Gemini, Nvidia NIM, GitHub Models, Cerebras, Mistral, HuggingFace, Cloudflare, local Ollama/vLLM), an automated discovery worker polling free models from the OpenRouter API (wired into application lifespan at startup and on periodic interval), an in-memory cascade failover engine handling `429`/`5xx` retries, and the synthetic `auto:free` routing model.
* **Done When:** An HTTP request dispatched via `curl` or the official OpenAI Python SDK to `http://localhost:8000/v1/chat/completions` receives a valid response from an OpenRouter free model, and an intercepted `429` error on the primary candidate seamlessly fails over to an alternative free candidate without client disruption.
* **Status:** `done` (Proof: 27 automated unit/integration tests passing in `backend/tests`; real live socket probe documented in `notes/T-004-live-probe.md` confirming real OpenRouter completion, `/v1/models` serving 21 live models, and 47 SSE chunks; live 429 failover verified at ASGI/mocked level as upstream rate limits were not reached during probe window; lifespan discovery wired).

---

### P2 — Provider Validation API, Circuit Breaker, Structured Telemetry, and Onboarding Agent
* **Deliverable:** Live activation across viable supported bundled providers (retired services are excluded and per-provider live prerequisites must be satisfied), adaptive Circuit Breaker with exponential cool-off intervals, structured logging with correlation IDs linking failover hops across candidates, validation endpoint (`POST /api/admin/providers/validate`), and the prototype for the automated Provider Onboarding Agent (`POST /api/admin/providers/auto-discover`).
* **Done When:** Requests can cascade across heterogeneous providers (e.g., OpenRouter -> Groq -> Google Gemini) upon quota exhaustion, and a new custom provider can be validated via API or analyzed automatically by the onboarding agent.
* **Depends On:** P1
* **Status:** `active` ← **Current Focus**
* **Accepted checkpoint (2026-10-23):** T-005/T-006 accepted. T-007 operational baseline is accepted and integrated: strict OpenRouter plus explicitly confirmed Groq/NVIDIA/Mistral on the local primary at127.0.0.1:8001. Six final actual primary buffered/SSE checks PASS at32-token caps; independent412 tests/12.67s. NVIDIA Free Endpoint discovery and probe-queue fairness repairs are included. [Primary evidence](notes/T-007-primary-activation.md); detailed historical proofs/limits remain in [results](notes/T-007-results.md).
* **Nearest owner-selected addition:** T-010 — task-specific catalogs and APIs for embeddings, rerank, decisions and speech, with dynamic free eligibility; see [TASKS](TASKS.md). Owner approved v1.0.0/N1–N4; source implementation and local verification are complete, with strict live admission gaps retained. Full T-010/AC-18 is open; primary activation is separate. This addition does not close existing P2 obligations.
* **Preserved gaps:** T-007 is not fully closed: HF positive delivery, Gemini live/profile work, gateways and positive local/cloud provenance remain unresolved/deferred as recorded in TASKS. Cloudflare/Cerebras/GitHub remain unconditional skips. T-009 is owner-accepted and primary-integrated with buffered/SSE target proof; onboarding T-008 is not implemented. Conditional account trust is not provider-certified zero cost.
* **Current T-009 checkpoint (2026-10-23):** Owner approved [v1.0.0](specs/T-009-adaptive-circuit-breaker.md) and R1–R3. [Verified result](notes/T-009-results.md):493 full tests, independent81 focused tests after repairs, actual strict-OpenRouter buffered/SSE PASS within2 capped sends. Owner subsequently accepted the result and authorized primary integration: PID33541 at8001, actual buffered/SSE PASS through Groq, one attempt each at32-token caps. No full P2 closure. The owner now prioritizes T-010 task-specific APIs before T-008; P3's P2 dependency is unchanged.

---

### P3 — Benchmark Engine, Quality Tiering, and Specialized Routing Pools
* **Deliverable:** Integrated benchmark scoring database (Chatbot Arena Elo, MMLU, HumanEval), automated tier classification (S / A / B), virtual routing aliases (`auto:quality`, `auto:fast`, `auto:code`), strict prompt context window guards, and reasoning-aware routing (addressing observation F-2 where reasoning-first models return content: null under constrained token budgets).
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

### Remaining route after accepted T-009

1. Review the owner-approved T-010 v1.0.0/N1–N4 implemented candidate. Preserve unknown gates; full positive free delivery/AC-18 remains open. The owner accepted the partial result; [v1.1.0 amendment](specs/T-010-free-variant-admission.md) and sourced admission recon are ready for approval. A1–A3/finite packet are proposed; current admission remains unchanged. Unlocking sourced profiles and primary activation remain separate decisions. See [results](notes/T-010-results.md).
2. Prepare T-008 onboarding recon/specification after T-010; its existing scope remains open.
3. Resolve or explicitly agree remaining T-007 dispositions and verify P2 exit criteria; current working pool/T-009 acceptance does not close them.
4. Deliver P3 ranking/pools/context/reasoning work after P2; P4 dashboard may proceed in parallel under its existing P1 dependency.
5. Deliver P5 packaging/cache/client documentation after P3 and P4.

[Current planning memory and provider return conditions](notes/next-steps-current-checkpoint.md). No new batch, live packet or phase-scope waiver is approved by this sequence.

---

### Deferred — OpenTelemetry Exporters
* **Item:** Full OpenTelemetry instrumentation (tracing spans, metrics exporters, collector integration).
* **Reason:** The proxy is a local single-user zero-setup tool; Bounded in-memory telemetry plus structured logging cover the current consumers of metrics; SQLite-backed operational storage remains planned. OTel adds heavy dependencies contradicting the zero-setup core value.
* **Return When:** Server-side deployment for a team / multiple proxy instances requiring aggregated monitoring; requires a separate DEC and stack approval.
