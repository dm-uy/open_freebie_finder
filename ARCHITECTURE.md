# System Architecture (ARCHITECTURE)

## 1. Scope and Specification Status

**Current state:** accepted T-007 backend locally integrated; owner-accepted T-009 is also integrated and target-verified; broader product architecture remains partly planned. The current checkpoint below and the latest as-built sections govern implemented behavior. Sections2–6 retain the original target design/examples, not a claim that every pictured API, UI, storage or routing component exists.

### Current backend checkpoint (2026-10-23)

| Component | As built / evidence |
|---|---|
| Runtime | Python/FastAPI/httpx/Pydantic backend; ordinary uvicorn at127.0.0.1:8001, last confirmed PID33541 |
| Public API | /health, /v1/models, /v1/chat/completions; memory-only model listing, covered text request profile, bounded buffered/SSE cascade |
| Implemented admin API | /api/admin/providers/validate, /api/admin/telemetry/recent and /api/admin/telemetry/stats; optional master-key checks, safe validation/telemetry |
| Admission | Strict OpenRouter source/enforcement; opt-in direct-provider account assertion plus fresh catalog and private buffered/SSE qualification |
| Active local account configuration | FREE_ACCOUNT_CONFIRMATIONS=["groq","nvidia_nim","mistral"]; shipped default/example[], HF unconfirmed; no manual model IDs |
| Discovery/qualification | Orchestrator-owned lifecycle, bounded resources, NVIDIA Free Endpoint exact intersection, fair provider cursor advanced after actual scheduling |
| Failure control | Registry-owned adaptive route backoff, credential quota/auth gates and atomic recovery tickets; counted attempts and stronger financial/account/source/lease gates remain |
| State | In-memory model/evidence/probe/guard/cooldown/telemetry state, process-local budgets; keys/config read from local environment; no SQLite-backed operational store is delivered |
| Delivery | Six actual primary checks passed for Groq/NVIDIA/Mistral buffered/SSE at32-token caps; independent412 tests/12.67s, [persistent evidence](notes/T-007-primary-activation.md) |
| Planned components | Automated onboarding, benchmark registry/ranking/context-aware quality pools, React dashboard and persistent storage are not delivered by the current backend |

Account-mode assurance is user_asserted, monetary reporting unavailable. A successful probe is availability evidence, not a zero tariff or automatic account inspection. Preserve complete-answer delivery/financial latch separation and no replay after SSE output starts. Source errors cannot retain eligibility or infer local execution from localhost. Earlier static free flags/model lists are superseded by the approved dynamic contracts.

**Target stack, not all implemented:** Python/FastAPI backend; React/Vite/Tailwind frontend; embedded SQLite storage. Relevant decisions are in section7. Provider examples/quota figures in the original target description are historical illustrations, not current free-access authority. Product targets and remaining phase obligations stay in VISION/ROADMAP/TASKS. [Next-step proposal](notes/next-steps-current-checkpoint.md) records why T-009 precedes onboarding; T-009 is owner-accepted and primary-integrated; T-010 preparation now precedes T-008; both remain separate from completed T-009.

### T-009 accepted and primary-integrated

[DEC-005](docs/decisions/DEC-005-adaptive-resilience.md) and [results](notes/T-009-results.md) describe the new registry-owned resilience controller: route service backoff, credential-scope quota pauses, credential-identity401 lockout, atomic generation-bound recovery and private permit integration. Retry-After never silently shortens a supported upstream pause; financial/source/account/lease gates remain stronger. Health finalization is independent of response delivery and waits for upstream cleanup. No new endpoint/store or public telemetry fields. Known eligible health-blocked requests return503 rather than404; model listing remains memory-only. The owner-authorized restart loaded T-009 on the primary at8001 (PID33541); actual buffered/SSE checks passed with32-token caps and one Groq attempt each. See the dated primary integration section in results.

### T-010 accepted partial source implementation; primary not activated

