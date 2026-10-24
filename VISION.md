# Project Vision (VISION)

## 1. Target Audience and Problem Statement
* **Target Audience:** Software engineers, prototyping developers, AI tinkerers, indie hackers, and engineering teams maintaining development and staging environments.
* **Problem Statement:** Commercial LLM inference (e.g., OpenAI, Anthropic) is prohibitively expensive for continuous local development, automated test suites, and rapid experimental iterations. Meanwhile, free-tier API models (such as OpenRouter `:free`, Groq free tier, Google Gemini free tier, and NVIDIA hosted prototyping access) are fragmented, frequently adjust rate limits, fail unpredictably with `429 Too Many Requests` or `5xx` errors, and experience transient availability drops. Developers must manually monitor endpoints, rotate keys, and modify client application code to handle downtime.

## 2. Core Value and Goals
* **Goal:** Build a lightweight, intelligent proxy and load balancer that aggregates available free-tier LLM models across multiple external providers, exposing them via a single standard OpenAI-compatible API featuring automatic, transparent cascade failover when rate limits or provider outages occur.
* **Core Value:** Zero-cost inference for development, testing, and staging workflows with resilient access through one `OPENAI_BASE_URL`. Strict source/enforcement profiles verify their covered cost policy; an explicitly opted-in account mode relies on the operator keeping the actual billing path nonbillable. The account-mode assertion is not an unconditional proxy guarantee against charges.

## 3. Success Criteria (Observable Conditions)
1. Any standard OpenAI-compatible client (e.g., official `openai` SDK, `curl`, Cursor, LangChain) successfully dispatches chat completion requests to `http://localhost:8000/v1/chat/completions` and receives valid completion responses.
2. Users provide a provider API key; the proxy automatically determines eligible free chat models for that key, without requiring hardcoded model identifiers or manually maintained model allowlists. Background refresh detects additions, removals and source-visible pricing/capability changes; account-side changes not exposed by the provider remain the opted-in operator's responsibility. Dispatch requires the current assurance defined for that provider. OpenRouter uses strict source/enforcement verification. Under the owner-accepted hybrid design, Groq/NVIDIA/Mistral/Hugging Face may instead use an explicit operator assertion of a nonbillable account plus fresh dynamic availability probes; default unconfirmed accounts remain excluded. A probe proves availability, not tariff. This conditional guarantee and its account-change/charge-reporting limits must be disclosed; see the [approved v1.3.0 contract](specs/T-007-hybrid-account-eligibility.md), whose exact H1–H4 implementation and isolated live packet were owner-approved on 2026-10-23; primary activation is a separate decision and has been explicitly authorized and verified for Groq/NVIDIA/Mistral in the [local primary checkpoint](notes/T-007-primary-activation.md).
3. Upon encountering or simulating a `429 Too Many Requests` or `5xx` error from an upstream provider, the proxy intercepts the failure and transparently reroutes the payload to an alternative eligible model in the free pool within < 500 ms without surfacing errors to the client.
4. Server-Sent Events (SSE) streaming (`stream=true`) is fully supported with failover-safe pre-buffering.
5. A React-based web dashboard displays real-time model availability, latency metrics, active routing queues/pools, and cumulative cost savings.

## 4. In-Scope
* **OpenAI-Compatible Proxy API:** Endpoints `/v1/chat/completions` (supporting both buffered and streaming modes) and `/v1/models`.
* **Task-specific inference (planned; nearest T-010):** Embeddings, rerank, structured decisions and text-to-speech through separate task APIs and task-filtered catalogs. Chat-client model discovery remains chat-only by default. Each task needs its own dynamically refreshed cost/capability/dispatch evidence; no manual model-ID admission lists or implicit transfer of chat eligibility. Embedding failover must preserve the consuming index's vector space. This extends product scope, not the current as-built API.
* **Discovery Engine:** Periodic background polling of provider catalogs and authoritative pricing/account-entitlement sources (OpenRouter, Groq, Google Gemini, Nvidia NIM) to determine zero-cost chat eligibility for the supplied key. Pricing formats and free-access rules are provider-specific; zero prompt/completion prices are one source, not a universal API schema or complete proof for every request feature. Eligibility must expire and be refreshed as conditions change. The evidence, enforcement or explicitly conditional account-assurance contract needed for each profile is specified before claiming support. Account-mode discovery is automatic and never based on manually maintained model IDs.
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
* **API Compatibility:** Preserve the documented OpenAI-compatible text-chat subset and client contracts. Planned embeddings and speech follow their documented OpenAI-style subsets; rerank and decisions use explicit task-specific contracts rather than a claim of universal OpenAI compatibility.
* **Zero External DB Dependencies:** Use embedded `SQLite` (accessed asynchronously via `aiosqlite` / `SQLAlchemy`) to maintain zero-setup local deployment.

## 7. Deferred Items
* **Semantic Embedding Cache:** Deferred in favor of exact-hash prompt caching in earlier phases; semantic vector matching will be evaluated once core routing matures.
* **Automated Multi-Account Key Cycling:** Key rotation across hundreds of disposable accounts per provider is deferred to avoid violating provider terms of service.
