# T-006 Input RECON — Provider Validation Admin API

- Date: 2026-10-22.
- Roadmap: P2; work package: B-002; task: T-006.
- Baseline: branch `main`, HEAD `6d49e2a174a111dc0a5bb8745530a97d0e9786da`; `git status --short --untracked-files=all` was empty before this work.
- Authorization: owner reported T-005 review fixes confirmed and requested preparation of the next specification in this chat on 2026-10-22. This authorizes specification preparation, not implementation or remote delivery.
- Specification: [T-006](../../specs/T-006-provider-validation-api.md).

## Sources and measured observations

| Source | Observation |
|---|---|
| `VISION.md`, `ROADMAP.md`, `TASKS.md` | P2 requires a provider validation API; T-006 precedes live multi-provider activation T-007 and onboarding T-008. |
| `PROJECT-PROCESS.md`, `SPEC-EXAMPLE.md` | Lightweight file-based governance: measured recon before a substantial spec, explicit implementation approval, distinct result acceptance; no compulsory DevPlan or role cycle. |
| `docs/decisions/DEC-002-declarative-provider-schema.md` | New providers are declarative; validation covers connectivity, catalog and a micro-completion. |
| `backend/app/core/providers/models.py` | `ProviderManifest` covers bearer/header/none auth and openrouter_free/all_available/regex/manual discovery. Both URL fields currently require absolute HTTP(S) strings, despite the models_endpoint field description mentioning relative endpoints. Validation is only prefix-based; unresolved templates are allowed. |
| `backend/app/core/providers/registry.py` | Registry owns manifests and model cache. Active providers depend on enabled state and credentials. Missing Cloudflare account ID disables its unresolved template. No validation service exists. |
| `backend/app/core/providers/providers.yaml` | Bundle includes public providers and local HTTP Ollama. A blanket ban on local destinations would break the intended provider profile. Manifests are configuration, not proof of current provider compatibility or free usage. |
| `backend/app/core/discovery/openrouter.py` | Only OpenRouter has a discovery implementation. Catalog shape is an object with a `data` list. Discovery filters both prices for zero, then writes the registry; it cannot be reused unchanged for a non-mutating validation operation. |
| `backend/app/core/adapters/openai_client.py` | Completion URL appends `/chat/completions` unless already present. Client resolves credentials from environment/settings, offers no request-scoped key override, rewrites model/stream, and synthesizes usage. Some exceptions contain raw upstream bodies. Blind reuse would violate isolated validation and safe diagnostics. |
| `backend/app/api/admin/telemetry.py`, `backend/app/api/admin/__init__.py` | Admin router currently mounts telemetry only. Optional master-key protection uses an OpenAI-shaped 401 envelope; empty master key permits local development access. |
| `backend/app/main.py` | Admin router already mounted at `/api/admin`. OpenRouter discovery scheduled at startup and periodically. No main.py edit is necessary to mount another child admin router. |
| `backend/tests/conftest.py` | HTTP tests use ASGITransport; those alone do not prove real socket delivery. |

## Baseline verification

Command: `.venv/bin/pytest backend/tests -q`.

Observed: **37 passed in 0.17s**, exit 0. This is a dated baseline, not an immutable test-count requirement. No external provider or live HTTP probe was run in this recon.

## Reconciliations and gaps

- T-005 is accepted based on the owner's current message. HANDOFF's uncommitted-state entry was stale: the starting tree was clean and T-005 implementation was already in history.
- ARCHITECTURE remains a proposal. SQLite persistence, broad live provider activation, benchmark pools and dashboard are not inferred from the diagram or README.
- Current schemas do not supply a generic catalog parser or complete URL/auth consistency validation. T-006 proposes endpoint-specific checks while preserving shared manifest behavior.
- T-006 does not prove a provider is free or has remaining quota beyond the tested request. All-available catalogs are not pricing guarantees.
- No external API documentation was consulted; the proposed contract deliberately targets the existing project's OpenAI-compatible JSON shape. Provider-specific deviations are diagnostics or future T-007 scope, not guessed integrations.
- No independent implementation review or new live delivery evidence exists. Both belong to subsequent execution and acceptance.