Owner-approved [v1.0.0/N1–N4](specs/T-010-task-specific-inference.md) adds registry-owned TaskCatalog/immutable evidence, owned TaskDiscovery jobs under the existing semaphore/lifespan, closed task protocols, exact TaskExecutor and safe catalog/API handlers. Default chat models/aliases and existing telemetry schemas are preserved. Nonchat snapshots never replace the chat cache. Sources are the separate embeddings catalog and three exact task-filtered OpenRouter model API requests, with bounded refresh/TTL and immediate fail-closed source invalidation.

New source interfaces: `/v1/models?task=embeddings|rerank|decisions|speech`, `/api/admin/models/catalog`, `/v1/embeddings`, `/v1/rerank`, `/v1/decisions`, `/v1/audio/speech`. IDs are exact `openrouter::<raw-id>` within each task; no alternative-model/provider fallback. Text JSON and mp3/pcm responses are fully buffered and validated before delivery. Client disconnect/timeout joins cancelled upstream I/O and releases every ticket/handle. Task body, source and transport limits are explicit in the specification.

Task source/dispatch/profile binding is separate from shared chat financial/auth/quota scope. BillingGuard has a registry-local OpenRouter account umbrella keyed by the private resolved credential identity: same-key source/epoch changes and pruning cannot erase a financial hold. Restoring an old key retains its prior latch. Task service breaker route keys include task/raw ID, while accepted credential quota/auth controllers are shared. New independent registries remain isolated, with no process-global account state. Complete valid output survives concurrent shared incidents; current-key privacy checks run again after awaited cleanup. Public/diagnostic IDs are checked after namespace masking as well as before it.

Strict embeddings/decisions admission requires all three zero prices and owned caps; additional/missing fees stay unknown. Rerank/speech remain externally gated. Four actual isolated source checks found catalog rows but zero admissible routes; no inference was sent. All nonchat monetary observation remains unavailable. Full T-010/AC-18 stays open. [Results and AC reconciliation](notes/T-010-results.md) own exact tests, source counts and candidate identity.

**Proposal only:** [T-010 v1.1.0](specs/T-010-free-variant-admission.md) would replace the task admission predicate with fresh exact catalog free-variant assurance, typed noncontradictory pricing and closed exact dispatch. It would distinguish provider-contract assurance from numeric-cap coverage, and allow optional speech voice/default pcm without invented model metadata. Approval is pending; none of these admission changes is as-built.

The accepted primary still serves its earlier T-009 process. A read-only health/OpenAPI check returned200 and showed none of the four T-010 task POST routes; no restart/configuration/account change occurred. Primary loading/target verification is a separate owner decision. T-008 and existing P2 exit obligations remain after disposition of this partial T-010 result.

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
* See [DEC-004: Benchmark Scoring Registry](docs/decisions/DEC-004-benchmark-scoring-registry.md) for the static curated benchmark store, script-assisted updates, and the `unranked` fallback governing P3.

## 8. Provider Validation API — As Built (T-006)

This section describes the implemented T-006 component; the broader architecture above remains a proposal for components not yet delivered.

`POST /api/admin/providers/validate` is mounted through `api/admin/__init__.py`. Its handler in `api/admin/providers.py` checks the optional master key before parsing the request or looking up providers. Input errors use fixed redacted envelopes. Request/report schemas live in `core/providers/validation_models.py`.

`core/providers/validation.py` runs three ordered checks: configuration, catalog, completion. It accepts a registered provider ID (including disabled providers) or an inline manifest. Registered providers may resolve their configured credentials; inline manifests require an explicit request-scoped key when authentication is needed. Overrides never enter Settings, the environment or the registry. Catalog rules support all_available, openrouter_free, regex and manual; selection uses sorted eligible raw IDs. A manual catalog does not perform a remote listing request. One fixed non-streaming micro-completion verifies protocol reachability, without claiming response quality or free pricing.

The service directly owns an asynchronous HTTP client with ambient proxy use and redirects disabled. Limits are 20 seconds for the combined network workflow, at most 10 seconds per HTTP stage, 1 MiB per decoded response and 100 reported model IDs. Failures stop subsequent stages and return safe diagnostics. Credentialed catalog/completion endpoints must share an origin. Local HTTP remains supported; full DNS/SSRF policy and untrusted-regex isolation are outside this scope.

