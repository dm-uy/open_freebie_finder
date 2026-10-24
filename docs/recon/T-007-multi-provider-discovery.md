# T-007 Input RECON — Multi-Provider Discovery and Cascade

- Date: 2026-10-22. P2 / B-002 / T-007.
- Baseline HEAD: `6d49e2a174a111dc0a5bb8745530a97d0e9786da`, branch `main`, plus the accepted, uncommitted T-006 candidate. Its seven runtime/test/tool hashes and passing suite are recorded in [T-006 results](../../notes/T-006-validation-results.md).
- Starting working tree: the fourteen task/preparation paths listed in T-006 HANDOFF, not a clean checkout. No runtime changes made during this recon. Acceptance metadata was synchronized first.
- Authorization: owner accepted T-006, authorized documentation synchronization and next-spec preparation; subsequently excluded Cerebras from T-007 and explicitly required model discovery for other providers, identifying OpenRouter-only discovery as a hidden functional gap. T-007 implementation is not approved.
- Output: [T-007 draft](../../specs/T-007-multi-provider-discovery-and-cascade.md).

## Local observations

| Source | Observed behavior |
|---|---|
| `backend/app/main.py` | Lifespan constructs only OpenRouterDiscoveryService. Both initial and periodic polling call that single provider. Other configured manifests do not cause background model discovery. |
| `core/providers/providers.yaml`, `models.py` | Ten bundled manifests describe endpoints and four discovery rule types. Existence/enabled state is not proof that a provider works, supports chat or is free today. No response-envelope discriminator, exact canonical alias map or explicit account-free confirmation exists. |
| `core/providers/registry.py` | Active means enabled plus credentials (or auth none). register_models replaces only named providers; get_models returns an in-memory snapshot. get_model_candidates treats no active IDs as permissive; do not copy this condition into the new eligibility path. |
| `core/discovery/openrouter.py` | Only implemented discovery is OpenRouter: object/data list, exact zero prompt/completion prices, strip trailing :free, mutate registry. Transport/parse failure retains prior cache; valid successful empty result clears that provider. |
| `core/balancer/router.py` | Candidate resolution filters active providers/cooldown but not is_free. Ordering is alphabetical and maximum attempts is three. A provider with many candidates can consume the attempt budget before any other provider is tried. |
| Same source | Raw requested IDs are compared directly against each candidate instead of first resolving the raw ID to canonical identity. This can demote the same model at a second provider into Tier 2. |
| Same source / `core/adapters/openai_client.py` / `api/v1/chat.py` | Structured hop errors are sanitized, but adapter exceptions may include raw upstream bodies; ordinary warning logs and final 503 error text can propagate them. This remains outside isolated T-006 and is relevant to the next runtime routing scope. |
| `api/v1/models.py` | Lists every cached canonical model without active/free/freshness checks. `/v1/models` makes no outbound calls; preserve that boundary. |
| `backend/tests/test_cascade_failover.py` | A test named same-model failover actually supplies two candidates from local_ollama, so its passing result is not proof of distinct live providers. Existing tests cover fixed cooldown, pre-buffering, Tier 2 and the three-attempt ceiling. |
| `TASKS.md`, `ROADMAP.md` | Original T-007 paths omit discovery/startup/schema/config despite needing them. P2 also promises an adaptive exponential breaker, but current tasks do not own it. Scope must be explicit before implementation. |

## Credential prerequisites (presence only)

Read Settings/registered environment names without printing values. OpenRouter credential present; Groq, Google Gemini, NVIDIA, Cerebras, GitHub, Mistral, Hugging Face and Cloudflare credentials absent. Cloudflare also has no resolved account configuration and is disabled. Local Ollama requires no credential; no running local model server was probed.

No authenticated provider requests, completion calls or application live probes were run. A direct public unauthenticated read of the hosted NVIDIA catalog through web access did return an OpenAI-shaped object/data list; it is catalog evidence, not inference activation evidence. No new suite was run for this read-only documentation task: the accepted baseline is the saved final T-006 run (131 passed in 1.63s), not a newly measured T-007 result.

## Current primary-source checks

All checks below were made on 2026-10-22. API documentation proves published contracts, not account entitlements or current live success.

