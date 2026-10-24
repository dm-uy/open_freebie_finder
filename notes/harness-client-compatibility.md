# DeepSeek Harness request-profile compatibility

Date: 2026-10-23. Scope: diagnose the owner's `400 unsupported_free_request` and fix the existing custom provider's client configuration. No backend request-profile expansion, new free entitlement, primary restart or provider inference.

## Cause and measured reproduction

The installed Harness OpenAI Chat Completions builder defaults an unrecognized/custom local endpoint to `supportsStore=true`, adding `store:false`. The backend intentionally rejects unknown top-level fields before any upstream inference. Thus this default is incompatible even for an otherwise ordinary text request; changing selected models cannot remove that client-level field.

Read-only sources: installed `/Applications/DeepSeek Harness.app/Contents/Resources/app.asar`, pi-ai `api/openai-completions.js`, and locally linked Harness `packages/llm/llm-pi-ai/src/config.ts`/`catalog.ts`. Both provider/model compatibility settings and route-to-model inheritance are supported. The linked pi-ai builder differs bytewise from the packaged builder; no claim of an identical runtime binary is made.

An offline test invoked the locally linked real pi-ai builder with synthetic messages/tools, intercepted `onPayload` and aborted before fetch. Original payload had `store`/`max_completion_tokens` and was rejected by the actual backend validator; configured payload used `max_tokens`, omitted `store` and passed. Both produced streaming/tool-shaped requests; fetch counter was0. Synthetic captures: `/tmp/off-harness-payload-check.json`; test script `/tmp/off_harness_payload_check.mjs`. This is request construction/validation evidence, not end-to-end generation proof.

## Exact client change

Only the `open-freebie-finder` provider in `/Users/a1111/.dsh/profiles/desktop/cordis.patch.yml` changed, through an approved filesystem escalation. Its endpoint, API-key reference and model selector entries were preserved. Other configuration was checked for semantic equality against the private0600 backup `/Users/a1111/.dsh/profiles/desktop/cordis.patch.yml.bak-off-compat-20261023T155606`. No key or credential store was changed or printed.

Added provider fields:

```yaml
cacheRetention: none
compat:
  supportsStore: false
  supportsReasoningEffort: false
  maxTokensField: max_tokens
  supportsDeveloperRole: false
  requiresThinkingAsText: true
```

This suppresses unsupported storage/cache/reasoning controls, uses the tested output-budget field/system role and avoids replaying raw reasoning extensions as extra assistant-message keys. It does not disable tools or streaming and does not alter the proxy's strict OpenRouter ceilings, conditional account assertions or closed structural validation. Client compatibility does not certify a model's tool capability, multimodal support or account price.

## Verification and continuation

All62 accepted backend/runtime manifest hashes remain unchanged. No project source/configuration, real `.env`, account/free gate or primary lifecycle change. No external request or generation was made for diagnosis. Installed app bundle was read only, never patched. The exploratory filesystem search encountered symlink cycles and was stopped; subsequent reads targeted explicit source paths.

Actual Harness retry remains pending: let Harness reload the changed configuration; if it retains old resolved models, restart the app and select this provider in a new text-only conversation. Existing conversations with unsupported attachments/history or model-specific unsupported features can still be rejected. A successful end-to-end request must be observed before claiming integration PASS. No automatic retry or additional live packet was run.

## Owner-observed follow-up

The owner subsequently reported that Harness works after this client-profile change. This is actual user-observed integration confirmation, not a new instrumented generation capture; no universal tool/multimodal workflow certification or new token/cost figures are inferred.