Validation does not call CascadeRouter or the mutating discovery worker and does not change enablement, model cache, cooldowns, persisted configuration or chat telemetry. A ContextVar-based filter on HTTPX/HTTPcore loggers suppresses library HTTP diagnostics only within validation tasks, preventing URL/header leakage while preserving ordinary proxy logging. Application diagnostics expose no raw upstream bodies or completion text.

There is no new feature flag: the validation endpoint is mounted whenever the application runs, subject to its existing optional master-key policy. No external environment deployment is part of T-006. Reproducible external verification uses `scripts/probe_provider_validation.py`; evidence and limitations are maintained in [T-006 results](notes/T-006-validation-results.md).

## 9. Historical T-007 v1.1.0 checkpoint

Historical scope: static admission and fixed cooldown in this section were superseded by the dynamic/hybrid sections and T-009 in section1. Do not use them as current admission or recovery authority.

The lifespan runs one DiscoveryOrchestrator for configured manifests. OpenRouterDiscovery is a compatibility facade, not a second scheduled worker. Discovery owns isolated per-provider statuses and bounded HTTP resources, with four slots, no overlapping cycles, a 15-second provider deadline and 4 MiB decoded-body cap. Complete OpenAI data lists atomically replace a provider snapshot; failures preserve the previous snapshot until stale. Explicit continuation markers fail as incomplete rather than publishing partial catalogs. Cloudflare is unsupported_profile, Cerebras excluded and GitHub retired before network work.

ProviderRegistry keeps raw snapshots, success timestamps, exact aliases and in-memory policy. Eligible reads recheck freshness (twice the poll interval), enabled state, credential presence, secret-reflected IDs and free/chat admission without network/filesystem I/O. Cloud inference requires free_access_confirmed plus exact chat_model_allowlist; built-in local auth-none Ollama and OpenRouter with openrouter_free are specific exemptions. Validation remains separate and cannot activate admission. Owner subsequently authorized persisted Groq/NVIDIA admission for openai/gpt-oss-20b (free_access_confirmed=true and a one-model allowlist); other cloud policy gates remain false/empty. Manifest changes take effect after backend restart. Earlier live probe overrides were process-local.

Unknown canonical IDs are provider-qualified. Exact aliases join verified identities without inventing availability. Routing resolves exact canonical/raw IDs before a unique case-insensitive compatibility fallback; ambiguous raw requests fail safely. Same-model candidates precede alternatives; each tier interleaves providers using optional routing_provider_priority then alphabetical order. max_failover_attempts defaults to three and accepts 1..10. Eligibility is rechecked immediately before each attempt, including after an earlier pending attempt. Fixed cooldown semantics remain; adaptive recovery is not delivered here.

The universal adapter buffers until first content, retries initiation errors safely, masks model IDs and emits one DONE on successful SSE. Explicit stream ownership spans adapter, router and response handler so cancellation/early downstream disconnect closes even a prebuffered upstream not yet iterated downstream. Diagnostics redact upstream bodies/keys; task-scoped HTTP library filtering prevents credentialed URL leakage. create_app accepts an isolated registry for normal-lifespan tests/probes without replacing routing.

Delivery evidence, effective gates, conditional provider limitations and candidate hashes are maintained in [T-007 results](notes/T-007-results.md). Timings are observations; zero-I/O listing is the verified invariant. No remote deployment occurred; Gemini live delivery and other missing prerequisites remain explicitly unverified.

## 10. T-007 dynamic eligibility — v1.2.0 implementation history

This section supersedes section 9's historical static admission behavior. The saved candidate follows the owner-approved [v1.2.0 correction](specs/T-007-dynamic-free-eligibility.md); [results](notes/T-007-results.md) identifies verified bytes. That original candidate record did not constitute deployment/acceptance; subsequent accepted integration is recorded in section1 and results.

ProviderRegistry owns EligibilityStore and BillingGuard. Raw bounded catalog visibility is separate from current eligibility. Source records bind provider/raw ID to normalized inference endpoint, credential epoch, exact source endpoint/auth configuration and source profile. Epochs are private in memory; no stable key fingerprint is persisted/exposed. Catalog registration alone does not certify admission. Legacy flags cannot grant eligibility; an optional legacy list only narrows a certified set. Aliases remain identity assertions.

