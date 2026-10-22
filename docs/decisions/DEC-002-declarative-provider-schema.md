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
