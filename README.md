# Open Freebie Finder

A local API proxy that discovers eligible LLM models and routes text chat requests across them, with bounded failover and streaming support.

You supply provider credentials. Applications talk to one OpenAI-compatible Chat Completions endpoint. The backend maintains the eligible pool and avoids temporarily failing routes. It does not host model weights or require a dashboard.

**Status: backend preview.** The proxy, discovery, conditional account qualification, telemetry, validation API and adaptive circuit breaker are implemented. A React dashboard, onboarding agent, quality-based routing and Docker packaging are planned. This is a supported subset of the OpenAI-style API, not a complete replacement for every OpenAI endpoint or client feature.

Licensed under [MIT](LICENSE).

## Contents

- [What works today](#what-works-today)
- [Quick start](#quick-start)
- [Send requests](#send-requests)
- [Task APIs and catalogs](#task-apis-and-catalogs)
- [Connect an application](#connect-an-application)
- [Configure providers](#configure-providers)
- [What free eligibility means](#what-free-eligibility-means)
- [Routing, failures and recovery](#routing-failures-and-recovery)
- [Settings](#settings)
- [Inspect and troubleshoot](#inspect-and-troubleshoot)
- [Advanced diagnostics](#advanced-diagnostics)
- [Development and project records](#development-and-project-records)

## What works today

| Available | Behavior |
|---|---|
| `GET /health` | Service liveness; not proof that a provider can generate |
| `GET /v1/models` | In-memory eligible model catalog and the `auto:free` alias |
| `POST /v1/chat/completions` | Buffered JSON and SSE text chat |
| Dynamic discovery | Provider-specific source checks; no manually maintained model admission lists |
| Cascade routing | Tries eligible alternatives within a configured attempt limit |
| Adaptive recovery | Route backoff, credential quota pauses, inference-401 lockout and one recovery attempt at a time |
| Admin telemetry | Recent request traces and aggregate counters |
| Provider validation | Separate request-scoped diagnostics; does not activate a provider |

**Not delivered:** `auto:quality`, `auto:fast`, `auto:code`, benchmark ranking, context-aware model selection, automated provider onboarding, React UI, Docker distribution, prompt caching and persistent operational storage. Current operational state is in memory. A bundled provider manifest or environment variable does not establish a working free-generation profile.

**T-010 source candidate:** separate embeddings, rerank, decisions and speech APIs/catalogs are implemented and locally verified, with strict external admission gates. The earlier running primary has not been restarted to load them. Positive external free delivery is still unverified; see [task results](notes/T-010-results.md).

## Quick start

Requirements: Python 3.11+, a shell, internet access to the selected provider and a usable provider key. Run the following from the repository root. These commands use a POSIX shell; use your platform's virtual-environment executable paths if they differ.

### 1. Install dependencies

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
```

### 2. Create local configuration

For a **new checkout without an existing `.env`**:

```sh
cp .env.example .env
```

If you already have `.env`, edit it in place rather than overwriting it. For a minimal OpenRouter setup, fill these entries in that file:

```dotenv
OPENROUTER_API_KEY=replace-with-your-openrouter-key
PROXY_MASTER_KEY=replace-with-a-long-random-local-password
FREE_ACCOUNT_CONFIRMATIONS=[]
```

Use actual local values, not the placeholders. The provider key authenticates upstream inference; the proxy password authenticates your application to this service. They are different credentials. Keep `.env` private and out of Git; only `.env.example` belongs in shared configuration.

OpenRouter uses the strict eligibility profile described below. You do not need to enable conditional account mode to use it. A key still needs usable provider access/quota; the proxy cannot create access or guarantee that a free model is currently available.

### 3. Start the backend

```sh
.venv/bin/python -m uvicorn backend.app.main:app \
  --host 127.0.0.1 --port 8001 --log-level warning --no-access-log
```

Keep this terminal running. Use another terminal for requests. If the port is occupied, select another port and update your client URL. The explicit Uvicorn flags select the listening address/port; editing `.env` `HOST`/`PORT` alone does not change this command.

The startup worker discovers eligible routes. Conditional account profiles also need background qualification, so admission may take longer than service startup. Do not repeatedly restart to hurry it up.

### 4. Check readiness

In the second terminal, set the same proxy password you put in `.env`:

```sh
export OFF_PROXY_KEY='the-same-value-as-PROXY_MASTER_KEY'
export OFF_BASE_URL='http://127.0.0.1:8001'

curl -sS "$OFF_BASE_URL/health"
curl -sS "$OFF_BASE_URL/v1/models" \
  -H "Authorization: Bearer $OFF_PROXY_KEY"
```

A healthy service may still have no eligible upstream model. `/v1/models` always includes the synthetic `auto:free` entry; that entry alone is not generation readiness. Wait for actual model entries and check your configuration if none appear. A listed model may also be temporarily paused by health protection.

The guide binds the service to loopback. If `PROXY_MASTER_KEY` is empty, chat and admin routes do not enforce a password. When set, it protects chat/admin routes; `/health` and `/v1/models` remain unauthenticated. This is not a complete multi-user authorization system. Do not treat the local example as a public-internet deployment recipe.

## Send requests

### Buffered chat

```sh
curl -sS "$OFF_BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $OFF_PROXY_KEY" \
  -H 'Content-Type: application/json' \
  -H 'X-Request-ID: my-first-request' \
  -d '{
    "model": "auto:free",
    "messages": [{"role": "user", "content": "Reply with one short greeting."}],
    "max_tokens": 32,
    "stream": false
  }'
```

The answer is in `choices[0].message`. The response model name matches the requested alias/model; use telemetry to see which provider and raw model actually served it. The response includes `X-Request-ID`; supply a unique ID per request or let the server generate one.

`32` is a small example output budget, not a proxy-wide limit on user requests. Health probes have their own fixed 32-token cap. Short budgets can be consumed by reasoning before a model produces visible text; a protocol-valid empty answer is not proof of useful output. The current router does not rank models by answer quality or reasoning behavior.

### Streaming chat

```sh
curl -N -sS "$OFF_BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $OFF_PROXY_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "auto:free",
    "messages": [{"role": "user", "content": "Reply with one short greeting."}],
    "max_tokens": 32,
    "stream": true
  }'
```

Read `data:` events until `data: [DONE]` on normal completion. Failover can happen before output begins. Once semantic output starts, the proxy will not start another model and replay the response. An incomplete interrupted stream may end with a redacted error event and no DONE; clients must handle that case.

### Request a catalog model

Replace `auto:free` with an `id` from `/v1/models`. The router prefers eligible routes for that canonical model, then may try other models if those routes fail. An explicit model name is therefore a preference, **not an exact-model/no-fallback guarantee**. Different models can produce different behavior.

Requests support the validated text-chat profile. Images, audio, arbitrary provider routing overrides and unknown request fields are rejected. Function tools have validated shapes and additionally require observed tool support in the current eligibility profile. Structured-output request shapes (`response_format`/JSON Schema) are validated, but there is no separate per-model structured-output capability check; upstream support is not guaranteed. Multiple-choice generation (`n > 1`) is unsupported.

## Task APIs and catalogs

The T-010 source candidate adds the following endpoints. They are available when running this source checkout; loading them into an existing service needs a deliberate restart. They are not an assertion that a free upstream currently exists.

| Endpoint | Supported subset |
|---|---|
| `POST /v1/embeddings` | Text or up to32 text inputs, float vectors; exact model, no cross-model/vector-space fallback |
| `POST /v1/rerank` | Text query/documents and optional top_n; indexed relevance results |
| `POST /v1/decisions` | Text state and typed choice/score/noul questions; upstream OpenRouter alpha Decisions protocol |
| `POST /v1/audio/speech` | Short text, preset voice and explicit mp3/pcm; whole bounded audio response |
| `GET /v1/models?task=embeddings` | Eligible models for that task only; other values rerank, decisions, speech or chat |
| `GET /api/admin/models/catalog?task=all` | Safe diagnostic inventory, including paid/unknown and operationally blocked rows; existing optional master-key auth |

The default `/v1/models` remains chat-only, including `auto:free`. Do not add nonchat models to a chat client's picker. Task model IDs use `openrouter::<raw-id>`; take them unchanged from the matching eligible task list. There are no automatic task aliases, and no silent substitution of embedding model, reranker, decision model or voice. An unchanged embedding ID does not guarantee the provider never changes its weights: applications own index versioning/rebuilds.

```bash
curl -sS "$OFF_BASE_URL/v1/models?task=embeddings"
curl -sS "$OFF_BASE_URL/api/admin/models/catalog?task=all" \
  -H "Authorization: Bearer $OFF_PROXY_KEY"
```

**Current free gates:** embeddings/decisions require explicit zero prompt/completion/request prices, no additional unverified fee keys, exact source/task binding and owned zero-price routing controls. The chat omitted-request-price exception does not apply. Rerank/speech remain `unknown / unsupported_enforcement` until a sourced, approved policy amendment. Direct-provider account confirmations and chat qualification do not activate any new task. Task monetary reporting is unavailable; a field named cost is not automatically interpreted as an operator charge. The diagnostic catalog can therefore contain models while an eligible task list is empty.

All new task requests use closed field subsets; provider routing/options, token or multimodal inputs, cloning/references, streaming fields and unknown fields return400 before inference. Optional embedding dimensions require explicit capability evidence, currently absent from the inspected catalog. Speech additionally requires proven voice/format capabilities. Known but nonfree/unknown/stale/guard-blocked targets return503; unknown IDs404; invalid upstream protocol502. All responses carry a correlation ID. Inputs are bounded to256KiB; complete upstream bodies/audio to8MiB and requests to30 seconds, with at most15 seconds for the one exact route attempt. Once output starts it is never replayed or spliced. Exact field/count limits are in the [approved contract](specs/T-010-task-specific-inference.md).

Safe isolated diagnostics default to zero inference sends:

```bash
.venv/bin/python scripts/probe_task_inference.py \
  --task embeddings --max-sends 0 --output /tmp/t010-embeddings-preflight.json
```

Exit2 with `UNVERIFIED` is expected when evidence is insufficient. The optional max-sends1 mode is the specification's finite live packet: one send per task/four total, guarded by a persistent private ledger at `/tmp/t010-live-budget.json`; it cannot grant admission. Do not remove/reset that ledger to bypass the approved budget. Unlike chat probes, these APIs do not share a universal32-output-token parameter; their probe inputs have separate small bounds. Reports contain safe metadata, never vectors/audio/prompts or keys.

## Connect an application

For an application that supports a configurable OpenAI-style **Chat Completions** backend:

| Client setting | Value |
|---|---|
| Base URL | `http://127.0.0.1:8001/v1` |
| API key | Your local `PROXY_MASTER_KEY` value |
| Model | `auto:free`, or an ID from the model catalog |
| Endpoint style | Chat Completions, not Responses/Assistants/embeddings |

Do not append `/chat/completions` to an SDK base URL that already builds that path. A browser-based or remote client must be able to reach the machine running the proxy; its own `localhost` may refer to a different machine. Additional network exposure/authentication is a separate deployment concern.

Compatibility depends on the fields the client sends. A client using unsupported extensions can receive `400 unsupported_free_request`; adding a compatible base URL alone does not certify every feature of that client. Start with the small text request above before testing richer tools or integrations.

### DeepSeek Harness

Use **Custom model API**, base URL `http://127.0.0.1:8001/v1`, protocol **OpenAI Chat Completions**, your proxy password and model `auto:free`. Harness can default to sending `store:false` for a generic endpoint; this is outside the proxy's closed request profile and causes400 before upstream dispatch.

In Harness's own configuration, add these fields inside this custom provider, preserving its existing URL, API-key reference and model entries:

```yaml
cacheRetention: none
compat:
  supportsStore: false
  supportsReasoningEffort: false
  maxTokensField: max_tokens
  supportsDeveloperRole: false
  requiresThinkingAsText: true
```

These are **Harness settings**, not proxy `.env` entries or backend manifest flags. Reload its configuration (restart Harness if needed), reselect the provider and start with a new text-only conversation. This profile has been checked with offline request construction/validation; a complete Harness agent/tool workflow has not yet been certified. It does not grant image/audio support or tool capability to an upstream model. [Diagnosis and verification boundaries](notes/harness-client-compatibility.md).

## Configure providers

Settings are read from the process environment and `.env` in the working directory; process environment values take precedence. Stop the server with Ctrl+C, edit configuration, and deliberately restart after changing keys/assertions. There is no implemented key-management dashboard or automatic provider onboarding.

| Provider/profile | Key variable | What else is required / current evidence |
|---|---|---|
| OpenRouter | `OPENROUTER_API_KEY` | Strict current source/enforcement checks; buffered/SSE delivery verified |
| Groq | `GROQ_API_KEY` | Explicit nonbillable-account assertion and current dynamic qualification; delivery verified |
| NVIDIA NIM | `NVIDIA_API_KEY` | Same assertion/qualification plus fresh exact Free Endpoint catalog intersection; delivery verified |
| Mistral | `MISTRAL_API_KEY` | Same assertion/qualification; delivery verified |
| Hugging Face | `HUGGINGFACE_API_KEY` | Conditional profile implemented; account-side billing/BYOK checks required; positive delivery remains unverified in project evidence |
| Gemini | `GOOGLE_AI_STUDIO_API_KEY` | Manifest/key slot exists; generation profile/live obligations deferred, not advertised as working |
| OpenCode / Kilo | No delivered activation contract | Earlier research/keys do not establish integration |
| Local Ollama / cloud-forwarded Ollama | No positive delivered provenance profile | `localhost` does not establish local execution or free cloud entitlement |
| Cloudflare / Cerebras / GitHub Models | Historical slots may exist | Unconditional skips in the current implementation; keys do not activate them |

These are project implementation/evidence statuses, not promises about a provider's current plans, prices or quotas. See [provider evidence](notes/T-007-primary-activation.md) and [remaining scope](notes/next-steps-current-checkpoint.md).

### Optional conditional account mode

After checking the actual account billing path, add the chosen provider keys and replace the default empty array with provider IDs, for example:

```dotenv
GROQ_API_KEY=replace-with-your-groq-key
NVIDIA_API_KEY=replace-with-your-nvidia-key
MISTRAL_API_KEY=replace-with-your-mistral-key
FREE_ACCOUNT_CONFIRMATIONS=["groq","nvidia_nim","mistral"]
```

Allowed IDs are `groq`, `nvidia_nim`, `mistral`, `huggingface`. The setting must be a JSON array of distinct allowed strings, not a comma-separated string. Never add OpenRouter or model IDs to it. Default is `[]`; copied project examples do not enable these accounts for you.

**What you assert:** the actual credential's billing path cannot incur operator-paid inference: only free/included gratis allowance, with paid overflow/PAYG/postpaid/auto-recharge disabled, no purchased credit balance being consumed, and no third-party billing/BYOK/organization bill-to path. Exhaustion must reject rather than continue into paid usage. Empty balance or no payment card alone is insufficient. For HF, verify account-side provider/BYOK preferences too. The proxy's ordinary inference key does not machine-prove those account settings.

Remove the assertion and stop/restart **before** enabling paid features or changing the billing path. An observed in-process key/source/auth/profile change revokes the assertion until deliberate restart, even if the original key is restored. Retaining an assertion through restart declares it again for the loaded key; it does not prove continuity of the account's plan. A false/stale assertion can incur a charge, including on the first probe, and the proxy cannot undo it.

## What free eligibility means

There are two different assurance levels:

| Mode | Admission basis | Limit |
|---|---|---|
| Strict OpenRouter | Fresh exact-bound source evidence plus owned zero-price routing ceilings | Only covered source/request features are admitted; unknown/invalid pricing or unsupported modalities are excluded |
| Conditional account mode | Operator assertion plus fresh catalog and successful buffered/SSE availability qualification | Proves availability under that assertion, not a zero model rate or provider-certified nonbilling |

OpenRouter chat requests retain zero ceilings for prompt/completion/request/image and `require_parameters=true`. The proxy does not retry without these constraints. The approved omitted-request-price case relies on enforcement; missing price is not rewritten as explicit zero. Mixed text+audio outputs and unsupported fees are excluded.

For opted-in accounts, the worker discovers model routes dynamically and requires both buffered and SSE text probes before admission. Each probe requests at most32 output tokens. At most five healthy routes per provider are active; the worker gradually explores/replaces candidates within fixed budgets. No model-ID list is maintained in YAML, and legacy `free_access_confirmed`/`chat_model_allowlist` fields do not certify the four account profiles.

Default source refresh/TTL are60/120 seconds. A successful account pair has a24-hour lease, renewed after12 hours; a catalog refresh cannot extend it. Failed renewal revokes the pass; queue deferral preserves it only until existing expiry. NVIDIA additionally requires a fresh public, available, preview, nondeprecated chat endpoint with an exact publisher/name match to the keyed catalog. Missing/partial/invalid evidence excludes the candidate rather than guessing a route.

Qualification consumes included allowance. Its fixed bounds include four sends/minute globally and two/provider,192/day globally and96/provider,64 new-candidate and128 renewal sends/day globally, two simultaneous pairs globally and one/credential. These are **private qualification** bounds, not ordinary user-request quotas or a durable spending limit.

The cost guard recognizes only implemented documented charge mappings, currently OpenRouter chat operator `usage.cost`. New task monetary mappings remain unavailable. Effective monetary reporting for the four account profiles is `unavailable`, never synthetic zero or invented savings. Account-side changes invisible to the key cannot be automatically detected. Neither successful HTTP responses nor absence of reported cost establishes free pricing.

## Routing, failures and recovery

`auto:free` selects eligible routes using configured provider priority and deterministic provider/model ordering, not benchmark quality or fastest-response measurement. Each request can make up to `MAX_FAILOVER_ATTEMPTS` actual attempts. Failover can consume provider allowance more than once for one client request.

- Service/network/timeout failures pause the affected route with exponential backoff, default60→120→240→480→900 seconds. After expiry, one real recovery attempt is allowed at a time; concurrent requests can try alternatives.
- A nonfinancial429 conservatively pauses sibling routes in the same credential scope. Supported `Retry-After` hints may extend pauses; very large/oversized hints defer automatic recovery rather than being silently shortened.
- An inference401 locks the rejected credential identity. A successful catalog refresh or source/profile change does not unlock it. Correct the credential/account and deliberately restart; do not repeatedly retry the same rejected key.
- Nonfinancial route/protocol incompatibilities use bounded quarantine rather than credential-wide auth lockout. Private qualification also retains its specific negative caches.
- Financial holds/latches are stronger than all health recovery. A billing/balance hold suppresses automatic qualification, even after transient expiry; private probes do not recover account balances. A real user request may perform existing bounded transient financial recovery only while its route remains valid. Positive/invalid recognized cost latches are not cleared by successful health checks.

A valid complete answer is delivered even if an observed charge blocks future requests. An already started incomplete SSE is not replayed. A health pause never creates free eligibility, restores an assertion or extends a lease.

State, budgets, telemetry and guards are process-local/in memory. Restart recreates them; multiple workers do not share protection or quotas. The documented setup uses one Uvicorn process. Do not use restarts, extra workers or diagnostic processes to evade a known financial incident or exhausted allowance. Resolve the account condition first; this is not a durable or distributed spend firewall.

## Settings

All entries below are configured through your environment/`.env`. See [.env.example](.env.example) for placeholders; do not copy actual keys into tracked files.

| Setting | Default | Meaning |
|---|---|---|
| `PROXY_MASTER_KEY` | empty | Optional password for chat/admin routes; set it for your installation |
| `FREE_ACCOUNT_CONFIRMATIONS` | `[]` | Explicit conditional account assertions, as described above |
| `MAX_FAILOVER_ATTEMPTS` | `3` | Actual attempts/client request, strict integer1..10 |
| `ROUTING_PROVIDER_PRIORITY` | `[]` | JSON array of distinct exact provider IDs; listed providers precede remaining alphabetical providers |
| `CIRCUIT_BREAKER_COOLDOWN_SECONDS` | `60` | Recovery base, strict integer1..300; local exponential cap900s |
| `DISCOVERY_INTERVAL_SECONDS` | `900` | Ordinary catalog cycle interval; distinct from dynamic eligibility refresh |
| `ELIGIBILITY_REFRESH_SECONDS` | `60` | Eligibility source refresh, integer10..300 |
| `ELIGIBILITY_TTL_SECONDS` | `120` | Evidence TTL, integer20..600 and at least twice refresh |

Do not increase intervals or add a flag to certify otherwise unknown pricing. Unsupported provider profiles stay excluded even if keys or legacy manifest flags are present. Advanced manifests/identity aliases live under `backend/app/core/providers/`; configuring an endpoint is not implementing its source/dispatch/free-policy contract.

## Inspect and troubleshoot

Automatic FastAPI API documentation is available at `http://127.0.0.1:8001/docs`. It explains endpoint shapes; protected API calls still need the configured bearer password. It is an API explorer, not the planned dashboard. Read-only telemetry examples:

```sh
curl -sS "$OFF_BASE_URL/api/admin/telemetry/recent?limit=20" \
  -H "Authorization: Bearer $OFF_PROXY_KEY"
curl -sS "$OFF_BASE_URL/api/admin/telemetry/stats" \
  -H "Authorization: Bearer $OFF_PROXY_KEY"
```

Use request correlation IDs to match failures and see actual provider/model attempts. Telemetry is bounded in memory and resets with the process; it is not a persistent billing ledger. Model listing shows eligibility, not a circuit-breaker snapshot. No public breaker-state/reset endpoint is implemented.

| Symptom | What to check |
|---|---|
| Only `auto:free` appears | Wait for discovery; check key variable, source connectivity and current profile. For conditional mode, check assertion and qualification. A key alone is insufficient. |
| `401` from the proxy | Match the bearer password to `PROXY_MASTER_KEY`; do not send the provider key as the proxy password. |
| `400 unsupported_free_request` | Try the basic text example; remove unsupported fields/modalities or features the admitted profile cannot support. |
| `404` model unavailable | The requested identity has no current eligible route, is unknown or has stale/revoked evidence. |
| `503` no usable route | Routes may be health/auth/capacity blocked, exhausted after attempts or unavailable. Inspect the correlated trace; zero attempts can indicate admission blocking. |
| SSE stops without DONE | Handle its redacted error event. Started output is not retried with another model. |
| Empty or reasoning-only answer | A short output budget may be insufficient; inspect the model's behavior or choose another catalog identity. No quality ranking/context guard is delivered yet. |
| Account models do not recover after a billing incident | Fix the account condition; health recovery/source refresh cannot clear financial protection. Never bypass it with another diagnostic process. |
| New key/settings have no effect | Check working directory/environment precedence, stop and deliberately restart. Changing only the file is not hot reload. |
| Address already in use | Keep the existing service, or select a free port and update the client URL. |

`POST /api/admin/providers/validate` can validate a registered provider or supplied manifest/request-scoped key. It does not persist keys, enable the provider or grant free eligibility. A requested validation includes a real micro-completion and can consume allowance or incur upstream cost; it is not the normal free-admission gate. Read [the implemented validation contract](specs/T-006-provider-validation-api.md) before using it. Do not click execution buttons in the API explorer expecting a read-only check.

## Advanced diagnostics

These commands can perform real inference. They are optional, separate from serving traffic, and should be used with a deliberate allowance/budget. New processes cannot inspect or clear the running service's in-memory holds.

Strict OpenRouter through an isolated normal proxy, one buffered/SSE packet, at most two attempts per mode and32 output tokens per attempt:

```sh
.venv/bin/python scripts/probe_multi_provider.py \
  --provider-id openrouter --mode proxy --generation both --max-attempts 2
```

This requires configured `MAX_FAILOVER_ATTEMPTS` to be at least2. A packet may stop early if it fails. It uses owned strict constraints and account confirmations[] in its isolated registry.

For an explicitly checked nonbillable account, an isolated account diagnostic:

```sh
.venv/bin/python scripts/probe_multi_provider.py \
  --provider-id groq --mode account --confirm-nonbillable-account
```

The flag accepts the same operator assertion as conditional account mode; it does not prove account pricing. Allowed IDs are `groq`, `nvidia_nim`, `mistral`, `huggingface`. The tool dynamically tries at most three qualification pairs and one actual proxy buffered/SSE pair, with at most eight inference sends/provider and32 output tokens/send. It does not activate the primary. Minute budgets can cause waits; output is safe metadata, not provider keys or response bodies.

Optional account controls: `--candidate-offset` selects a position in the fresh catalog, `--candidate-limit` is1..3 and `--send-limit` is1..8, lowering the packet ceiling. They select diagnostic candidates, not admission lists. Respect the total intended budget across repeated processes. Missing prerequisites or no usable route must be reported honestly as UNVERIFIED/failure rather than a mock pass. Use `--help` for the available modes; catalog/evidence inspection is not proof of live generation.

## Development and project records

Current runtime: Python, FastAPI, Pydantic and httpx with YAML configuration. Dependencies are in [backend/requirements.txt](backend/requirements.txt). Presence of a database dependency is not evidence of delivered persistent storage. Fresh installations must resolve those dependencies; the repository does not currently ship a dependency lockfile or container distribution.

Run local regression tests from the root:

```sh
.venv/bin/python -m pytest backend/tests -q
```

Some tests use temporary loopback TCP servers and require permission to bind local sockets. Files named `*_live.py` in this suite use controlled local fixtures; deliberate external inference is run through the separate diagnostic tools. Retained accepted T-009 evidence:493 full tests, independent81 focused tests, strict OpenRouter isolated buffered/SSE delivery and actual primary Groq buffered/SSE delivery. These are dated project proofs, not guaranteed provider availability or a fresh-install matrix. See [T-009 results](notes/T-009-results.md).

| Record | Purpose |
|---|---|
| [VISION.md](VISION.md) | Product goals and constraints |
| [ROADMAP.md](ROADMAP.md) | Phase outcomes and dependencies |
| [TASKS.md](TASKS.md) | Accepted, active and planned work |
| [HANDOFF.md](HANDOFF.md) | Current continuation state |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Current implementation versus historical/target design |
| [docs/decisions/](docs/decisions/) | Architectural decisions |
| [Current remaining route](notes/next-steps-current-checkpoint.md) | Next preparation and unresolved provider obligations |
| [PROJECT-PROCESS.md](PROJECT-PROCESS.md) | Lightweight project process |
| [AGENTS.md](AGENTS.md) | Contributor/agent operating instructions |

P2 onboarding and outstanding provider/provenance obligations remain open. P3 ranking, P4 dashboard and P5 packaging/cache work are planned; this README does not imply they are shipped. Changes to code or provider behavior follow the approved task/specification process. Never include real provider credentials in commits, issues or shared diagnostics.