DiscoveryOrchestrator is the single lifespan worker, with independent catalog and eligibility due times. Evidence refresh fetches the actual source and cannot freshen catalog age; catalog success cannot certify old prices. Defaults are 60-second evidence refresh and 120-second TTL; failures/cancellation clear affected proof, exact expiry excludes it. Fetch limits are four concurrent/15-second operations, 30-second cycle and 4 MiB decoded document; at most 1000 model records per provider. Contradictory duplicate IDs cannot certify first-wins prices. No NVIDIA page parser or speculative local provenance classifier is delivered.

The closed text_chat_v1 request validator checks original JSON, including tools and nested structural fields; JSON Schema stays inert. Unknown fields/paid add-ons fail with unsupported_free_request before inference. OpenRouter zero ceilings and require_parameters=true are injected only for its exactly bound declarative source profile, on every dispatch/failover. They are not generic additions to other OpenAI-compatible payloads. Credential/source binding changes revoke prior evidence before requests/listings.

BillingGuard shares holds across all models in provider/endpoint/credential scope. It inspects only documented operator-charge fields, never synthetic token estimates. Positive/invalid recognized charges latch; fixed balance holds permit a single bounded post-expiry user attempt, with failed recovery renewing the hold. Complete valid buffered/SSE answers survive cancellation and cost incidents and finish normally; incomplete pre-output work may fail over; started semantic text/tool/reasoning streams never replay and interrupt safely when needed. Stream ownership extends through terminal framing/downstream close and finalizes one delivery trace; billing incidents are separately redacted operational events. Pending I/O cancellation retains responsibility for a concurrently produced response. No telemetry schema/store change or durable incident database is added.

All listing/admission reads are in memory. Operational probe evidence mode exposes safe aggregate basis/reason/age/hold metadata without new public APIs; no CLI flag grants free eligibility. Localhost/auth-none cannot certify local execution because Ollama can forward cloud requests. Under the owner-approved [v1.2.1 amendment](specs/T-007-openrouter-price-evidence-amendment.md), absent OpenRouter request pricing may use catalog_zero_tokens_with_request_ceiling / free_enforced when prompt/completion are explicitly zero and the exact source/auth/inference binding and owned zero-ceiling policy are active. Missing is never rewritten to zero. Present invalid fees and unknown/conditional pricing remain excluded. One policy builder drives dispatch and capability checks; policy loss removes this basis from listing/admission/request support. No other provider profile changes.

Current OpenRouter evidence requires output_modalities exactly ["text"]. A contains-text test admitted music text+audio endpoints with zero token prices but documented song charges; their generic provider INVALID_ARGUMENT was relayed as OpenRouter 400 and isolated-proxy 503. The exact rejected argument was not disclosed. Mixed outputs now remain unknown / unsupported_output_modality; no model-ID list or description-price parser. This owner-authorized conservative repair narrows the historical v1.2.0 capability predicate. Dispatch retains canonical string "0" for prompt/completion/request/image max_price plus require_parameters=true.

The dated OpenRouter snapshot admitted18/468 offers. Corrected live buffered/SSE proof passed with visible output, reported usage.cost=0, current admission, one attempt each and all caps verified. A protocol-valid empty/reasoning-only result no longer counts as probe delivery proof; runtime complete-answer/no-replay semantics are unchanged. Probe supports bounded diagnostic candidate selection and auto/cascade checks without changing production routing/order or saved model configuration. Full T-007/P2 and other account/provenance gates remain open. On 2026-10-23 the owner accepted the repair and authorized primary local activation. No project backend was running; ordinary uvicorn now serves127.0.0.1:8001 (port 8000 is unrelated oMLX), with actual primary buffered/SSE delivery verified at 32-token caps and reported zero cost. Runtime policy/evidence hashes match accepted source. Service remains running; no config/keys/accounts or external hosting changed.


## T-007 hybrid account admission — implementation and integration history

