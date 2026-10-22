# System Architecture (ARCHITECTURE)

## 1. Scope and Specification Status
* **Status:** `proposal` (architectural design prior to baseline framework implementation).
* **Stack:**
  * **Backend:** Python 3.11+ / FastAPI / httpx / Pydantic v2 / aiosqlite
  * **Frontend:** React 18+ / Vite / Tailwind CSS / Lucide Icons
  * **Storage:** Embedded SQLite

## 2. System Components and Responsibilities

```
[ Client Application (OpenAI SDK / Cursor / LangChain / curl) ]
                  │
                  ▼ (OpenAI Chat Completions Protocol: /v1/chat/completions)
┌───────────────────────────────────────────────────────────────┐
│                 Open Freebie Finder (FastAPI)                 │
│                                                               │
│  ┌─────────────────────────┐     ┌─────────────────────────┐  │
│  │   OpenAI Proxy Router   │     │   Admin & Settings API  │  │
│  └────────────┬────────────┘     └────────────┬────────────┘  │
│               │                               │               │
│               ▼                               ▼               │
│  ┌─────────────────────────┐     ┌─────────────────────────┐  │
│  │   Smart Balancer Core   │◄────┤ Model Registry & Cache  │  │
│  │  - Virtual Model Router │     │  - OpenRouter           │  │
│  │  - Cascade Failover     │     │  - Groq                 │  │
│  │  - Circuit Breaker      │     │  - Google AI Studio     │  │
│  │  - Benchmark Evaluator  │     │  - Nvidia NIM           │  │
│  └────────────┬────────────┘     └────────────┬────────────┘  │
│               │                               │               │
│               ▼                               ▼               │
│  ┌─────────────────────────┐     ┌─────────────────────────┐  │
│  │    Provider Adapters    │     │   SQLite Metrics Store  │  │
│  │ (Async HTTP Client Pool)│     │  (Telemetry, Cooldowns) │  │
│  └────────────┬────────────┘     └─────────────────────────┘  │
└───────────────┼───────────────────────────────────────────────┘
                │
                ▼ (Outbound HTTPS Requests)
 [ External Free Cloud APIs: OpenRouter, Groq, Google, Nvidia ]
```

### Core Backend Modules (`backend/app/`)
1. **`api/v1/` (OpenAI Proxy Endpoints):**
   * `/v1/chat/completions`: Receives standard OpenAI payloads with full support for buffered responses and Server-Sent Events (`stream: true/false`).
   * `/v1/models`: Returns available upstream models and synthetic virtual aliases (`auto:*`).
2. **`api/admin/` (Management & Telemetry Endpoints):**
   * Provider API key persistence, manual discovery refresh triggers, health metrics, request execution logs, and pool priority configuration.
3. **`core/discovery/` (Discovery Engine):**
   * Periodically polls provider endpoints (e.g., OpenRouter `GET /api/v1/models`), filtering for zero-cost models where `pricing.prompt == 0 and pricing.completion == 0`.
   * Manages an automated background task (default interval: 15 minutes) to update active model registries.
4. **`core/balancer/` (Smart Balancer & Cascade Failover):**
   * Resolves requested model identifiers or virtual routing aliases (`auto:free`, `auto:fast`, `auto:code`, `auto:quality`) into prioritized candidate queues.
   * Enforces Circuit Breaker cooldowns, filtering out endpoints recovering from recent `429` or `5xx` spikes.
   * Validates context window constraints by dropping models whose maximum token window is smaller than the incoming prompt.
   * Executes the cascade retry sequence: intercepts `429` / `5xx` / timeout events, marks candidate models in cooldown, and dispatches the request to the next candidate in the queue.
5. **`core/providers/` (Declarative Provider Registry & Universal Adapter):**
   * Configured via declarative manifests (`providers.yaml` / JSON schema) without requiring Python code modifications for new endpoints.
   * `GenericOpenAIProviderAdapter`: Universal async adapter executing HTTP requests, headers injection, streaming SSE transformations, and error handling.
   * Out-of-the-box pre-configured manifests covering 90%+ of zero-cost inference needs:
     1. **OpenRouter:** Dynamic `:free` models filter (`pricing.prompt == 0 and pricing.completion == 0`).
     2. **Groq Cloud:** Ultra-fast free tier (Llama 3.3 70B, Gemma 2, Llama 3.1 8B).
     3. **Google AI Studio (Gemini):** 15 RPM / 1M context free tier via OpenAI-compatible endpoint.
     4. **NVIDIA NIM:** Hosted open weights (Llama 3.3, Nemotron 70B, Mistral Large).
     5. **GitHub Models:** Azure AI free tier via GitHub PAT (GPT-4o-mini, Phi-4, Llama 3.3).
     6. **Cerebras Cloud:** Ultra-fast ~2000 t/s Llama 3.1 free tier.
     7. **Mistral AI:** Free experiment tier (Mistral Small, Codestral).
     8. **Hugging Face Inference API:** Serverless free open models.
     9. **Cloudflare Workers AI:** 10,000 free daily neurons.
     10. **Local / Self-hosted:** Fallback to local Ollama, vLLM, or LM Studio.
   * Validation interface (`POST /api/admin/providers/validate`): Tests endpoint connectivity, model availability, and single-token completion.
   * Roadmap readiness: Foundation for internal "Onboarding Agent" (`POST /api/admin/providers/auto-discover`).
6. **`core/benchmarks/` (Quality & Benchmark Index):**
   * In-memory benchmark scoring table (Chatbot Arena Elo, MMLU, HumanEval) enabling tiered model routing into quality and specialized coding pools.
7. **`storage/` (SQLite Telemetry & Config Store):**
   * Embedded asynchronous database logging request latency (Time To First Token - TTFT), error distributions, failover incidents, and provider credentials.