| Provider | Primary source and implication |
|---|---|
| Groq | [Models](https://console.groq.com/docs/models), [OpenAI compatibility](https://console.groq.com/docs/openai), [rate limits](https://console.groq.com/docs/rate-limits), [billing](https://console.groq.com/docs/billing-faqs): existing base/catalog endpoints are documented; catalog includes non-chat workloads. Free and paid account plans differ. Listing does not certify free chat eligibility. |
| Gemini | [OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai?hl=en) documents the configured OpenAI base, models listing and chat endpoint. [Pricing](https://ai.google.dev/gemini-api/docs/pricing) distinguishes free/paid access by model and feature. Do not include every catalog ID in auto:free. |
| NVIDIA | [Hosted LLM APIs](https://docs.api.nvidia.com/nim/reference/llm-apis) documents hosted chat completions. A subsequent direct read of the [hosted catalog](https://integrate.api.nvidia.com/v1/models) returned object=list with a data list of id/object/created/owned_by entries. This closes the catalog-envelope gap; it does not prove credentialed completion access, chat capability or free entitlement. Self-hosted NIM documentation was not used as hosted proof. |
| Cerebras | [Current rate-limit FAQ](https://inference-docs.cerebras.ai/support/rate-limits) describes a time/credit-limited trial and explicitly denies a permanent free tier. Older pricing material conflicts with this current FAQ. Owner chose exclusion from T-007; return separately. |
| GitHub Models | [GitHub Docs](https://docs.github.com/en/github-models) reports complete retirement, including catalog and inference. Mark retired and skip; do not migrate silently to Copilot or paid Azure services. |
| Hugging Face | [Hub API](https://huggingface.co/docs/inference-providers/main/hub-api) documents router.huggingface.co/v1/models with a data envelope and provider status/pricing metadata. The old api-inference base in the bundle differs from the documented router. Discoverability does not establish zero-cost routing. |
| Cloudflare | [Model Search](https://developers.cloudflare.com/api/resources/ai/subresources/models/methods/list/) documents /accounts/{account_id}/ai/models/search, native success/result envelope, and optional marketplace format. [Chat compatibility](https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/) documents the existing chat base. A data-only parser cannot parse the native catalog. The official [SDK model resource](https://raw.githubusercontent.com/cloudflare/cloudflare-typescript/main/src/resources/ai/models/models.ts) uses page pagination but declares item type unknown. Its [pagination implementation](https://raw.githubusercontent.com/cloudflare/cloudflare-typescript/main/src/core/pagination.ts) increments page until an empty result. Native item identification still needs confirmed evidence before profile delivery. |
| Mistral | [Models API](https://docs.mistral.ai/api/endpoint/models) and [workspace verification](https://docs.mistral.ai/getting-started/quickstarts/admin/manage-workspaces) document model listing. Chat capability differs from other model functions; model existence does not establish free-tier entitlement. |
| Local Ollama/vLLM | Existing manifest targets the OpenAI-compatible local models API. No local runtime or model availability checked here; missing runtime must produce an isolated failure, not stall every provider. |

## Independent assessment and proposal boundaries

A read-only reviewer independently checked the local producer/consumer gaps and current primary sources for GitHub retirement, Cerebras trial, HF router and Cloudflare envelope. Recommended a shared scheduler with provider-specific declarative catalog profiles, safe admission and explicit skipped/error states. Owner's requirement rules out closing T-007 after adding only Groq.

Important design alternatives, trade-offs and proposed choices are retained in the draft. The owner has settled Cerebras exclusion; profile/admission/mapping/scheduling details remain proposals until spec approval. NVIDIA hosted catalog envelope was subsequently observed directly. Cloudflare item identification remains an evidence gap; its pagination mechanism is verified from the official SDK. Missing credentials limit live acceptance, not preparation.

## Subsequent owner decisions — 2026-10-22

These decisions refine scope after the measured recon; they do not change the original observations or claim new runtime evidence.

- Cloudflare: defer its profile as unsupported_profile, zero T-007 requests. Native item mapping/parser/pagination moves to a separate future approved scope.
- Live generation: owner stated Groq/NVIDIA keys can be supplied; keep their live checks mandatory. No key values captured and no subsequent presence/entitlement check run. Owner explicitly deferred Gemini external live generation until a key is available while retaining its implementation/local tests and keeping P2 open.
- Owner accepted all six design choices and expanded edit boundaries. Specific Cloudflare deferral takes precedence over the earlier general envelope proposal.
- Final concrete specification v1.1.0 is approval-ready; implementation execution approval remains pending. No implementation or new test/live run occurred during this record update.
