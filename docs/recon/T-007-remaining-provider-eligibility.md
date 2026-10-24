# T-007 Remaining Direct Providers: Strict Free Eligibility Reconnaissance

- Date: 2026-10-23 (owner timezone America/Montevideo; captures use UTC).
- Phase/task: P2 / B-002 / [T-007](../../TASKS.md), serving [VISION](../../VISION.md)'s key-only dynamic zero-cost inference.
- Scope: Groq, NVIDIA hosted, Mistral and Hugging Face source/account/free-only feasibility with already supplied keys. Read-only research, not implementation, activation or new inference.
- Authority: owner requested investigation of what blocks these providers while retaining dynamic eligibility and no manual model lists. Existing strict NVIDIA selection and accepted output/cost/free gates remain settled. No reduced-guarantee alternative is adopted.
- Baseline: main at 6d49e2a174a111dc0a5bb8745530a97d0e9786da plus the accepted dirty-tree candidate. Start inventory: /tmp/t007-other-providers-start-status.txt. The accepted primary local backend on 127.0.0.1:8001 is preserved.
- Prior context: [original dynamic recon](T-007-dynamic-free-eligibility.md), [approved correction](../../specs/T-007-dynamic-free-eligibility.md), [accepted amendment/results](../../notes/T-007-results.md).

## 1. Executive finding

All four supplied keys were present in memory and their configured catalogs returned HTTP 200. HF whoami-v2 separately returned 200. These are current access observations, not account-tariff or zero-charge certification. No generation is necessary to establish this source gap; a successful completion cannot answer whether later usage is billed.

The runtime has an intentional implementation boundary: backend/app/core/eligibility/evidence.py, source_verdict, has a positive source contract only for the exactly bound OpenRouter profile. Groq/Mistral/HF currently return unknown / account_evidence_unavailable, NVIDIA unknown / enforcement_unverified. Manifests already enable catalog discovery. Enabling them again or adding an allowlist does not implement a new free-evidence profile.

There are two distinct missing parts: authoritative effective-price/free-only evidence for the actual credential/request scope, and a reviewed provider-specific source/dispatch implementation consuming that evidence. The existing evidence TTL/epochs, fail-closed revocation, request validator, shared guards and cascade can be reused; they do not manufacture missing provider evidence.

## 2. Fresh authenticated read-only observations

Command:

```text
PYTHONPATH=/Users/a1111/Dev/open_freebie_finder .venv/bin/python /tmp/t007_remaining_provider_catalogs.py
```

Exactly five GET requests: the four configured official model catalogs and documented HF whoami-v2. No POST, inference, billing mutation, guessed admin endpoint, browser session, signup or provider message. Keys loaded privately from existing settings; no key, account identity, raw model ID or body persisted. Each response is bounded to 4 MiB decoded, 20s overall / 15s transport; trust_env=false, redirects disabled. The fixed field/header checks below are scoped observations, not an exhaustive assertion that a provider has no billing data anywhere.

Exact capture /tmp/t007-remaining-provider-catalogs-20261023.jsonl:

```jsonl
{"provider": "groq", "key_present": true, "observed_at": "2026-10-23T10:34:01.971009+00:00", "inference_requests": 0, "catalog_http_status": 200, "catalog_model_count": 11, "root_evidence_fields": [], "model_field_presence": {"plan": 0, "tier": 0, "account_tier": 0, "billing": 0, "credits": 0, "entitlements": 0, "free_only": 0, "is_free": 0, "pricing": 8, "capabilities": 0}, "named_billing_header_present": false, "catalog_positive_rate_model_count": 8, "catalog_all_observed_numeric_rates_zero_count": 0}
{"provider": "nvidia_nim", "key_present": true, "observed_at": "2026-10-23T10:34:01.991523+00:00", "inference_requests": 0, "catalog_http_status": 200, "catalog_model_count": 84, "root_evidence_fields": [], "model_field_presence": {"plan": 0, "tier": 0, "account_tier": 0, "billing": 0, "credits": 0, "entitlements": 0, "free_only": 0, "is_free": 0, "pricing": 0, "capabilities": 0}, "named_billing_header_present": false}
{"provider": "mistral", "key_present": true, "observed_at": "2026-10-23T10:34:01.992012+00:00", "inference_requests": 0, "catalog_http_status": 200, "catalog_model_count": 53, "root_evidence_fields": [], "model_field_presence": {"plan": 0, "tier": 0, "account_tier": 0, "billing": 0, "credits": 0, "entitlements": 0, "free_only": 0, "is_free": 0, "pricing": 0, "capabilities": 53}, "named_billing_header_present": false, "chat_capable_count": 27}
{"provider": "huggingface", "key_present": true, "observed_at": "2026-10-23T10:34:01.992209+00:00", "inference_requests": 0, "catalog_http_status": 200, "catalog_model_count": 133, "root_evidence_fields": [], "model_field_presence": {"plan": 0, "tier": 0, "account_tier": 0, "billing": 0, "credits": 0, "entitlements": 0, "free_only": 0, "is_free": 0, "pricing": 0, "capabilities": 0}, "named_billing_header_present": false, "provider_route_count": 271, "provider_pricing_count": 176, "explicit_free_route_count": 0, "live_free_route_count": 0, "zero_token_price_route_count": 0, "token_authentication_http_status": 200}
```

