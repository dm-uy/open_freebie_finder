# DEC-003: Canonical Model Mapping, Upstream Credential Encapsulation, and Harness Interoperability

## Context and Problem
Target consumers of Open Freebie Finder are developer tools and open-source AI harnesses (e.g. DeepSeek Harness `dsh`, Cursor, Continue, LibreChat, Open WebUI).
These harnesses expect:
1. A single unified OpenAI-compatible endpoint with no complex multi-provider credential setup on the harness side.
2. An instant, non-blocking response when pressing "Fetch available models" (`GET /v1/models`).
3. Seamless execution even if the exact requested model exists under different IDs across multiple free providers (e.g., `llama-3.3-70b-versatile` on Groq vs `meta-llama/llama-3.3-70b-instruct:free` on OpenRouter vs `meta/llama-3.3-70b-instruct` on NVIDIA NIM).
4. Reliable failover without broken streams or mismatched model identifiers returned in completion chunks.

## Decision

### 1. Centralized Credential Encapsulation
* All upstream provider keys (OpenRouter, Groq, Nvidia, Gemini, etc.) are managed **internally** within Open Freebie Finder (via `.env`, config, or the web dashboard).
* Downstream harnesses treat Open Freebie Finder as a single provider. Downstream requests do not require upstream keys; authorization is permissive by default (accepting empty or dummy keys like `freebie-local`).
* Optional master key (`PROXY_MASTER_KEY`) can be enabled if hosted on a public network.

### 2. Two-Tier Smart Failover Strategy
When a harness requests a model (e.g., `meta-llama/llama-3.3-70b-instruct`):
* **Tier 1 — Same-Model Cross-Provider Failover:**
  The proxy first attempts to serve the request from fastest/highest-quota provider hosting the *exact same model* (e.g. Groq). If it returns `429 Too Many Requests` or times out, the proxy tries Provider 2 (Nvidia NIM), then Provider 3 (OpenRouter `:free`), then Cerebras. The user receives the exact model requested with zero degradation.
* **Tier 2 — Alternative Model Fallback:**
  Only if all providers for that specific model are exhausted or in cooldown, the proxy falls back to an alternative model in the same capability tier (e.g., `qwen/qwen-2.5-72b` or `gemini-2.0-flash`).

### 3. Non-Blocking `/v1/models` from In-Memory Registry
* `GET /v1/models` never triggers outbound network calls.
* It returns from the active in-memory model registry (periodically synced in background) within 1-2 ms.
* "Fetch available models" in external harnesses succeeds immediately.

### 4. Canonical Model Name Masking
* The proxy normalizes incoming model names to internal provider IDs when dispatching outbound requests.
* When returning responses (buffered or SSE streaming chunks), the proxy overrides the `model` field in the payload to match the canonical name requested by the harness, preventing client-side validation errors.

### 5. First-Token Stream Pre-buffering
* For streaming requests (`stream: true`), the proxy holds the downstream HTTP connection open while waiting for the upstream provider's first chunk.
* If an upstream error (429 or in-stream JSON error) occurs before the first valid delta content chunk, the proxy discards the stream and repeats the request on the next candidate.
* Once the first token is received, the proxy flushes headers and streams tokens downstream.

### 6. Error Taxonomy
* **`429` / `503` / Timeout:** Triggers immediate failover to the next candidate and marks current candidate in cooldown (60s).
* **`400` Context Window Exceeded:** Does NOT retry candidates with equal or smaller context windows. Only fails over to models with sufficient context capacity (e.g. Gemini 1M) or returns a descriptive error.
* **`401` Unauthorized:** Marks that provider disabled and alerts the dashboard.

### 7. Superposition Brainstorming Protocol
* For complex architectural forks or trade-offs during implementation, a dedicated subagent is spun up to evaluate candidate options in superposition, score them against project constraints, and deliver an optimal consensus summary.

## Consequences
* Seamless plug-and-play compatibility with DeepSeek Harness, Cursor, and any OpenAI client.
* Zero leakage of upstream provider complexity into the consumer tools.
* Maximized utilization of all free tier quotas before degrading to alternative models.


## T-010 approved task extension (2026-10-23)

Owner approval of [T-010 v1.0.0/N1–N4](../../specs/T-010-task-specific-inference.md) extends the source backend with separate task catalogs/protocols and exact OpenRouter task routes. Declarative logical provider identity is retained; task parsing/zero-price controls are owned protocol policy, never arbitrary YAML expressions or client routing overrides. Chat's default listing, alternative-model fallback and response masking do not authorize embedding/rerank/decisions/speech substitution. Task service health is distinct; credential quota/auth and the financial account umbrella protect related chat/task routes together within the retained registry. Independent registries remain isolated. Rerank/speech and incomplete task pricing remain unknown, with no inherited chat omitted-fee exception or account qualification. This approval authorizes implementation, not acceptance of missing external proof or primary activation. [Result evidence and limits](../../notes/T-010-results.md).