### Frontend Application (`frontend/`):
* **Dashboard Overview:** Real-time proxy status, throughput graphs, request volume, and aggregate cost savings calculated against commercial GPT-4o reference rates.
* **Models Catalog:** Interactive data table showing discovered free models, real-time availability states (`Healthy`, `Rate-Limited`, `Cooldown`), context lengths, and benchmark scores.
* **Pools Configuration:** Visual builder for virtual model groups (`auto:free`, `auto:code`, etc.) with drag-and-drop fallback priority ordering.
* **Live Inspector:** Real-time request log displaying execution path, provider failover hops, round-trip latency, and token consumption.
* **Settings:** Secure entry and validation for provider API keys.

## 3. Entry Points, Interfaces, and Contracts

### Client Interface (OpenAI Compatible)
* `POST /v1/chat/completions`
  * **Request Body:**
    ```json
    {
      "model": "auto:free",
      "messages": [
        {"role": "user", "content": "Explain quantum computing in simple terms."}
      ],
      "stream": false,
      "temperature": 0.7
    }
    ```
  * **Response Body (Non-Streaming):**
    ```json
    {
      "id": "chatcmpl-freebie-01J9XABC",
      "object": "chat.completion",
      "created": 1729600000,
      "model": "meta-llama/llama-3.3-70b-instruct:free",
      "system_fingerprint": "open-freebie-finder-v1",
      "choices": [
        {
          "index": 0,
          "message": {
            "role": "assistant",
            "content": "Quantum computing uses quantum bits or qubits..."
          },
          "finish_reason": "stop"
        }
      ],
      "usage": {
        "prompt_tokens": 15,
        "completion_tokens": 48,
        "total_tokens": 63
      }
    }
    ```
  * **Response Body (Streaming):**
    Delivered via standard SSE format: chunks formatted as `data: { ... }\n\n` concluded by `data: [DONE]\n\n`.

### Admin & Management Interface
* `GET /api/admin/models`: Returns all discovered free models along with health states and metrics.
* `POST /api/admin/discovery/refresh`: Manually triggers an immediate background discovery cycle across all active providers.
* `GET /api/admin/stats`: Returns aggregated operational statistics (request counts, 429 failover events, token volumes, estimated savings).
* `POST /api/admin/keys`: Stores and tests upstream provider API authentication keys.

## 4. Failure Handling: Cascade Failover Flow

```
Client Request -> [/v1/chat/completions] (model="auto:free")
                         │
                         ▼
             [Select Candidate Queue]
        [Model A (70B), Model B (70B), Model C (32B)]
                         │
                         ▼
                 [Try Candidate 1] ─── HTTP 200 OK ──────────► Return to Client
                         │
                 HTTP 429 / 5xx / Timeout
                         │
                         ▼
             [Record Failure & Cooldown]
         (Candidate 1 marked unavailable for 60s)
                         │
                         ▼
                 [Try Candidate 2] ─── HTTP 200 OK ──────────► Return to Client
                         │
                 HTTP 429 / 5xx
                         │
                         ▼
                 [Try Candidate 3] ─── HTTP 200 OK ──────────► Return to Client
                         │
               All candidates exhausted
                         │
                         ▼
        HTTP 503 "All free pool candidates exhausted"
```

## 5. Invariants and Trust Boundaries
1. **Client Isolation from Upstream Failures:** Upstream `429 Too Many Requests` and `5xx` errors are never propagated directly to the downstream client as long as at least one eligible model remains available in the candidate pool.
2. **Centralized Upstream Credential Encapsulation:** Downstream harnesses (e.g. DeepSeek Harness, Cursor) connect using a single endpoint without needing upstream keys. All provider credentials reside securely inside Open Freebie Finder.
3. **Failover-Safe Streaming:** For streaming completions (`stream: true`), the proxy delays emitting the initial SSE handshake until receiving a valid first chunk from the upstream provider. If an upstream `429` or connection failure occurs at initiation, failover executes seamlessly before any bytes are transmitted to the downstream client.
4. **Canonical Model Name Masking:** Model names returned in completion payloads and SSE chunks always match the canonical identifier requested by the client, shielding downstream consumers from internal provider naming discrepancies.
5. **Non-blocking Model Catalog:** `GET /v1/models` resolves exclusively from the local in-memory registry in < 2ms, guaranteeing instantaneous response to harness "Fetch available models" queries.
6. **Local Credential Boundary:** Provider API keys are maintained strictly in local storage (`.env` or local SQLite); keys are never logged, telemetry-reported, or exposed to third parties.

## 6. Execution and Environments
* **Local Development Environment:**
  * Backend: `uvicorn backend.app.main:app --port 8000 --reload`
  * Frontend: `npm run dev --prefix frontend` (Vite dev server proxying `/api` and `/v1` to `http://localhost:8000`)
* **Standalone / Docker Environment:**
  * Multi-stage Docker container: React frontend assets are compiled and served as static files directly by FastAPI, exposing a unified service on port `8000`.

## 7. Architectural Decisions and Rationales
* See [DEC-001: Technology Stack and Architecture Pattern](docs/decisions/DEC-001-stack-and-architecture.md) for rationale concerning FastAPI, React, SQLite, and OpenAI reverse-proxy pattern selection.
* See [DEC-002: Declarative Provider Schema and Automated Onboarding](docs/decisions/DEC-002-declarative-provider-schema.md) for declarative configuration, universal adapter, out-of-the-box provider bundle, and provider onboarding evolution.
* See [DEC-003: Canonical Model Mapping and Harness Interoperability](docs/decisions/DEC-003-canonical-model-mapping-and-harness-interop.md) for two-tier failover, credential encapsulation, and harness interop.
