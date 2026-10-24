# DEC-002: Declarative Provider Schema and Automated Onboarding

## Context and Problem
Free LLM inference providers fluctuate rapidly: new providers emerge, existing ones update endpoints, rate limits, and model naming conventions.
Hardcoding provider-specific Python classes creates high maintenance friction and forces code rewrites whenever a new provider appears.
Additionally, because 90%+ of modern AI inference providers adhere to the OpenAI REST specification (`/chat/completions`, `/models`, Bearer token auth), hardcoding separate adapters is unnecessary.

We need a flexible, future-proof mechanism to:
1. Support all major existing free providers out-of-the-box.
2. Allow adding new providers via configuration (YAML/JSON/UI) without altering backend code.
3. Allow external desktop agents (Cursor, Claude, Antigravity) to create or update provider configs effortlessly.
4. Provide a stepping stone toward a built-in automated "Provider Onboarding Agent".

## Considered Options

### Option 1: Hardcoded Python Adapter Classes
* *Pros:* Maximum customization per provider.
* *Cons:* Requires code changes, PRs, and deployments for every new service or endpoint change. High coupling.

### Option 2: Declarative Schema + Universal OpenAI-Compatible Adapter (Chosen)
* *Pros:*
  * All providers configured via a clean, structured YAML/JSON schema.
  * A single robust `GenericOpenAIProviderAdapter` handles HTTP requests, authentication, and streaming.
  * Easy to expose through the Admin API and Web UI (CRUD operations).
  * Can be extended and tested instantly by any external agent or developer.
  * Out-of-the-box bundle ships with top providers pre-configured.
* *Cons:* Non-standard providers (e.g. providers that deviate substantially from OpenAI format) require custom mapping rules in schema.

### Option 3: Full Autonomous Agent First
* *Pros:* Fully automated discovery from documentation URLs.
* *Cons:* Over-engineering at step 1; requires an existing LLM or external API key to parse docs before any proxy is even running.

## Decision
1. **Declarative Engine:** Implement a declarative YAML/JSON provider manifest schema (`providers.yaml`).
2. **Universal Adapter:** Implement a unified `GenericOpenAIProviderAdapter` capable of querying any OpenAI-compatible API with configurable:
   * `base_url`
   * `auth_type` (Bearer, custom header) and `api_key_env`
   * `models_endpoint`
   * `free_discovery` rules (e.g., `pricing_zero` JSONPath for OpenRouter, `all_models` for quota-based free keys like Groq/Nvidia, or regex patterns).
3. **Out-of-the-Box 90%+ Coverage Bundle:** Ship with pre-configured manifests for:
   * **OpenRouter** (Dynamic `:free` filter)
   * **Groq Cloud** (Ultra-fast free tier: Llama 3.3 70B, Gemma 2, Llama 3.1 8B)
   * **Google AI Studio (Gemini)** (15 RPM free tier via OpenAI-compatible endpoint)
   * **NVIDIA NIM** (Hosted open weights: Llama 3.3, Nemotron, Mistral)
   * **GitHub Models** (Free tier via Azure AI and GitHub PAT: GPT-4o-mini, Phi-4, Llama 3.3)
   * **Cerebras Cloud** (Ultra-fast 2000 t/s Llama 3.1 8B/70B free tier)
   * **Mistral AI** (Free experiment tier: Mistral Small, Codestral)
   * **Hugging Face Inference API** (Serverless free models)
   * **Cloudflare Workers AI** (10,000 free daily neurons)
   * **Local / Self-hosted** (Ollama / vLLM / LM Studio fallback)
4. **Validation Endpoint:** Implement `POST /api/admin/providers/validate` to test connectivity, model listing, and test completions before enabling a provider.
5. **Phase 2 Evolution:** In Phase 2/3, build a lightweight internal "Onboarding Agent" endpoint that accepts a documentation link and API key, probes the endpoints, generates the manifest, and validates it.

## Consequences
* New providers can be added in seconds via config or Web UI without touching Python code.
* The codebase remains lean and maintainable.
* Provides full readiness for both external and future internal agent-driven onboarding.


## T-007 hybrid assurance refinement (approved, local candidate verified)

On 2026-10-23 the owner accepted strict OpenRouter plus explicit nonbillable-account assertions and dynamic availability probes for Groq/NVIDIA/Mistral/HF, without model-ID lists. [T-007 v1.3.0](../../specs/T-007-hybrid-account-eligibility.md) defines the exact implementation contract, subsequently owner-approved with H1–H4 and the bounded isolated live packet on 2026-10-23. Manifest profiles identify a trusted parser/dispatch binding, not a free certificate; legacy all_models/free flags do not grant admission. OpenRouter's owned max_price/require_parameters routing policy remains provider-specific and mandatory. The four conditional profiles are implemented in the local v1.3.0 candidate and require an operator assertion and fresh private qualification; successful inference is availability evidence only. This refines historical free-discovery examples above; those examples, model names and quota figures are not current billing authority. Exact correction approval is recorded; result acceptance and primary activation remain separate.

The same day's explicitly authorized NVIDIA discovery repair adds an owned public-source parser within its existing profile, intersecting Free Endpoint/chat/availability metadata with exact keyed API IDs. It does not add a provider-specific inference adapter or model lists. Public labels are candidate-selection evidence only; assertion, both-mode qualification and financial holds still govern dispatch. NGC receives no inference credentials and source failure removes admission. Actual live evidence and source-interface stability limits are recorded in [T-007 results](../../notes/T-007-results.md).

The owner then accepted the NVIDIA repair and authorized local primary activation for Groq/NVIDIA/Mistral. Their three explicit confirmations are operator configuration, not shipped defaults; actual primary buffered/SSE delivery is verified. Cold-start provider fairness was repaired by advancing the probe cursor after actual scheduling rather than idle polling, preserving every resource/financial gate. [Primary evidence](../../notes/T-007-primary-activation.md) records the accepted integration and independent412-test checkpoint; earlier pending-activation wording describes its historical stage.


## T-010 approved task extension (2026-10-23)

Owner approval of [T-010 v1.0.0/N1–N4](../../specs/T-010-task-specific-inference.md) extends the source backend with separate task catalogs/protocols and exact OpenRouter task routes. Declarative logical provider identity is retained; task parsing/zero-price controls are owned protocol policy, never arbitrary YAML expressions or client routing overrides. Chat's default listing, alternative-model fallback and response masking do not authorize embedding/rerank/decisions/speech substitution. Task service health is distinct; credential quota/auth and the financial account umbrella protect related chat/task routes together within the retained registry. Independent registries remain isolated. Rerank/speech and incomplete task pricing remain unknown, with no inherited chat omitted-fee exception or account qualification. This approval authorizes implementation, not acceptance of missing external proof or primary activation. [Result evidence and limits](../../notes/T-010-results.md).
