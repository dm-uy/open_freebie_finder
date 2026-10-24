# T-007 primary activation evidence

Date:2026-10-23. Owner accepted the NVIDIA discovery repair and explicitly authorized enabling Groq/NVIDIA/Mistral, local restart and buffered/SSE32-token checks. The accepted scope is now active on the main backend; full T-007/P2 remains open.

Primary: `http://127.0.0.1:8001`, PID3119, ordinary uvicorn in the project cwd, warning/no-access logging. Port8000 untouched. Health200. The normal lifespan performed cold source discovery and private both-mode qualification; no seeded models, fake evidence or isolated registry. NVIDIA became listed during the checker at183.8s.

Active runtime setting: `FREE_ACCOUNT_CONFIRMATIONS=["groq","nvidia_nim","mistral"]`, persisted in ignored real.env and explicitly matched in the launched process. Every other.env entry/key was preserved. Shipped default/example remains[]; HF remains unconfirmed. Strict OpenRouter is unchanged. Account assurance is user_asserted; effective cost reporting unavailable, never reported zero. Account-side billing settings were not changed.

| Provider | Buffered | SSE | Observed completion tokens, buffered/SSE | Attempts per check |
|---|---|---|---|---|
| `groq` | HTTP200 / visible PASS | HTTP200 / visible PASS / one DONE | 10 / 10 | 1, intended provider |
| `nvidia_nim` | HTTP200 / visible PASS | HTTP200 / visible PASS / one DONE | 9 / unavailable | 1, intended provider |
| `mistral` | HTTP200 / visible PASS | HTTP200 / visible PASS / one DONE | 32 / 32 | 1, intended provider |

All six final requests specified max_tokens32, used the actual primary HTTP API, and checked response correlation against its real admin telemetry: one successful intended-provider attempt each. No answer from a different fallback provider was counted. Raw responses, keys and upstream errors were not retained. The consumer checker exited after success; the primary and its normal bounded qualification worker remain running.

The activation also exposed and repaired AC-H8 scheduler starvation: rotating on every idle poll can phase-lock ten manifests with60s quota windows. Cursor now advances after actual task scheduling only. A deterministic old-code failure and three-window/idle regression cover the fix. Root targeted34 tests/1.11s and independent full412 tests/12.67s pass. Token/minute/day/concurrency/deadline/source/guard/cascade policies are unchanged. Only probes.py and its tests changed from activation baseline; protected7 T-006 files and main.py remain unchanged.

Initial PID1128 produced four successful Groq/Mistral ordinary checks before the checker was stopped for the fairness repair. Those captures are preserved separately. Final PID3119 then passed six new ordinary checks: ten ordinary verification requests across this activation, each cap32. The enabled background worker separately made private qualification requests under its fixed budgets; ten is not a total upstream inference count. An immediate pre-readiness health attempt sent no inference and required no additional restart. Process budgets/leases remain intentionally memory-only.

Final safe capture (retained observations):