Owner accepted the hybrid design on 2026-10-23; the [complete correction](specs/T-007-hybrid-account-eligibility.md) was subsequently owner-approved with H1–H4 and the bounded isolated live packet; implementation/source/fairness repair has passed412 independent backend tests. Owner subsequently accepted the NVIDIA repair and authorized primary Groq/NVIDIA/Mistral integration; actual primary buffered/SSE delivery is verified for allthree. The historical OpenRouter-only runtime is superseded for this explicitly enabled local instance; shipped defaults remain unconfirmed. The candidate implements default-empty FREE_ACCOUNT_CONFIRMATIONS for Groq/NVIDIA/Mistral/HF, scope-bound user assertions, private buffered/SSE probe permits, independent source/probe expiry and a bounded dynamic active subset. Account-mode assurance is user_asserted, not provider-certified pricing. HF evidence/dispatch is pinned to an exact model/provider row while financial holds remain credential/account-wide. Strict OpenRouter caps and complete-answer/no-replay semantics are unchanged. Existing orchestrator lifecycle owns the worker; no new public endpoint, main.py change, storage or primary activation is proposed.

Candidate qualification uses raw strict text framing and shared owned I/O/guard hooks, separate from ordinary delivery. Runtime-owned budgets survive worker recreation; new/renewal selection alternates available partitions. A local reservation deferral preserves existing expiry, while a sent failed renewal revokes it. Full-pool exploration replaces only after a fresh pair passes; source-cache restoration uses vacancies only. Nullable absent tool calls are valid in normal text responses/deltas; malformed calls and nontext qualification remain rejected. See results for historical pre-fix live hashes, current post-fix Mistral PASS and unresolved NVIDIA/HF delivery gates.

NVIDIA/Mistral follow-up: fixed-shape probe diagnostics retain no raw upstream text/IDs. NVIDIA404 matching the observed function-not-found-for-account pattern reuses the one-hour per-route negative cache; it never establishes a financial hold or infers account-wide entitlement loss. CLI candidate offsets and reduced send ceilings are diagnostic only. At that intermediate checkpoint Mistral raw qualification and ordinary proxy buffered/SSE passed after nullable-call handling; NVIDIA was still unverified. The later NVIDIA and primary proofs below supersede that intermediate gap. Public documentation intersections are research selection aids, not production eligibility sources.

Owner-authorized NVIDIA Free Endpoint repair supersedes the preceding NVIDIA candidate-selection limitation. `discovery/nvidia.py` narrows the keyed API catalog by a complete public NGC ENDPOINT snapshot: exact publisher/name, public/AVAILABLE/PREVIEW, Free Endpoint/chat labels and no deprecation. It never guesses a slug alias, fetches a provider-supplied URL, infers tools or certifies an account tariff. The orchestrator fetches both sources within one15s deadline with4MiB-per-body bounds; source errors/removal revoke admission through the existing account lifecycle. Explicit HTTP requests and `auth=None` prevent client-default headers/auth/cookies from leaking to public NGC or overriding keyed catalog auth. Existing private both-mode qualification, assertion/guard/lease gates and universal chat adapter remain. Fresh independent regression411 tests passes; actual first NVIDIA buffered/SSE qualification and ordinary proxy delivery now PASS under user_asserted assurance, cost unavailable. Primary activation remains separate; current live exploration details belong in results.

Primary integration checkpoint: owner-authorized FREE_ACCOUNT_CONFIRMATIONS=["groq","nvidia_nim","mistral"] is persisted only in the ignored real.env and matched by the launched process. At the original T-007 integration, ordinary uvicorn PID3119 served127.0.0.1:8001 (subsequently replaced by T-009 PID33541) with the normal discovery/probe lifecycle. During cold start, advancing the provider cursor on every idle poll phase-locked10 manifests with60s budget windows and starved NVIDIA. The AC-H8 fix advances it only after actual task scheduling; quotas/concurrency/guards are unchanged. Independent412 tests and a three-window/idle regression pass. Allthree providers passed actual primary buffered/SSE with visible text, exact intended-provider telemetry and oneDONE. [Primary evidence](notes/T-007-primary-activation.md) supersedes earlier primary-inactive statements in historical checkpoint sections. HF is unconfirmed, OpenRouter strict, other deferred/skipped profiles unchanged. Consumer checks ended; normal bounded background qualification and the primary remain running. No external deployment or account/billing/key change.
