# Project Vision (VISION)

## 1. Target Audience and Problem Statement
* **Target Audience:** Software engineers, prototyping developers, AI tinkerers, indie hackers, and engineering teams maintaining development and staging environments.
* **Problem Statement:** Commercial LLM inference (e.g., OpenAI, Anthropic) is prohibitively expensive for continuous local development, automated test suites, and rapid experimental iterations. Meanwhile, free-tier API models (such as OpenRouter `:free`, Groq free tier, Google Gemini free tier, and Nvidia NIM credits) are fragmented, frequently adjust rate limits, fail unpredictably with `429 Too Many Requests` or `5xx` errors, and experience transient availability drops. Developers must manually monitor endpoints, rotate keys, and modify client application code to handle downtime.

## 2. Core Value and Goals
* **Goal:** Build a lightweight, intelligent proxy and load balancer that aggregates available free-tier LLM models across multiple external providers, exposing them via a single standard OpenAI-compatible API featuring automatic, transparent cascade failover when rate limits or provider outages occur.
* **Core Value:** Complete elimination of inference costs for development, testing, and staging workflows, preserving service resilience and uptime without requiring changes to client application code (a single update to `OPENAI_BASE_URL` is all that is required).

## 3. Success Criteria (Observable Conditions)
1. Any standard OpenAI-compatible client (e.g., official `openai` SDK, `curl`, Cursor, LangChain) successfully dispatches chat completion requests to `http://localhost:8000/v1/chat/completions` and receives valid completion responses.
2. The proxy dynamically discovers active free models from integrated providers (e.g., OpenRouter) without hardcoded model identifiers in source code.
3. Upon encountering or simulating a `429 Too Many Requests` or `5xx` error from an upstream provider, the proxy intercepts the failure and transparently reroutes the payload to an alternative eligible model in the free pool within < 500 ms without surfacing errors to the client.
4. Server-Sent Events (SSE) streaming (`stream=true`) is fully supported with failover-safe pre-buffering.
5. A React-based web dashboard displays real-time model availability, latency metrics, active routing queues/pools, and cumulative cost savings.

## 4. In-Scope
* **OpenAI-Compatible Proxy API:** Endpoints `/v1/chat/completions` (supporting both buffered and streaming modes) and `/v1/models`.
* **Discovery Engine:** Periodic background polling of provider model catalogs (OpenRouter API, Groq API, Google Gemini API, Nvidia NIM) to identify models with zero token costs (`pricing.prompt == 0 and pricing.completion == 0`).
* **Smart Failover & Circuit Breaker:** Cascade retry strategy on `429`, `503`, and network timeouts; transient cool-down ejection for unstable upstream models.
* **Smart Pools & Virtual Models:** Virtual model identifiers (`auto:free`, `auto:fast`, `auto:quality`, `auto:code`).
* **Scoring & Context Guard:** Built-in benchmark score registry (Chatbot Arena Elo, MMLU, HumanEval) and prompt context window validation to prevent context overflow errors.
* **React Web Dashboard:** Provider API key management, pool inspection, live request trace viewer, error logs, and cost savings analytics.
* **Configuration & Storage:** `.env` file support, embedded SQLite database for settings, telemetry, and metrics, and Docker containerization.

## 5. Out-of-Scope (Non-Goals)
* Self-hosting GPU runtimes or serving raw model weights locally (e.g., embedding vLLM or Ollama inside the proxy container) — the proxy balances external, hosted free cloud APIs.
* User billing, subscription paywalls, or multi-tenant commercial monetization.
* Model fine-tuning or parameter adaptation.

## 6. Hard Constraints
* **Backend:** Python 3.11+ with FastAPI, using asynchronous I/O via `asyncio` and `httpx`.
* **Frontend:** React with Vite and Tailwind CSS.
* **API Compatibility:** The external interface must adhere strictly to the OpenAI Chat Completions API specification for drop-in interoperability.
* **Zero External DB Dependencies:** Use embedded `SQLite` (accessed asynchronously via `aiosqlite` / `SQLAlchemy`) to maintain zero-setup local deployment.

## 7. Deferred Items
* **Semantic Embedding Cache:** Deferred in favor of exact-hash prompt caching in earlier phases; semantic vector matching will be evaluated once core routing matures.
* **Automated Multi-Account Key Cycling:** Key rotation across hundreds of disposable accounts per provider is deferred to avoid violating provider terms of service.