```json
{
  "primary_port": 8001,
  "confirmations": [
    "groq",
    "mistral",
    "nvidia_nim"
  ],
  "health_status": 200,
  "elapsed_seconds": 185.9,
  "results": [
    {
      "provider": "groq",
      "stream": false,
      "http_status": 200,
      "passed": true,
      "visible_output": true,
      "done_count": null,
      "completion_tokens": 10,
      "request_max_tokens": 32,
      "attempt_count": 1,
      "all_attempts_target_provider": true,
      "attempts": [
        {
          "provider": "groq",
          "status": "success",
          "http_status": 200
        }
      ],
      "request_id": "t007-primary-groq-buffered-5e8aa715",
      "model_fingerprint": "7f068d98acedf530",
      "duration_ms": 464.36,
      "assurance": "user_asserted",
      "cost_reporting": "unavailable"
    },
    {
      "provider": "groq",
      "stream": true,
      "http_status": 200,
      "passed": true,
      "visible_output": true,
      "done_count": 1,
      "completion_tokens": 10,
      "request_max_tokens": 32,
      "attempt_count": 1,
      "all_attempts_target_provider": true,
      "attempts": [
        {
          "provider": "groq",
          "status": "success",
          "http_status": 200
        }
      ],
      "request_id": "t007-primary-groq-sse-010ecc68",
      "model_fingerprint": "7f068d98acedf530",
      "duration_ms": 507.08,
      "assurance": "user_asserted",
      "cost_reporting": "unavailable"
    },
    {
      "provider": "mistral",
      "stream": false,
      "http_status": 200,
      "passed": true,
      "visible_output": true,
      "done_count": null,
      "completion_tokens": 32,
      "request_max_tokens": 32,
      "attempt_count": 1,
      "all_attempts_target_provider": true,
      "attempts": [
        {
          "provider": "mistral",
          "status": "success",
          "http_status": 200
        }
      ],
      "request_id": "t007-primary-mistral-buffered-ab1399d1",
      "model_fingerprint": "41a92a7d61388a9d",
      "duration_ms": 842.73,
      "assurance": "user_asserted",
      "cost_reporting": "unavailable"
    },
    {
      "provider": "mistral",
      "stream": true,
      "http_status": 200,
      "passed": true,
      "visible_output": true,
      "done_count": 1,
      "completion_tokens": 32,
      "request_max_tokens": 32,
      "attempt_count": 1,
      "all_attempts_target_provider": true,
      "attempts": [
        {
          "provider": "mistral",
          "status": "success",
          "http_status": 200
        }
      ],
      "request_id": "t007-primary-mistral-sse-d532e979",
      "model_fingerprint": "41a92a7d61388a9d",
      "duration_ms": 1045.91,
      "assurance": "user_asserted",
      "cost_reporting": "unavailable"
    },
    {
      "provider": "nvidia_nim",
      "stream": false,
      "http_status": 200,
      "passed": true,
      "visible_output": true,
      "done_count": null,
      "completion_tokens": 9,
      "request_max_tokens": 32,
      "attempt_count": 1,
      "all_attempts_target_provider": true,
      "attempts": [
        {
          "provider": "nvidia_nim",
          "status": "success",
          "http_status": 200
        }
      ],
      "request_id": "t007-primary-nvidia_nim-buffered-4ddf523f",
      "model_fingerprint": "dedf501e6e1282bb",
      "duration_ms": 963.45,
      "assurance": "user_asserted",
      "cost_reporting": "unavailable"
    },
    {
      "provider": "nvidia_nim",
      "stream": true,
      "http_status": 200,
      "passed": true,
      "visible_output": true,
      "done_count": 1,
      "completion_tokens": null,
      "request_max_tokens": 32,
      "attempt_count": 1,
      "all_attempts_target_provider": true,
      "attempts": [
        {
          "provider": "nvidia_nim",
          "status": "success",
          "http_status": 200
        }
      ],
      "request_id": "t007-primary-nvidia_nim-sse-ee31fa5a",
      "model_fingerprint": "dedf501e6e1282bb",
      "duration_ms": 1130.95,
      "assurance": "user_asserted",
      "cost_reporting": "unavailable"
    }
  ],
  "final_eligible_counts": {
    "groq": 1,
    "mistral": 1,
    "nvidia_nim": 1
  },
  "complete": true
}
```

Capture integrity:

| Capture | SHA-256 |
|---|---|
| `/tmp/t007-primary-account-activation.jsonl` | `0cb32a8511b9e992f7976aa8f4875c47679040f5a2b3814154cdcf2cf3d3441d` |
| `/tmp/t007-primary-account-activation.json` | `d0063db04c507b8d5f5e308c9dacf45c023381f70250b8cd557f2bd6e0370cec` |
| `/tmp/t007-primary-account-activation-initial.jsonl` | `8179c0a00c6145ca203c5d4ffaeac073db4e578eb01c799b8cbd928a8873cab0` |
| `/tmp/t007-primary-account-activation-initial.json` | `396451d11e4b0aa5f937ac58ff249c94142fb8408249928b1e25ef14f71d0cea` |
| `/tmp/t007-activation-config.json` | `7ee4c8ad98dde8752cd4dafd68333f2d6e255124f185d3c179942fecb1e58561` |
| `/tmp/t007-activation-restart.json` | `59dff34231579e7216cc67bf31d6d383cf3393fcf19e39c082e0b851480ced52` |
| `/tmp/t007-activation-restart-initial.json` | `3e95ee346ae7ed9d26b27998d6af2737e906b2a7023300a829245c3eedaba46d` |
| `/tmp/t007-activation-final-runtime.json` | `a30821d5202ce42eb99cb53ded9d05e7c3ad76fd026948b36b9a602a799285a1` |

[Full results and history](T-007-results.md). Source and route outcomes before activation remain in the [dated NVIDIA snapshot](T-007-nvidia-free-chat-check.md). No commit/push/external deployment, HF activation or provider-account/billing change occurred. Gemini/provenance/gateways, HF delivery and T-008/T-009 remain open.