| Provider | Catalog/access observation | Evidence it does not establish |
|---|---|---|
| Groq | 11 models; 8 pricing objects with positive observed catalog rates | Effective price under this key's current account plan; public/list rates are not an invoice and do not prove these Free-account requests paid |
| NVIDIA | 84 model IDs; no pricing objects in the measured catalog | Per-route text capability, account entitlement, current effective price or hard free-only enforcement |
| Mistral | 53 models; 27 advertise completion_chat; no pricing objects | Current Organization plan/PAYG/allowance and an enforceable zero-cost dispatch scope |
| HF | 133 models, 271 provider rows, 176 pricing rows, 0 explicit free rows and 0 zero-input/output-price rows; whoami 200 | A current qualifying free promotion or an account-level spend guard; absence in this snapshot is not a claim that HF never has free routes |

## 3. Provider contracts and specific blockers

### Groq: account-free access, not zero public list prices

The [Billing FAQ](https://console.groq.com/docs/billing-faqs) distinguishes Free from paid Developer access and requires a payment method to upgrade. Current [rate-limit documentation](https://console.groq.com/docs/rate-limits) distinguishes Free/Developer limits and documents 429 on quota exhaustion; it does not identify the supplied key's current account plan. A cached community Free Plan FAQ appeared in search but its direct URL now redirects to groq.com and is not adopted as current proof. A positive catalog rate alone still does not establish a Free account's effective invoice amount.

[Service tiers](https://console.groq.com/docs/service-tiers) are performance/throughput/reliability choices, not free-plan selectors. [Spend limits](https://console.groq.com/docs/spend-limits) are a paid-account facility with delayed accounting and possible overshoot; they are not a request-level zero-price ceiling. The [reviewed inference API](https://console.groq.com/docs/api-reference) did not establish a supported ordinary-key plan/effective-price introspection or hard free-only parameter. This is a bounded search finding, not a proof that no such interface exists.

Needed before strict activation: a supported current credential-bound Free-plan/zero-spend source and its fail-closed loss/change semantics, plus dynamic chat-capability/model discovery. Do not treat quota headers, successful generations, performance tiers or the owner's historical no-card statement as an automatically refreshed account certificate. Positive catalog prices alone must not classify the owner's effective Free-account cost as paid.

### NVIDIA: public free offers do not settle the chosen strict account guarantee

[Run NIM Anywhere](https://docs.api.nvidia.com/nim/docs/run-anywhere) documents Developer Program access for prototyping. [API Quickstart](https://docs.api.nvidia.com/nim/docs/api-quickstart) establishes hosted access and developer-key use. Prior recon found dynamically observable Free Endpoint metadata and exact routes on official model pages; a parser could discover offers without model-ID lists, but that observed page format is not a documented account-pricing API.

Do not hardcode historical credit counts: the [FAQ](https://docs.api.nvidia.com/nim/docs/faq) and a [2025 official-forum discussion](https://forums.developer.nvidia.com/t/cannot-find-the-amount-of-credits-left-on-nim-api/337051) disagree about credit versus variable rate-limit operation. Neither proves the current supplied key's strict free-only scope. [Trial Terms](https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf), section 1.4, distinguish trial/continued-production subscription; they do not prove an immutable free-only hostname or different key/host for every paid case. The general [Technology Access Terms](https://developer.nvidia.com/legal/terms), section 7, discuss promotion expiry/charges subject to the relevant product agreement. This recon does not make a legal conclusion about which agreement controls this account.

A documented intrinsically free-only hosted service could in principle satisfy strict handling without a balance API. That contract was not established for the bound integrate endpoint, and the opposite claim of a proven paid mode on that same host was not established either. Needed: documented current entitlement/free-only enforcement for this exact hosted credential/route scope, including exhaustion/change handling. The owner's prior strict choice remains in force; free-offer-only activation is not silently substituted.

### Mistral: Organization billing state follows the key

[API keys](https://docs.mistral.ai/admin/identity-access/api-keys) explicitly inherit Organization plan/PAYG settings rather than being permanently Free/PAYG-scoped keys. [Subscriptions](https://docs.mistral.ai/admin/billing-usage/subscriptions) and [Billing](https://docs.mistral.ai/admin/billing-usage/billing) distinguish included usage from enabled PAYG backed by prepaid credits. A balance/allowance is not automatically a statement that model tariff is zero or that paid overflow is forbidden. The Billing page also warns that delayed processing may take prepaid balance below zero and put the overage on an invoice; prepaid balance is not an atomic zero-spend ceiling.

The [Admin API](https://docs.mistral.ai/admin/admin-api/overview) is Enterprise-only and ordinary inference keys do not authenticate its endpoints. No admin call was attempted with the supplied inference key; requesting an Admin key would not itself prove an adequate plan/PAYG evidence endpoint exists. Catalog completion_chat/function capabilities support dynamic model filtering; the current source gap is Organization-level billing/free-only proof.

Needed: a supported read-only account-state contract binding the inference key to current included free access and disabled/blocked paid overflow, plus an explicit per-request applicability contract. It must detect plan/PAYG changes and quota exhaustion automatically. No manual model list is needed, but the ordinary key/catalog alone did not establish this state.

### Hugging Face: useful per-route promotion metadata, no current free offer

Both current [en pricing](https://huggingface.co/docs/inference-providers/en/pricing) and [main pricing](https://huggingface.co/docs/inference-providers/main/pricing) now list no included monthly credits for Free users. This resolves the earlier en/main version discrepancy in the prior recon; stale $0.10 claims are not a current guarantee. Purchased/subscription credits are a different product condition. BYOK can cause direct provider billing and cannot certify zero operator spend.

The [Hub API](https://huggingface.co/docs/inference-providers/main/hub-api) documents providers[].is_free as current free promotion for that exact provider, with per-provider status/pricing/capabilities. The measured snapshot contains no explicit free row. Even a future matching row requires exact [provider selection](https://huggingface.co/docs/inference-providers/index) (documented model:provider binding), fresh proof of the covered text-chat profile and prevention of paid fallback/promo-end billing. Automatic fastest/cheapest/preferred selection does not preserve proof for a specific provider. A request-level zero-price/free-only enforcement contract was not established in the reviewed sources.

Needed: implement the exact per-provider promotional source profile only after settling its strict dispatch guarantee. An is_free flag alone has a tariff-change race, and an absent flag must remain unknown. Dynamic monitoring can find later promotions without manual IDs; it cannot create a free route in the present snapshot or treat paid subscription credits as a free model.

## 4. Proposed next packet; not implementation approval

1. Record one evidence contract per direct provider: source/auth, credential/account/route binding, effective included-price scope, text-only output and allowed parameters, refresh/expiry/failure semantics, quota behavior and the mechanism preventing paid overflow. No account-session scraping or undocumented endpoint guesses.
2. Reuse existing EligibilityStore and shared guard/cascade. Add a positive profile only when its provider contract is sufficient; account evidence and model catalog remain separate. New/changed/removed offers are refreshed automatically, not curated in YAML. A separate read-only account-data credential/source would expand the original key-only input contract and requires an explicit design decision, not an invented supported API.
3. For HF, the documented promotional catalog is the most direct dynamic offer source, but current 0 offers and unresolved hard free-only dispatch remain blockers. For Groq/Mistral, prioritize account-state/free-only evidence rather than model-ID discovery. For NVIDIA, retain the selected strict gate until an adequate service/account contract is established.
4. Only after sufficient free evidence exists, perform bounded 32-token buffered/SSE verification through the actual proxy. Do not use a generation or missing monetary field to decide price; existing guard policy cannot undo the first unexpected charge.

Current recommendation: no direct-provider activation on the supplied-key evidence alone. This is a precise source/product-contract gap plus intentional unimplemented source profiles, not a need for model allowlists. The search does not prove those providers cannot ever support the requirement. No new specification version, implementation, account change, service restart or generation is authorized or claimed by this report.

## 5. Runtime preservation and verification

Primary backend listener remains PID 37372 at 127.0.0.1:8001; capture /tmp/t007-remaining-provider-primary-listener.txt. No application/manifest/.env/account/billing changes, no commit/push/deployment, no generation. The prior 334-test result remains historical for unchanged accepted code; no tests rerun for this read-only recon.

Current code hashes retained for the evidence-boundary check:

| Path | SHA-256 |
|---|---|
| `backend/app/core/eligibility/evidence.py` | `9b67ffa2d825cc9d5a9c2939ad1148dee49c8031a7825e03cf603540706d20f8` |
| `backend/app/core/eligibility/request.py` | `2588a80c9729437903a50bf08bf233b85d324409a13b070a4dabb3575d13fa21` |
| `backend/app/core/providers/registry.py` | `bfd2632b119236c1f89484b7c476058126a7b7f1ea07a992d03ecb0439fc33ef` |
| `scripts/probe_multi_provider.py` | `017dcec5433e51a325eaf32adf393959cced519f05994d7a0b3e6ac3d0ed0941` |
| `backend/tests/test_dynamic_eligibility.py` | `23792f02efa7b40755d0f8951323b28ed58ebb56f6d792acbde7d3a5ec4723d0` |
| `backend/tests/test_free_request_profile.py` | `7598da9beb35a274e1ddda10efc6273f2ae6c402f1bf260c837baf2d98957b08` |

Independent read-only source/capture/record verification is clear after removing a redirected Groq community FAQ as current proof and qualifying Mistral prepaid processing delay. The exact five-GET capture, six accepted candidate hashes, seven protected T-006 hashes, 19 unaffected baseline hashes, 17 local record links/markers, status inventory and git diff --check were verified. Listener evidence confirms the preserved primary PID 37372 on 127.0.0.1:8001. Reviewer writes/tests/authenticated or inference calls/.env reads: none; no writes outside allowed paths (none). No new software test or whole-candidate implementation QA is claimed.


## Follow-up evidence after approved hybrid implementation (2026-10-23)

The owner's hybrid decision supersedes strict-only activation recommendations above for explicitly asserted account mode; original source gaps remain factual. [Follow-up results](../../notes/T-007-results.md) establish current post-fix Mistral conditional buffered/SSE delivery. NVIDIA now returns a measured function_not_found_for_account error for some cataloged/currently documented chat selectors; other bounded requests time out. The official [LLM reference](https://docs.api.nvidia.com/nim/reference/llm-apis) confirms the owned origin/path but not account entitlement. Bounded table/catalog intersection is a diagnostic aid, not evidence that unmatched models are retired or matched models are accessible/free. Public forum user reports suggest entitlement/deployment issues but do not certify this account's root cause. No account setting/billing mutation or model-ID list was introduced. Exact counts/captures/code hashes and honest provider delivery gates belong in the results record.

## NVIDIA Free Endpoint repair recon and measured delivery (2026-10-23)

The owner subsequently authorized fresh free chat discovery, short32-token key-bound probes and discovery repair. This supersedes the earlier generic-catalog-only selection, not the account-assurance premise or other providers' proof gaps. Current public NGC ENDPOINT search for nim_type_preview returns43 resources;17 carry playgroundtype_chat,11 are public/AVAILABLE/PREVIEW and nondeprecated,10 have an exact publisher/name match in the keyed84-ID API catalog. No slug alias is guessed for the remaining available resource. Free Endpoint is a model/endpoint label, not a count of independent providers or proof of account pricing. Sources: [Build Models](https://build.nvidia.com/models) and `https://api.ngc.nvidia.com/v2/search/catalog/resources/ENDPOINT` with the documented-in-results observed query. This public interface may change and must fail closed on incomplete/malformed responses.

The implemented selection is a bounded JSON-source intersection, not a model-ID list or HTML/free-text price parser. NGC requests carry no inference key/default auth/cookies. Both catalogs share15s and each retains the4MiB bound; no source fallback. Existing private account qualification and guards still apply. Actual isolated buffered/SSE qualification and ordinary real proxy delivery now confirm working DiffusionGemma and Llama3.2 11B Vision routes; their exact identities/capture hashes and remaining packet outcomes belong in the [dated snapshot](../../notes/T-007-nvidia-free-chat-check.md) and [results](../../notes/T-007-results.md). Therefore the prior five failures do not establish a provider-wide key/entitlement problem. They still do not reveal the underlying NVIDIA deployment/account reason for each old404. Cost reporting remains unavailable and account trust user_asserted. No primary activation or account mutation is included.
