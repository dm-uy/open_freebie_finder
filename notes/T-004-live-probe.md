# T-004 / P1 Live Probe Report (2026-10-22)

Verification of the P1 "Done When" criterion against a real upstream, run by the reviewing agent on owner request after the review-fix commit `9b852f6` (26 tests passing).

## Environment

- Server: `uvicorn` (real HTTP socket) started from an in-process warm-up script (`/tmp/offer_live_probe_server.py`, temporary, not part of the codebase) that ran `OpenRouterDiscoveryService.discover_free_models()` once before serving, because the app lifespan does not yet schedule discovery at startup (known gap, see Findings).
- `OPENROUTER_API_KEY` present in local `.env` (value never printed or committed).
- HEAD at probe time: `9b852f6`.

## Results

1. **`GET /health`** → `200 {"status": "healthy", ...}` — PASS.
2. **`GET /v1/models`** → `200`, 21 entries: `auto:free` + 20 discovered canonical free models (samples: `recursive/flint-v1.0`, `nvidia/nemotron-3.5-super-vl`, `liquid/lfm-2.5-2.6b`) — PASS (real socket, real discovery data).
3. **`POST /v1/chat/completions` (buffered, `model: "auto:free"`)** → real completion from a live OpenRouter free model (Cohere): `content: "Hello!"`, `finish_reason: "stop"`, `usage` present with `cost: 0`, `model` masked to `auto:free` — **PASS: the core P1 Done-When condition (valid response from an OpenRouter free model via a real HTTP request) is satisfied.**
4. **`POST /v1/chat/completions` (`stream: true`)** → valid SSE: 47 content chunks, all masked `"model": "auto:free"`, single terminating `data: [DONE]` — PASS.
5. **Live 429 interception** → **UNVERIFIED (upstream never returned a 429)**: 12 sequential + 25 sequential + 40 parallel requests (the last two bursts against a single model `cohere/north-mini-code`) all returned `200`, and the server log contains no failover events. Upstream rate limits were not reached during the probe window. Transparent 429 failover remains verified only at the mocked/ASGI level (reviewer probes, `test_cascade_failover.py`), not against a real upstream.

## Findings (probe-specific)

- **F-1 (medium):** `backend/app/main.py` lifespan is empty — discovery is not scheduled at startup or on an interval. A freshly started server serves only `auto:free` in `/v1/models` and returns 404 for `auto:free` completions until something warms the cache. The ROADMAP P1 deliverable names an "automated discovery worker"; the worker exists but is not wired into the app lifecycle. Recommend scheduling it (startup run + periodic task, `DISCOVERY_INTERVAL_SECONDS=900`) as a small follow-up task in P1/P2.
- **F-2 (observation):** auto:free may route to reasoning-first free models; with small `max_tokens` the first candidate can return `content: null` with only `reasoning` populated. The router does not currently treat a `content: null` 200 as a failed candidate (not an AC; note for quality routing in P3).

## Verdict

P1 "Done When" is satisfied for the primary condition (real curl request → valid OpenRouter free-model completion). The secondary condition (intercepted live 429 → transparent failover) is verified at the mocked level only and could not be reproduced against the live upstream within the probe window. Phase closure under this evidence is an owner decision.
