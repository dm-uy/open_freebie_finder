# T-007 Follow-up RECON — Dynamic Free Eligibility

Date: 2026-10-22. Phase P2 / B-002. Status: extended feasibility recon and corrective specification draft; implementation approval pending.

## Owner requirement and authorization

The owner clarified in chat that users provide a provider key, the service automatically determines which models are free for that key, uses only those models and tracks later pricing changes. Hardcoded model IDs and recurring manual YAML list maintenance are not the intended workflow. This restores the original [VISION](../../VISION.md) success criterion; it does not accept the completed T-007 candidate or erase its test evidence. Preparation of this correction follows that instruction. A concrete replacement admission contract still needs specification and approval under PROJECT-PROCESS.md.

## Measured local gap

- `backend/app/core/discovery/orchestrator.py`, `_parse`: only the openrouter_free rule checks catalog prompt/completion prices. Other rules construct DiscoveredModel with is_free=True and rely on registry policy for admission. A successful HTTP response or a declared free account does not independently refresh tariff evidence.
- `backend/app/core/providers/registry.py`, `admits`: cloud admission requires free_access_confirmed and membership in chat_model_allowlist, except specific built-in OpenRouter/local exemptions. Rechecks enforce revocation of these local settings and catalog freshness, not discovery of external tariff changes.
- `backend/app/core/providers/models.py`: the manifest has static confirmation/list fields; there is no structured account-scoped pricing evidence, checked-at time, validity interval or unknown/paid eligibility reason.
- `backend/app/core/providers/providers.yaml`: the owner separately authorized enabling Groq/NVIDIA for the previously live-tested model. Those saved entries remain the actual current configuration, not the proposed dynamic solution. They were not removed or expanded in this recon.
- [T-007 results](../../notes/T-007-results.md) proves catalog discovery, routing and live reachability. It does not prove autonomous cloud tariff determination. Preserve the historical hashes and the subsequent authorized YAML-change hash.

Consequently, new free models outside the list remain excluded and an allowlisted model whose tariff changes is not automatically reclassified by the current Groq/NVIDIA parser. This is a product-contract gap requiring correction, rather than a new optional convenience feature. Shared discovery, exact identity, safe routing and cleanup remain useful delivered infrastructure.

## Current public evidence and limits

Initial public-source pass on 2026-10-22 used no authenticated requests. The subsequent owner-authorized continuation below adds limited real catalog metadata observations using local credentials in memory, with no secret output, completion calls or account changes. Previous T-007 generation evidence remains historical.

| Provider / source | Verified information | Unresolved evidence requirement |
|---|---|---|
| OpenRouter [models API](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties) | The catalog exposes pricing metadata; the existing parser already uses token-price checks. | A replacement contract must account for billable request features as well as token prices, freshness and any provider-side zero-cost enforcement. Do not infer complete request cost from two fields alone. |
| Groq [API reference](https://console.groq.com/docs/api-reference), [billing](https://console.groq.com/docs/billing-faqs) | Model listing is authenticated; Free and paid Developer access are distinct, and an upgrade changes billing behavior. | These sources do not establish a documented inference-key endpoint returning current account tier plus per-model zero-charge entitlement. This is a search result limitation, not proof that no such endpoint exists. |
| Groq [rate limits](https://console.groq.com/docs/rate-limits) | Free/Developer tables and request/token limit headers exist; exact organization limits are available in the console. | A matching rate-limit value is not authoritative account-plan or price proof. A global free-plan table alone cannot certify the supplied key is on that plan. |
| NVIDIA [hosted LLM reference](https://docs.api.nvidia.com/nim/reference/llm-apis), [API catalog quickstart](https://docs.api.nvidia.com/nim/docs/api-quickstart) | Hosted endpoints and developer-key setup are documented. The earlier measured hosted catalog established model identity/envelope shape. | Neither reviewed guide establishes a key-scoped pricing/credit/automatic-paid-overflow contract suitable for dynamic admission. Hosted access must not be inferred from self-hosted NIM licensing. |

No uniform provider API is assumed. More research is required to identify supported authoritative pricing/account sources for Groq/NVIDIA and other viable profiles before promising key-only activation for them. Do not invent a billing endpoint or use undocumented console sessions as if they were part of the inference-key contract. Existing Cloudflare/Cerebras/GitHub exclusions and Gemini live deferral remain in force.

## Proposed behavior for the corrective specification

These are design requirements/proposals, not claims about delivered runtime:

1. Keep provider connection and discovery rules in YAML. Do not store the automatically discovered free-model set as a hand-maintained YAML allowlist. Any optional operator restriction can only narrow the computed eligible set, never certify price.
2. Separate catalog visibility, chat capability, account access, price and transient availability. Derive model/request eligibility from current authoritative provider evidence and relevant account/key scope. No generic assignment of is_free=True based on catalog presence.
3. Represent free, paid and unknown explicitly. Attach source/provenance, check time, expiration, account/credential binding without storing the secret, applicable request features and a safe reason. Free allowance/credits must not silently fall through to paid inference.
4. Refresh evidence in the background with bounded requests/resources. Re-evaluate the entire candidate set on successful refresh: newly verified free models join automatically; positive price, revoked entitlement and removed models leave automatically. Source failure never renews old evidence; unknown/expired evidence excludes models from new dispatches. Key replacement invalidates account-bound evidence immediately.
5. Listing and routing consume only in-memory eligible evidence. Recheck before each actual dispatch, including later failover attempts. Maintain existing correlation, stream ownership, secret hygiene, provider diversity and memory-only listing contracts.
6. Use completion probes only for protocol reachability after free eligibility is established; HTTP 200, trial credits, a successful generation or token-limit headers alone do not prove zero price. Do not spend money to discover whether a model is paid.
7. Define a measured refresh/expiry window. Periodic polling cannot observe an unannounced provider change instantaneously; a strict no-charge guarantee needs provider-enforced free-only routing/account constraints or a binding price ceiling. Neither a cached catalog nor even a preflight request makes a later inference atomically free. The specification must state each profile's attainable guarantee.
8. If a provider cannot supply adequate evidence with the supplied key, report a clear unsupported/unknown eligibility reason and exclude it. Preserve the key-only product goal; do not disguise manual operator attestation or a static model list as its fulfillment. Any weaker opt-in mode would be a separate explicit product decision.

## Options to assess

| Option | Benefit | Limitation / disposition |
|---|---|---|
| Keep manual confirmation plus per-model list | Existing bounded admission, previously approved implementation | Does not meet the clarified dynamic requirement; retain only as current-state description during correction. |
| Automatically admit all listed models or all successful probes | Minimal operator work | Does not prove zero cost or account plan; reject. |
| Provider-specific current evidence with expiration and fail-closed admission | Supports dynamic discovery/revocation and auditable reasons without hardcoded model IDs | Recommended direction; key-scoped sources/guarantees must be verified per provider, especially Groq/NVIDIA. |
| Enforce free-only/zero-spend at provider and refresh catalog evidence | Stronger protection against tariff races | Use where supported; cannot assume such enforcement exists for every account/API. |

## Required verification before claiming delivery

Use fixture state transitions and controlled real sockets to cover free-to-paid, paid-to-free, new/removed models, expired/unavailable/malformed sources, key/account changes and changes during failover. Assert no paid or unknown candidate is dispatched; ordinary /v1/models remains memory-only. Negative chat-capability metadata wins. Verify every request feature admitted to auto:free is covered by the price contract. Preserve existing T-006/T-007 scenarios. Required live evidence must demonstrate the actual source of eligibility, not just another successful completion; missing prerequisite/source remains UNVERIFIED or an explicit blocker.

## Next step and current verification

Prepare a concrete T-007 corrective specification/addendum after resolving per-provider evidence feasibility. Do not silently rewrite the approved v1.1.0 contract or mark its result accepted. The owner has set the dynamic requirement; no need to ask whether hardcoded model lists should remain the primary workflow.

Current follow-up changes only project requirements/state/recon records. Runtime, YAML policy, real .env and historical evidence remain unchanged. No tests rerun for documentation-only work. Independent read-only assessment confirmed the static-admission gap, the provider-source limits and the proposed evidence-based direction. It recommended binding evidence to endpoint/credential/model/request capabilities, separating catalog and tariff freshness, and considering every billable request component. Final independent document verification found no substantive discrepancies; one stale HANDOFF readiness phrase was corrected. Local record links resolve, git diff --check passes, and delivered runtime plus the last owner-authorized manifest hashes remain unchanged. The reviewer wrote no files, ran no tests/authenticated calls and did not read .env or secrets.

## Extended feasibility investigation — owner-authorized continuation

The owner explicitly instructed continued Groq/NVIDIA reconnaissance and preparation of a corrective T-007 specification without manual model lists. The resulting draft is [T-007 v1.2.0 correction](../../specs/T-007-dynamic-free-eligibility.md). It preserves the approved v1.1.0 contract/history and makes its proposed admission replacements explicit. No replacement implementation is authorized yet.

### Groq: pricing now exists, but effective account cost remains unresolved

The current authenticated GET /openai/v1/models response has pricing objects for some models. This corrects the overly broad inference that Groq exposes no prices: published reference/SDK types do not exhaust current live metadata. Prices in the observed objects are positive despite the owner's prior confirmation of free-account access, and correspond to public list-price magnitudes. Their presence alone therefore cannot certify the effective account charge, nor justify marking the free-account models paid.

Checked primary sources:

- [Official SDK model schema](https://raw.githubusercontent.com/groq/groq-python/main/src/groq/types/model.py) and [API surface](https://raw.githubusercontent.com/groq/groq-python/main/api.md): model identity and supported client resources; neither reviewed surface establishes key-scoped billing/plan introspection. This is a bounded absence finding, not proof no interface exists elsewhere. SDK main is mutable and is not a promised frozen schema.
- [Service tiers](https://console.groq.com/docs/service-tiers) and [completion parameter schema](https://raw.githubusercontent.com/groq/groq-python/main/src/groq/types/chat/completion_create_params.py): service tiers select performance/processing behavior, not a documented free-only mode. The reviewed contract does not establish a zero-price request ceiling.
- [Billing FAQ](https://console.groq.com/docs/billing-faqs): an account upgrade changes billing immediately. A previous owner free-plan declaration is not automatic change detection.
- [Spend limits](https://console.groq.com/docs/spend-limits) and [model permissions](https://console.groq.com/docs/model-permissions): console-managed budget and model restrictions exist; neither reviewed page establishes a zero-spend enforcement API controlled solely by an inference key. Do not confuse model permission with price permission.
- [Models](https://console.groq.com/docs/models) and [rate limits](https://console.groq.com/docs/rate-limits): model availability and free/paid quota information. Public tables can inform offer discovery, but quota matching is not account-tier attestation.

Search covered the official reference, SDK resource index/model/request types, billing/spend/permissions/service-tier documentation and targeted searches for billing APIs, organization tier and free-only/max-price controls. Some third-party search hits describe console-internal endpoints; those were not adopted as provider contracts or called with keys/cookies. Public docs llms.txt could not be retrieved through the web tool. No guessed billing endpoint was probed. No contact message was sent to the provider.

### NVIDIA: a dynamic official-offer source is feasible

The official [model page](https://build.nvidia.com/openai/gpt-oss-20b) advertises a free hosted endpoint and identifies its exact server and text/chat profile. Independent read-only inspection of the public HTML also found structured React Flight data: a nim_type_preview endpoint tag, its Free Endpoint display mapping, AVAILABLE/PREVIEW attributes, modelPath and embedded OpenAPI server/chat path. This is an observed page format, not a documented stable API. It must not be evaluated as JavaScript or treated as an account-billing API.

The constructive algorithm is dynamically catalogued IDs intersected with matching fresh official model-page free-offer/capability/route metadata. Model identifiers come from the catalog, not a hardcoded list. Partner deployments and self-hosted offerings are distinct; a model name match cannot redirect credentials or inference there. Invalid page format, conflicting fields, removed offer or unmatched route becomes unknown, never an optimistic free default.

Additional primary evidence:

- [General FAQ](https://docs.api.nvidia.com/nim/docs/product): free developer endpoints for prototyping.
- [Trial terms](https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf), section 1.4: trial scope/credits may be limited; later/production use has separate subscription conditions. This does not establish account balance introspection or universal no-paid-overflow semantics for every possible key.
- [NGC User Guide](https://docs.nvidia.com/ngc/latest/ngc-user-guide.html): public API endpoint access is a permission, not a guarantee that an arbitrary inference key carries every entitlement. Artifact/download rights are not hosted inference pricing.

No documented inference-key method for effective account price, credit balance, automatic account-change signal or provider-enforced zero ceiling was established in these sources. Older credit announcements cannot be hardcoded into current rules. Official free-offer metadata is useful evidence; it is weaker than key-scoped, provider-enforced free-only access. Selecting that bounded guarantee requires an explicit owner decision in the corrective specification, not per-model approval.

### Real catalog metadata observations

Commands: PYTHONPATH=. .venv/bin/python /tmp/t007-inspect-eligibility.py and PYTHONPATH=. .venv/bin/python /tmp/t007-inspect-groq-pricing.py, exit 0. Both were read-only catalog inspections outside the network sandbox, using trust_env=False, redirects disabled, bounded time and no inference requests. Only sanitized structural/numeric metadata was retained; no raw model IDs, generated content, credential values, account IDs or error bodies. The field-presence probe checks a named set of possible pricing/plan fields, not every possible schema or undocumented endpoint. The second check reports pricing structure/numeric values, not an invoice or actual charge.

The one-off scripts are temporary recon tools, not shipped runtime/probe contracts. Reproduce during implementation through the scoped script changes in the draft; do not assume /tmp survives a new environment.

Catalog field observation (actual stdout):

```jsonl
{"provider": "groq", "http_status": 200, "model_count": 11, "root_evidence_fields_present": [], "model_field_presence_counts": {"pricing": 8, "price": 0, "is_free": 0, "free": 0, "plan": 0, "tier": 0, "billing": 0, "credits": 0, "entitlements": 0, "capabilities": 0, "active": 11, "context_window": 11, "max_completion_tokens": 11}, "price_or_plan_header_present": false}
{"provider": "nvidia_nim", "http_status": 200, "model_count": 83, "root_evidence_fields_present": [], "model_field_presence_counts": {"pricing": 0, "price": 0, "is_free": 0, "free": 0, "plan": 0, "tier": 0, "billing": 0, "credits": 0, "entitlements": 0, "capabilities": 0, "active": 0, "context_window": 0, "max_completion_tokens": 0}, "price_or_plan_header_present": false}
```

Groq pricing structure/value observation (actual stdout):

```json
{"provider": "groq", "pricing_shapes_and_numeric_values": [{"prompt": "7.5E-8", "completion": "3E-7", "image": "0", "request": "0", "input_cache_read": "3.75E-8"}, {"prompt": "8E-7", "completion": "0.000004", "image": "0", "request": "0", "input_cache_read": "4E-7"}, {"prompt": "3E-8", "completion": "3E-8", "image": "0", "request": "0", "input_cache_read": "1.5E-8"}, {"prompt": "0.000022", "image": "0", "request": "0", "input_cache_read": "0.000011"}, {"prompt": "4E-8", "completion": "4E-8", "image": "0", "request": "0", "input_cache_read": "2E-8"}, {"prompt": "0.00004", "image": "0", "request": "0", "input_cache_read": "0.00002"}, {"prompt": "1.5E-7", "completion": "6E-7", "image": "0", "request": "0", "input_cache_read": "7.5E-8"}]}
```

### Feasibility conclusion and open choice

| Path | Current evidence | Consequence |
|---|---|---|
| Strict effective-price/free-only key scope | Source not established for Groq/NVIDIA | Keep discovery; classify eligibility unknown and block inference. This is honest behavior, not successful delivery of both providers' key-only activation. |
| NVIDIA official free-offer policy | Public page/embedded metadata observed; route and capability can be matched | Feasible dynamic implementation candidate without manual lists. Needs owner acceptance of observed-offer semantics, bounded update delay and lack of key-level/atomic billing attestation; implement as a named distinct evidence basis. |
| Groq public list prices plus free-plan table | Both exist but do not establish the key's current plan | Insufficient for key-only free admission. More owner declarations or a model list would repeat the product gap. A supported account-proof/free-only source remains a provider-specific blocker. |
| OpenRouter catalog prices plus supported max_price | [Provider routing](https://openrouter.ai/docs/guides/routing/provider-selection) documents prompt/completion/request/image ceilings | Constructive dynamic source and provider-side ceiling for the bounded text-chat request profile. Does not justify arbitrary paid add-ons or a global guarantee for every feature. |

Independent NVIDIA research supplied both the positive dynamic-offer alternative and its strict-proof limits. No software tests were rerun. Runtime and the separately authorized Groq/NVIDIA YAML entries remain unchanged. Final independent draft/record verification is recorded after review.

## Owner decision following the extended recon

The owner selected strict NVIDIA handling in the structured chat answer on 2026-10-22: without sufficient confirmation for the key, NVIDIA remains unknown and does not generate under the proposed correction. This settles D1 in the draft; the observed-offer alternative is researched but not selected. It is a design decision for the correction, not approval of exact v1.2.0 implementation. The saved v1.1.0 runtime/YAML was not changed by this preparation.

## Additional owner-supplied sources — OpenCode and Kilo

The owner supplied [OpenCode free models](https://opencode.ai/v2/docs/console/models/#free-models) and [Kilo free models](https://kilo.ai/landing/free-models) while corrective preparation was active. These are relevant new gateway candidates and source patterns; they do not replace ongoing Groq/NVIDIA obligations or automatically authorize provider activation/account creation.

- OpenCode's documentation lists limited-time free offers and mixed API families. It documents a public model catalog at https://opencode.ai/inference/v1/models and per-model routes, including an OpenAI chat-completions route. Some models require Responses, Anthropic, Gemini or a non-chat protocol; a common catalog cannot be mapped wholesale onto the current adapter. [Inference API](https://opencode.ai/v2/docs/console/api/inference/) and [API overview](https://opencode.ai/v2/docs/console/api/) describe gateway credentials. Do not substitute a Groq/NVIDIA key.
- Kilo's official [models/providers docs](https://kilo.ai/docs/gateway/models-and-providers) document a public catalog at https://api.kilo.ai/api/gateway/models, with pricing/features and free models available anonymously subject to limits. Its free-model page describes automatic filtering from live hosted-model pricing and promotional availability. That is a useful dynamic-source precedent; marketing page counts are not an authoritative fixed catalog.
- Kilo's [API reference](https://kilo.ai/docs/gateway/api-reference) currently names a different API base than its [overview](https://kilo.ai/docs/gateway), so any activation must resolve the exact catalog/chat/auth contract rather than silently mix hosts. The public overview/models catalog URL was measured below. [Authentication](https://kilo.ai/docs/gateway/authentication) and [billing](https://kilo.ai/docs/gateway/usage-and-billing) must be considered: a gateway-side zero cost for BYOK does not prove the underlying provider charges nothing. An anonymous free-only route is a promising separate enforcement scope, pending a concrete integration contract and live proof.

Read-only command: .venv/bin/python /tmp/t007-inspect-public-gateways.py, exit 0. Two documented public catalog GET requests, no authentication/cookies, no inference, trust_env=False, no redirects, bounded bytes/time. Structural samples contain type names only, not raw model IDs. The zero-token-price count is a preliminary filter count, not admitted chat models or proof of all request/account fees.

Actual sanitized stdout:

```jsonl
{"provider": "opencode", "http_status": 200, "model_count": 85, "root_shape": {"object": "str", "data": "list"}, "model_schema_samples": [{"id": "str", "object": "str", "created": "int", "owned_by": "str"}], "pricing_count": 0, "zero_prompt_completion_count": 0, "cost_objects_count": 0, "zero_input_output_cost_count": 0}
{"provider": "kilo", "http_status": 200, "model_count": 401, "root_shape": {"data": "list"}, "model_schema_samples": [{"id": "str", "name": "str", "created": "int", "description": "str", "architecture": {"input_modalities": {"type": "list", "sample": "str"}, "output_modalities": {"type": "list", "sample": "str"}, "tokenizer": "str"}, "top_provider": {"is_moderated": "bool", "context_length": "int", "max_completion_tokens": "int"}, "pricing": {"prompt": "str", "completion": "str", "request": "str", "image": "str", "web_search": "str", "internal_reasoning": "str"}, "context_length": "int", "supported_parameters": {"type": "list", "sample": "str"}, "opencode": {}, "inference_provider_ids": {"type": "list", "sample": null}, "preferredIndex": "int", "isFree": "bool", "mayTrainOnYourPrompts": "bool", "autoRouting": {"models": {"type": "list", "sample": "str"}}}], "pricing_count": 401, "zero_prompt_completion_count": 19, "cost_objects_count": 0, "zero_input_output_cost_count": 0}
```

Observed consequences: OpenCode's measured public list lacks pricing objects, so the documented free-offer/pricing source still needs machine-contract verification; the catalog alone is insufficient. Kilo's measured response does include pricing, supported-parameter/modality fields and route/auto metadata. Its observed token-zero count differs from its marketing-page count; investigate endpoint/population/active/routing differences instead of treating either as a stable quota or silently merging catalogs. Auto-routing aliases need their own free-only guarantee, not just zero placeholder prices. Neither source's price for a model can certify a same-named model dispatched directly with a Groq/NVIDIA key.

These candidates are included in the draft as an explicit proposed follow-up source/integration path, not shipped profiles. No new provider manifest, key, account, generation or implementation is authorized by presenting links. A bounded scope extension may be proposed after checking complete fee semantics, API compatibility, source freshness and free-only enforcement. Existing hard skips and strict NVIDIA selection remain unchanged.

### Stronger anonymous-free enforcement contracts and supplied credentials

Independent checking found a constructive provider-side boundary for both gateway candidates:

- [Kilo authentication](https://kilo.ai/docs/gateway/authentication) explicitly restricts unauthenticated inference to free models; paid access requires authentication. [Usage/billing](https://kilo.ai/docs/gateway/usage-and-billing) distinguishes free models from BYOK requests with zero gateway-side cost but potential direct-provider bills.
- [OpenCode inference authentication](https://opencode.ai/v2/docs/console/api/inference/) explicitly allows free chat models without Authorization and requires it for paid models. Its catalog and chat URLs have different prefixes; use the documented route mapping. Free/non-chat catalog entries still must not be sent to Chat Completions.

This supports a proposed anonymous-only integration profile: dynamically classify models using current authoritative pricing/route/capability evidence and send no account/provider/BYOK key, cookie or auth-bearing passthrough field at all. If a promotion becomes paid, the documented provider boundary requires authentication instead of silently billing the user's account. This is stronger than a stale free badge used with a paid-capable token, but must still be verified through a scoped implementation and actual compatibility checks. No generations were performed here, and policy enforcement was not stress-tested with paid inference.

The owner subsequently stated that OPENCODE_API_KEY and KILOCODE_API_KEY were added locally. A presence-only check using process environment/local dotenv values returned true for both; no values, prefixes, lengths or account identifiers were output. Current Settings does not declare dedicated fields for these providers, and no manifests are installed. The normal service is not claimed to load/use those keys. Future anonymous-only free profiles must not inject them even when configured; an authenticated mode would be a separate price/account scope. No token was sent to either new gateway during that initial public-catalog recon stage; later authorized comparisons are recorded below.

Anonymous profile integration is now a recommended bounded extension candidate, rather than a declaration that both have been activated. Required follow-up: exact chosen Kilo API alias contract, all applicable fees/auto-router behavior, OpenCode dynamic price+route mapping, request-boundary and private-header tests, and actual buffered/SSE free-only evidence. No hardcoded free-ID/suffix heuristic is sufficient. These sources do not change strict direct NVIDIA or unresolved direct Groq requirements.

## Final preparation verification

Independent read-only review confirmed the source interpretation, exact embedded stdout, strict owner-selected NVIDIA policy and the distinction between proposed engine/gateway options and full direct-provider delivery. Request boundaries/zero ceilings, positive OpenRouter capability predicate, observable credential epochs and historical AC wording were clarified after review; the BR-prefix cosmetic typo was corrected. Local links and paired specification markers passed. All protected T-006 hashes, delivered non-YAML T-007 runtime hashes and the last authorized providers.yaml hash remain unchanged. The only newly added path relative to this continuation's saved status is the corrective specification; previous dirty paths were preserved. git diff --check passed.

The draft is suitable for review as a source-blocked proposal, not as an approval-ready claim that strict key-only Groq/NVIDIA evidence has been found. Exact replacement implementation and any new gateway profile scope remain unapproved. At that initial review checkpoint no software tests or generations had been rerun; later authorized micro-probes are recorded below. Independent reviewers wrote no files or read secrets. Current service configuration, including the earlier authorized static Groq/NVIDIA policy, was not changed or restarted.

## Added Hugging Face/Mistral keys and authorized short probes

The owner added HUGGINGFACE_API_KEY and MISTRAL_API_KEY, stated that no billing details were entered on the accounts, and explicitly authorized short testing/configuration research across available keys. Presence-only checks found these keys plus earlier OpenRouter/Groq/NVIDIA/OpenCode/Kilo variables; Gemini remains absent. No values were output. This authorizes bounded reachability investigation, not persistent automatic free certification or approval of the replacement implementation. Strict direct NVIDIA no-generation handling remains settled and no new NVIDIA generation was attempted.

### Current provider findings

- **HF:** [current main pricing](https://huggingface.co/docs/inference-providers/main/pricing) lists no monthly credits for Free users; credits purchase or a subscription are separate choices. The older /en/pricing version still advertises the previous small allowance, so preserve this documentation-version conflict rather than hardcoding either quota. [Current Hub API](https://huggingface.co/docs/inference-providers/main/hub-api) documents per-provider live status, input/output prices, is_free promotional flag and capabilities. That supports dynamic offer discovery, with exact provider binding; automatic fastest/cheapest routing must not silently choose a paid route. The measured snapshot had no explicit free or zero-token-price routes, so no HF inference was sent. This is not a universal claim that HF can never offer free routes.
- HF's token was separately authenticated with the [official SDK whoami endpoint](https://raw.githubusercontent.com/huggingface/huggingface_hub/main/src/huggingface_hub/hf_api.py), using only an HTTP status/boolean report. Identity/permissions do not certify account tariff. Extra OAuth billing permission or browser state is outside the key-only contract; no such flow was run.
- **Mistral:** authenticated model catalog supplies completion_chat/function_calling and aliases, useful for dynamic capability discovery. [Subscriptions](https://docs.mistral.ai/admin/billing-usage/subscriptions) and [billing](https://docs.mistral.ai/admin/billing-usage/billing) distinguish included usage from PAYG: extra usage requires PAYG enabled and prepaid balance. An absence of card data is the owner's current probe boundary, not a machine-readable promise that account settings can never change. [Admin API](https://docs.mistral.ai/admin/admin-api/overview) is Enterprise-only with a separate Admin key; ordinary inference keys explicitly do not work, so no admin endpoint was probed.
- A short Mistral candidate was selected dynamically from chat-capable, non-archived, non-fine-tuned catalog entries (no model-ID list). Buffered and SSE probes succeeded. The independent function-calling count is not a subset count of chat-capable tools; no tool call or quality benchmark was attempted. These are direct external protocol checks, not proxy integration or dynamic tariff proof.

### Actual sanitized observations

Temporary command: PYTHONPATH=. .venv/bin/python /tmp/t007-hf-mistral-probe.py. Catalog GETs plus at most one buffered/SSE Mistral micro-completion, max_tokens=8, non-sensitive fixed prompt. Responses bounded to 4 MiB and 20 seconds/request; trust_env=False, redirects disabled, private HTTP diagnostics. No response text/model IDs/keys/account identifiers retained. No HF inference without a qualifying current route.

```jsonl
{"provider": "huggingface", "catalog_http_status": 200, "catalog_model_count": 129, "root_price_count": 0, "catalog_proves_key_tariff": false, "provider_route_count": 272, "provider_pricing_count": 176, "explicit_free_route_count": 0, "zero_token_price_route_count": 0, "free_flag_and_zero_price_route_count": 0, "completion_outcome": "NOT RUN", "completion_reason": "no_account_scoped_free_route_contract_established"}
{"provider": "mistral", "catalog_http_status": 200, "catalog_model_count": 53, "root_price_count": 0, "catalog_proves_key_tariff": false, "chat_capable_count": 27, "function_calling_count": 35, "account_plan_evidence_present": false}
{"provider": "mistral", "probe": "direct_external_reachability_only", "stream": false, "http_status": 200, "max_tokens": 8, "dynamic_free_eligibility_proved": false, "valid_chat_response": true}
{"provider": "mistral", "probe": "direct_external_reachability_only", "stream": true, "http_status": 200, "max_tokens": 8, "dynamic_free_eligibility_proved": false, "valid_sse": true, "done_count": 1}
```

Temporary command: PYTHONPATH=. .venv/bin/python /tmp/t007-hf-key-check.py, documented read-only whoami-v2, no identity fields output:

```jsonl
{"provider": "huggingface", "whoami_http_status": 200, "token_authenticated": true, "proves_free_tariff": false}
```

### Gateway short-probe continuation under the same authorization

The owner also authorized short tests for the earlier supplied keys. Anonymous free routes were preferred to avoid account/BYOK exposure. Temporary tools select from current public API/doc metadata, not hardcoded model identifiers. No new runtime/provider was installed.

Initial temporary command .venv/bin/python /tmp/t007-anonymous-gateway-probe.py used an overly conservative Kilo predicate requiring optional request/image prices to be present. It found no candidate; no inference was attempted for Kilo at this stage. OpenCode selected a current official free chat offer by intersecting its catalog, pricing table and exact chat route, then got HTTP 403 anonymously. No SSE retry followed that failure.

```jsonl
{"provider": "kilo", "catalog_http_status": 200, "dynamic_candidate_count": 0, "selection_basis": "live_catalog_free_flag_zero_prices_text_profile_anonymous_only", "authorization_sent": false, "source_proves_direct_groq_nvidia_free": false}
{"provider": "kilo", "outcome": "NOT RUN", "reason": "no_adequate_dynamic_candidate"}
{"provider": "opencode", "catalog_http_status": 200, "dynamic_candidate_count": 8, "selection_basis": "live_catalog_intersection_official_free_price_and_chat_route_anonymous_only", "authorization_sent": false, "source_proves_direct_groq_nvidia_free": false}
{"provider": "opencode", "stream": false, "http_status": 403, "authorization_sent": false, "max_tokens": 16, "probe": "direct_external_anonymous_reachability", "outcome": "auth_quota_or_access_blocked"}
```

Diagnostic .venv/bin/python /tmp/t007-kilo-filter-check.py established where the initial candidate set vanished. This is a temporary recon filter correction, not a runtime bug fix or evidence of paid Kilo models:

```jsonl
{"provider": "kilo", "selection_filter_diagnostic": [{"filter": "is_free", "remaining": 17}, {"filter": "free_suffix", "remaining": 13}, {"filter": "zero_prompt_completion", "remaining": 13}, {"filter": "zero_request_image", "remaining": 0}, {"filter": "all_price_values_zero", "remaining": 0}, {"filter": "text_input_output", "remaining": 0}, {"filter": "not_auto_routing", "remaining": 0}]}
```

Refined command .venv/bin/python /tmp/t007-kilo-anonymous-refined.py relied on current explicit free flag, exact free-route identity, zero input/output prices, text modality, no auto-routing alias, no contradictory applicable price fields, and the documented anonymous-free-only contract. Missing optional fee keys were not treated as a general zero-price certificate; the provider auth boundary supplied the additional protection for this direct test. It made a buffered/SSE micro-completion without any key, max_tokens=16:

```jsonl
{"provider": "kilo", "catalog_http_status": 200, "dynamic_candidate_count": 13, "selection_basis": "catalog_free_offer_and_documented_anonymous_free_only_contract", "authorization_sent": false, "source_proves_direct_groq_nvidia_free": false}
{"provider": "kilo", "stream": false, "http_status": 200, "authorization_sent": false, "max_tokens": 16, "probe": "direct_external_anonymous_reachability", "valid_chat_response": true}
{"provider": "kilo", "stream": true, "http_status": 200, "authorization_sent": false, "max_tokens": 16, "probe": "direct_external_anonymous_reachability", "valid_sse": true, "done_count": 1}
```

A separate owner-authorized OpenCode comparison, PYTHONPATH=. .venv/bin/python /tmp/t007-opencode-authorized-probe.py, sent its own provided token only to the documented OpenCode chat endpoint for a currently documented free offer, max_tokens=16. It also returned HTTP 403 and stopped before SSE. This one-off diagnostic does not change the future anonymous-only profile or prove account free-only enforcement. The reason for 403 is unresolved; do not label the key invalid, attribute it to billing or generalize to every OpenCode model.

```jsonl
{"provider": "opencode", "probe": "owner_authorized_direct_free_offer_reachability", "authorization_sent": true, "stream": false, "http_status": 403, "max_tokens": 16, "dynamic_account_free_enforcement_proved": false, "outcome": "auth_quota_or_access_blocked"}
```

All standalone diagnostics completed with exit 0, while each probe's actual status is reported above; wrapper exit 0 is not a service success claim. An authenticated public catalog response alone does not validate a token. Mistral completions and HF whoami provide stronger authentication observations. Kilo's direct anonymous success is not normal-application integration, paid-enforcement stress testing, or direct NVIDIA eligibility proof. Automated backend tests were not rerun for these record-only changes. Runtime/.env/YAML were not edited, and no service restart or external deployment occurred.

## Ollama Cloud and reactive billing safeguards — subsequent owner steering

The owner asked to include Ollama Cloud's free allowance, cut off a provider immediately if a response reports paid cost, and switch to other models/providers when balance is insufficient. These requirements extend the proposed correction; they do not approve exact replacement implementation or waive strict direct NVIDIA evidence.

### Ollama Cloud versus local execution

Current [Ollama pricing](https://ollama.com/pricing) includes starter usage for Free accounts/starter models and also permits purchased credits. Included allowance is used before purchased balance. This is an account-limited allowance, not a public statement that every cloud model has zero token price. Do not hardcode old hourly/weekly quota numbers; current published terms describe monthly plan usage.

[Cloud API](https://docs.ollama.com/cloud) documents the public /api/tags catalog and authenticated /api/chat. [OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility) documents https://ollama.com/v1 and also notes local-server cloud access. Consequently localhost/auth-none does not prove local computation: the current built-in local exemption must not automatically certify models forwarded to a paid-capable cloud account. A cloud model needs its own adequate eligibility scope. Native [usage fields](https://docs.ollama.com/api/usage) describe token counts and durations; they are not a documented monetary-charge field.

Temporary command .venv/bin/python /tmp/t007-ollama-cloud-catalog.py read only the documented public cloud catalog and checked OLLAMA_API_KEY presence. No key was present, no credentials sent, no inference/account change. Actual stdout:

```jsonl
{"provider": "ollama_cloud", "catalog_http_status": 200, "catalog_model_count": 23, "root_model_field_present": true, "model_pricing_count": 0, "account_evidence_fields_present": [], "api_key_present": false, "authorization_sent": false, "completion_outcome": "NOT RUN", "completion_reason": "account_free_only_source_not_established"}
```

No reviewed key-only account allowance/balance/free-only enforcement source was established for Ollama Cloud. Keep it as a separate researched candidate; no cloud manifest or local authentication bypass is approved by this observation.

### Monetary fields and existing handling gaps

[OpenRouter usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting) documents usage.cost as the amount charged to the account, available in a buffered response or final SSE message. Upstream inference cost is a separate quantity; public rate cards, estimates, sponsored upstream costs and token counts are not automatically a charge to the operator. Zero/missing/synthetic usage cannot certify free access. Not every provider documents a monetary response field.

[OpenRouter errors](https://openrouter.ai/docs/api_reference/errors-and-debugging) distinguish insufficient credits from transient in-flight budget pressure, including metadata limit_source and possible Retry-After. Exhausted typed budgets can also be represented by other status codes. Do not classify all quota words, every 402 or every 403 as the same wallet failure. Mistral's documented 402 beyond included allowance likewise requires provider-scoped treatment; new provider mappings need explicit source support.

Current source observations: adapter _error treats 402 generically; SSE error parsing maps explicit billing errors to 502 or a substring-derived 429. CascadeRouter applies model-level cooldown, so later candidates can hit the same unavailable wallet. There is no monetary usage guard. The adapter swallows late upstream errors, and router records stream success on initial handoff. Those contracts need explicit correction for late paid usage/error reporting. Meaningful output also includes tool-call/reasoning deltas, not only delta.content; restarting after such output risks duplicate side effects.

Required direction: provider-specific charge extraction before buffered success and on every SSE event, including usage-only events; latch a shared provider/endpoint/credential guard on an unexpected positive operator charge; cancel/close owned upstream work best effort and prohibit new dispatch in that scope. Before output, continue safely to another eligible provider within budget. After meaningful output, terminate with a safe stream error and no replacement answer/fake successful DONE. Keep balance holds separate from paid-cost incidents, classify provider-specific codes/metadata, and define bounded recovery independently of the deferred adaptive-breaker task.

An after-response guard is reactive. It cannot refund a completed request, detect a charge the provider does not report, or guarantee all concurrent already-sent work stopped billing. Adequate preflight/free-only enforcement remains the primary admission condition; positive-cost detection adds protection rather than licensing probes of arbitrary paid models.

## Final extended preparation checkpoint

Independent read-only verification matched all seven continuation stdout captures and reviewed HF/Mistral source semantics, anonymous Kilo versus selected OpenCode failure, Ollama Cloud/local provenance, monetary payer/timing, billing-error classification and fixed recovery. Historical no-token/no-generation statements were qualified to their earlier stage. Unestablished OpenRouter 402 metadata literals were removed; known transient 402 and documented typed 403 budget cases remain distinct. No material findings remain for presenting this explicitly source-blocked draft. This is not implementation approval or proof that direct Groq/NVIDIA/HF/Mistral/Ollama account pricing is solved.

Final local record links, paired markers and git diff --check passed. Delivered runtime, protected T-006 hashes and last authorized providers.yaml remain unchanged. No backend test suite rerun, deployment, commit or push. Independent reviewers wrote no files, read no secrets and sent no authenticated/inference requests. Preparation's direct network probes are the separately authorized sanitized observations above; current runtime has none of the proposed billing guards or new gateway profiles active.


## Final proposal checkpoint — owner response policy (2026-10-22)

The owner explicitly requested the final T-007 specification for approval and settled the consumer policy: return a ready answer without an error, block the provider scope, switch before output, and never restart an SSE answer after output has begun. This supersedes earlier draft wording that always converted late cost into a consumer error. The final v1.2.0 section 6A and AC-D13/D14 distinguish complete valid responses from incomplete pre-output and incomplete started responses; completion takes precedence. Shared cancellation preserves complete answers, successful delivery and the billing incident are recorded separately, and genuine generation failure remains failure. No replacement runtime is authorized by this drafting instruction.

The final proposal's concrete approval object is a bounded strict correction: evidence engine/OpenRouter profile, migration and guards, with unsupported direct-provider proof remaining unknown/no-generation. It neither claims the outstanding Groq/NVIDIA source gaps solved nor closes T-007/P2. Gateway integrations remain outside this packet. No new external source claims, probes, backend tests, runtime/configuration changes or .env access were required for this document revision. Earlier probe captures and historical hashes remain unchanged.

Final independent review and local preservation checks: pending at this checkpoint; append actual outcome before handoff.

Final independent outcome: read-only reviewer cleared the completion-first state matrix, shared cancellation/finalization, terminal delivery accounting and bounded-scope coherence. One remaining HANDOFF chronology qualifier was corrected: the no-token statement now explicitly describes the initial presence-only checkpoint, before later authorized OpenCode diagnostics. Reviewer verified local links/markers in eight records, ten saved captures, 25 non-YAML recorded hashes and the latest authorized YAML hash; all matched. No reviewer writes, tests, probes or secret reads. Unchanged external sources were not fetched again.

Final local verification: six affected records passed paired-marker/local-link checks (43 local links); all 25 recorded non-YAML hashes and the last authorized YAML hash matched; git diff --check passed. Backend tests were not rerun for these documentation-only changes. Implementation approval remains pending for this exact final v1.2.0 bounded proposal; full provider-source obligations remain open.


## Owner-supplied specification review caveats (2026-10-22)

The owner supplied a review recommending v1.2.0 approval with caveats, without instructing implementation. The proposal now records ordered bounded implementation checkpoints with focused and full regression gates, a conditional precedence banner in the historical base and the provider-specific OpenRouter routing boundary in ARCHITECTURE. Request enforcement precedes billing-guard integration, and incomplete checkpoints cannot activate inference. Local provenance without adequate evidence is unknown from B1; B4 verifies that safety boundary, not an invented classifier. Existing settled policy and BR/AC scope are unchanged. New SDK fields intentionally receive the fixed unsupported-request 400 until a reviewed extension. Preparation/spec review and future independent AC-D12 implementation review remain distinct; the latter is NOT RUN. No runtime, manifest, secrets or probe changes were made.

Caveat-delta verification: independent read-only review found no issues in checkpoint dependencies, full regression gates, conditional precedence banner, OpenRouter dispatch separation or pending authorization. It verified 52 local links across the six reviewed records including the new section fragment, paired markers, 25 non-YAML hashes and the authorized YAML hash. Reviewer writes: none; no tests/network/secret reads. Local git diff --check passed. The runtime is unchanged; AC-D12 remains a future implementation-result gate.


## Implemented strict correction and newly measured OpenRouter source gap (2026-10-22)

Owner approved exact v1.2.0 with caveats and B1–B4 and instructed implementation under PROJECT-PROCESS.md. The scoped evidence engine, request boundary, billing guards and provenance fail-closed behavior are now implemented in the saved candidate. Historical source gaps remain, not replaced by fixture admission. Runtime verification/evidence belongs to notes/T-007-results.md.

The new actual authenticated catalog/evidence checks returned zero admitted models for every measured provider. OpenRouter's required pricing.request was absent in every one of 468 entries, including 20 explicit zero-token offers; current strict classification is therefore unknown/price_scope_unknown. A public follow-up GET of one dynamically selected zero-token model's documented endpoint-detail route also lacked request pricing (one endpoint). This sample does not establish every model/endpoint's schema. The current model source and published example differ: [official Models guide](https://openrouter.ai/docs/guides/overview/models) and [official API reference](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties) illustrate the request field, but do not define omission as zero.

The [official provider routing contract](https://openrouter.ai/docs/guides/routing/provider-selection#max-price) documents a per-request ceiling in max_price and rejection when no price matches, unlike soft performance preferences. This supports a proposed bounded provider-enforced guarantee; it does not turn a missing catalog value into an observed zero or prove flawless platform billing. No deliberately paid request or inference enforcement stress test was performed.

The owner then explicitly requested preparation of a justified source/admission amendment for approval. [Proposed v1.2.1](../../specs/T-007-openrouter-price-evidence-amendment.md) separates absent request price from zero invoice, retains all ceilings and proposes a distinct enforced basis. It is NOT implemented/approved. v1.2.0 remains strict. No gateway activation, relaxed NVIDIA policy, new provenance parser, .env edit, account change or deployment occurred.

Reproducible public-source follow-up: .venv/bin/python /tmp/t007_openrouter_contract_recon.py; sanitized stdout /tmp/t007-v121-openrouter-source-contract.jsonl. The script uses only the fixed public OpenRouter catalog and a documented endpoint-detail path constructed from a dynamically selected catalog ID; redirects/ambient proxies disabled, no credentials/inference.

Capture: `/tmp/t007-v120-groq-evidence.jsonl`

```json
{"outcome": "UNVERIFIED", "catalog_outcome": "succeeded", "code": null, "catalog_count": 11, "admitted_count": 0, "duration_ms": 370.57, "eligibility": {"states": {"free": 0, "paid": 0, "unknown": 11}, "reasons": {"account_evidence_unavailable": 11}}, "billing": {"kind": null}, "source_ids": ["unsupported_eligibility"], "bases": ["none"], "source_age_seconds": 0.0, "observed_at": "2026-10-22T21:15:45.456956+00:00", "expires_in_seconds": 120.0}
```

Capture: `/tmp/t007-v120-nvidia_nim-evidence.jsonl`

```json
{"outcome": "UNVERIFIED", "catalog_outcome": "succeeded", "code": null, "catalog_count": 83, "admitted_count": 0, "duration_ms": 942.79, "eligibility": {"states": {"free": 0, "paid": 0, "unknown": 83}, "reasons": {"enforcement_unverified": 83}}, "billing": {"kind": null}, "source_ids": ["unsupported_eligibility"], "bases": ["none"], "source_age_seconds": 0.001, "observed_at": "2026-10-22T21:15:43.971034+00:00", "expires_in_seconds": 119.999}
```

Capture: `/tmp/t007-v120-openrouter-evidence.jsonl`

```json
{"outcome": "UNVERIFIED", "catalog_outcome": "succeeded", "code": null, "catalog_count": 468, "admitted_count": 0, "duration_ms": 911.84, "eligibility": {"states": {"free": 0, "paid": 0, "unknown": 468}, "reasons": {"price_scope_unknown": 468}}, "billing": {"kind": null}, "source_ids": ["openrouter_zero_price"], "bases": ["none"], "source_age_seconds": 0.008, "observed_at": "2026-10-22T21:15:46.034323+00:00", "expires_in_seconds": 119.992}
```

Capture: `/tmp/t007-v120-mistral-evidence.jsonl`

```json
{"outcome": "UNVERIFIED", "catalog_outcome": "succeeded", "code": null, "catalog_count": 53, "admitted_count": 0, "duration_ms": 1063.34, "eligibility": {"states": {"free": 0, "paid": 0, "unknown": 27}, "reasons": {"account_evidence_unavailable": 27}}, "billing": {"kind": null}, "source_ids": ["unsupported_eligibility"], "bases": ["none"], "source_age_seconds": 0.0, "observed_at": "2026-10-22T21:15:46.149503+00:00", "expires_in_seconds": 120.0}
```

Capture: `/tmp/t007-v120-huggingface-evidence.jsonl`

```json
{"outcome": "UNVERIFIED", "catalog_outcome": "succeeded", "code": null, "catalog_count": 128, "admitted_count": 0, "duration_ms": 544.35, "eligibility": {"states": {"free": 0, "paid": 0, "unknown": 128}, "reasons": {"account_evidence_unavailable": 128}}, "billing": {"kind": null}, "source_ids": ["unsupported_eligibility"], "bases": ["none"], "source_age_seconds": 0.002, "observed_at": "2026-10-22T21:15:45.675421+00:00", "expires_in_seconds": 119.998}
```

Capture: `/tmp/t007-v120-local_ollama-evidence.jsonl`

```json
{"outcome": "UNVERIFIED", "catalog_outcome": "succeeded", "code": null, "catalog_count": 1, "admitted_count": 0, "duration_ms": 23.39, "eligibility": {"states": {"free": 0, "paid": 0, "unknown": 1}, "reasons": {"unsupported_eligibility": 1}}, "billing": {"kind": null}, "source_ids": ["unsupported_eligibility"], "bases": ["none"], "source_age_seconds": 0.0, "observed_at": "2026-10-22T21:15:45.806831+00:00", "expires_in_seconds": 120.0}
```

Capture: `/tmp/t007-v121-openrouter-source-contract.jsonl`

```json
{"observed_at": "2026-10-22T21:22:32.375225+00:00", "http_status": 200, "catalog_count": 468, "missing_request_price_count": 468, "zero_prompt_completion_count": 20, "simple_zero_price_count": 20, "sample_endpoint_http_status": 200, "sample_endpoint_count": 1, "sample_endpoint_pricing_fields": [["completion", "discount", "prompt"]], "sample_endpoint_explicit_request_count": 0, "generation_requests": 0, "authenticated_requests": 0}
```

Final independent runtime QA cleared the exact strict candidate after all repairs and verified its 285 passed / 9.71s capture. The separate v1.2.1 proposal was checked against the current official max_price/request-ceiling rejection contract, Models price units/overrides description and the sanitized source capture. No numerical source claim or unsafe missing=zero inference remains. The amendment is still a proposal; no amended admission, free live-pass or result acceptance is implied. Reviewer writes none, no test/authenticated/inference/.env actions. Latest candidate hashes, AC status, checkpoint deviation and environment gates are maintained in the results note.


## Approved OpenRouter amendment implementation and bounded live result (2026-10-22)

Owner explicitly approved exact T-007 v1.2.1 including its live checks. The implemented absent-request basis and owned-policy checks yielded a new actual source result: 468 catalog entries / 20 admitted free_enforced / 322 paid / 126 unknown. This replaces the historical strict-v1.2.0 observation only for current amended code; source metadata still has no synthesized request price.

The permitted real proxy probe sent one buffered generation with actual zero ceilings and max_tokens=32, trace attempt_count=1. Proxy returned 503, billing hold null, monetary reporting unavailable. The upstream cause was not retained by the first probe version; do not infer a specific external error or absence of charge. Probe stopped, SSE was not run and no external generation was retried. AC-O7 remains UNVERIFIED. Safe HTTP/status diagnostics were then improved and tested locally; no extra live call was made. Detailed commands, exact sanitized captures, candidate hashes and AC trace are maintained in notes/T-007-results.md. No unsupported provider activation, .env edit, account change or external deployment.

## Renewed diagnostic checks and wire-schema finding (2026-10-22)

Owner authorized one renewed buffered and one SSE attempt at 32 output tokens each. Both were used once, both upstream HTTP 400 → proxy 503. Safe SSE diagnostics referenced provider/request without a specific type error. Public official [OpenAPI](https://openrouter.ai/openapi.json), ProviderPreferences.properties.max_price, requires string price values. Prior dispatch sent numeric zeros; corrected dispatch uses canonical "0" for all four mandatory axes with require_parameters=true. This demonstrates a payload defect and plausibly explains 400; neither sole causality nor post-fix external success is proven. No additional generation after repair. All 323 local tests pass; independent delta review clear. Exact captures, current hashes and exhausted allowance are recorded in [results](../../notes/T-007-results.md). No financial-policy relaxation or account change.

## Post-fix delivery check (2026-10-23 UTC)

Owner authorized another one buffered and one SSE attempt at 32 tokens each. Both used exactly once with string-zero caps verified; both still upstream 400 → proxy 503. The type correction alone does not restore delivery. Exact remaining rejection cause is unresolved; temporary diagnostic fixed phrase matching added no cause. No raw error persisted, no runtime change, no further generation. AC-O7 remains UNVERIFIED; latest allowance exhausted. Exact captures and commands are in [results](../../notes/T-007-results.md).

## Music admission defect and verified repaired delivery (2026-10-23)

Public source snapshots /tmp/t007-rootcause-public-models.json and /tmp/t007-rootcause-lyria-public.json reproduce the first two zero-token-price candidates as Lyria music text+audio endpoints. Official [Clip](https://openrouter.ai/google/lyria-3-clip-preview) and [Pro](https://openrouter.ai/google/lyria-3-pro-preview) pages document song charges. The contains-text predicate was therefore insufficient to certify the closed text-only-output profile. The observed provider INVALID_ARGUMENT → OpenRouter 400 → isolated proxy 503 identifies the error chain, but not the exact rejected argument.

Owner authorized repair and necessary repeated 32-token checks with all free constraints. Current evidence requires exactly ["text"] output; mixed outputs unknown / unsupported_output_modality, without model lists. Current source: 468 total, 18 admitted, 322 paid, 128 unknown. Probe criteria now require visible answer output in both modes; empty/reasoning-only HTTP200 is not PASS. Some candidates exhaust the 32-token budget or fail transiently, and historical music/protocol-only results are invalidated as text-chat proof.

Actual final buffered/SSE pair in /tmp/t007-rootcause-scan-12.jsonl passed with visible output, reported usage.cost=0, max_tokens32, mandatory zero caps and one attempt each. Scan stopped after success; no saved candidate list or production routing change. Final regression334passed/11.20s. [Results](../../notes/T-007-results.md) preserves full ledger, exact final capture, hashes, limits and distinct result-acceptance/P2 gates. No managed restart, account/.env edit, deployment or commit.
