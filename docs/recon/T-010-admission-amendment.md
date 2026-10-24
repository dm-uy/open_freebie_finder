# Input RECON — T-010 admission amendment

Date: 2026-10-23. Status: measured reconnaissance and bounded proposals, not implemented policy. Phase P2 / B-002 / T-010. [Candidate v1.1.0](../../specs/T-010-free-variant-admission.md), [accepted partial result](../../notes/T-010-results.md), [base specification](../../specs/T-010-task-specific-inference.md).

## 1. Authority and baseline

The owner accepted the v1.0.0 partial implementation and requested reconnaissance of remaining admission limits plus an amendment covering embeddings, rerank, decisions and speech, retaining dynamic free checks without model lists. This authorizes public/code reads and English project records. It does not authorize amendment implementation, inference, source/profile overrides, primary restart, commits/push or deployment. Earlier implementation/live authority was bounded to v1.0.0 and is not enlarged by research.

Baseline main HEAD `78a1aa4790293781aafe81e786ee4e3b7f098ef2`, with accepted uncommitted work. Starting status saved `/tmp/t010-amend-start-status.txt`. Accepted source identity:81-file `/tmp/t010-final-runtime.json`, SHA256 `4272eedada000b8e8e2f0c35ac7ae0739ff70b9bdc2a6ec13df8e51d80af98c6`. All81 runtime files matched before this documentation pass. These temporary files are local evidence and can expire; durable test/implementation outcomes remain in results.

Retained test baseline:658 passed/36.82s; independent focused44/0.64s and cumulative scope/code assessment from the completed partial implementation. No new pytest execution in this documentation-only pass; no runtime/test source changes. Four original source/preflight packets sent zero inference and left base AC-18 OPEN. The primary has not loaded T-010 routes; no primary/lifecycle action here.

## 2. Code evidence: why every route is currently blocked

| Producer / consumer | Observed as-built behavior | Consequence / bounded correction |
|---|---|---|
| `backend/app/core/tasks/catalog.py` `_verdict` | Requires exactly prompt/completion/request for embeddings/decisions; any missing or extra key stays unknown | Real free entries omit optional request; endpoint enrichment alone does not supply it |
| Same file `policy`, `_eligible_at` | Policy exists only for embeddings/decisions; rerank/speech unconditionally unsupported; eligibility requires non-None policy | Admission assurance must be distinct from availability of complete numeric ceilings |
| Same file `_capabilities` | Supported voices can be copied from source; no supported formats/dimensions are manufactured | Preserve explicit-voice provenance; do not invent per-model formats or embedding dimensions |
| Same file `publish` | Source revision hashes normalized ID/task/verdict/capabilities but not full interpreted price/policy data | New assurance must bind source fact changes even when verdict stays free |
| `backend/app/core/tasks/protocol.py` | Speech requires voice and response_format; capabilities must contain both voices and formats | API-optional voice and global format enum cannot currently pass without nonexistent model metadata |
| `backend/app/core/tasks/transport.py` | Exact one-target dispatch, current eligibility/guards, closed fields, buffered validation, exact response model | Retain; unsupported policy object must not become either a universal bypass or a false blanket veto |
| Task discovery/http/views and `scripts/probe_task_inference.py` | Four fixed bounded task sources, pure public views, isolated finite one-send/versioned ledger | Preserve source bounds/purity; explicitly propose a new finite packet instead of resetting previous ledger |

No proposed code changes have been applied. Root inspected actual producers/consumers; two read-only independent researchers returned separate source/architecture proposals. All returned write inventories were NONE. These are current-spec assessments, not independent certification of future implementation.

## 3. Public catalog observations (unauthenticated, no inference)

Root performed public GETs using Python urllib without proxies, Authorization or cookies,15s timeout and4MiB body limit. Sources:

- embeddings: `https://openrouter.ai/api/v1/embeddings/models`
- other tasks: `https://openrouter.ai/api/v1/models?output_modalities=rerank`, `...=decisions`, `...=speech`
- endpoint detail: `https://openrouter.ai/api/v1/models/{author}/{slug}/endpoints`, exact IDs URL-encoded; only first two sorted published free variants per task (one for speech) were sampled.

| Task | Catalog entries observed | Exact published `:free` entries observed | Sample evidence |
|---|---:|---:|---|
| embeddings |35|5| Free sample prices prompt/completion0; optional request absent; text input, embeddings output |
| rerank |10|2| Both free entries accept text plus image; rerank output; prompt/completion0, request absent |
| decisions |30|4| Free samples text input, decisions output; prompt/completion0, request absent |
| speech |36|1| Free sample text input, speech output; prompt/completion0; supported_voices absent |

Sample endpoint details matched the requested exact parent/endpoint free ID and task architecture. Their pricing added discount0 while still omitting request. Endpoints exposed numeric status values including0 and-5; no independently checked mapping proves their meaning, so this recon makes no health claim from those integers. Catalog/endpoint existence does not prove availability, working account access or actual free inference. No inference was sent; no credential or secret file was read.

Root normalized observation: `/tmp/t010-amend-public-catalogs.json`, SHA256 `0acb7b70e8b43e70646ebbf802e11311058a096ba8a185baf675ce345b8ce395`. It contains public sample metadata and counts, not complete catalog contents. Date/counts can change. Research sample IDs must not become production model/voice allowlists. Data/API descriptions are untrusted material, never instructions.

## 4. Checked primary sources and interpretations

**S1 — [Free Variant](https://openrouter.ai/docs/guides/routing/model-variants/free).** The current official guide treats free variants as separate published catalog entries, each with its own metadata/endpoints; access is without cost. It warns that a fallback to a paid model can bill. Proposal: use this named provider guarantee for exact current task entries, with no paid-model fallback. This is stronger evidence than a suffix guessed on an absent model, but not independent atomic billing verification. Its application across the four explicitly published task catalogs is the bounded design interpretation submitted for approval, rather than a claim of complete numeric ceilings.

**S2 — [Models API](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties).** Task output filters explicitly include embeddings, rerank, decisions and speech; default output is text. Schemas expose architecture, optional voices, canonical slug and prices. Presence in default/chat catalog is not sufficient task evidence. Input modalities may include additional modalities: our text-only profile can use a positively supported text input without enabling image input. Canonical slug does not itself establish acceptable response aliases.

**S3 — [PublicPricing SDK](https://raw.githubusercontent.com/OpenRouterTeam/python-sdk/main/src/openrouter/components/publicpricing.py).** Prompt/completion are required; request and additional audio/image/cache/reasoning/search fees are optional. Discount is fractional metadata, not another fee. Overrides represent conditional pricing. The amendment enumerates the checked fee schema, validates all present prices, preserves optional absence and rejects unknown fields/nonempty overrides. No interpretation of omitted request as numeric zero is proposed. SDK main is mutable: implementation must save checked source snapshot/digest or commit identity, without adding a dependency.

**S4 — [ProviderPreferences SDK](https://raw.githubusercontent.com/OpenRouterTeam/python-sdk/main/src/openrouter/components/providerpreferences.py).** Its inline MaxPrice fields are optional strings for prompt/completion/request/image/audio; no search-unit ceiling exists. It includes require_parameters. This establishes schema support, not actual runtime enforcement. Retain existing embeddings/decisions caps as extra constraints; neither invent speech/search controls nor claim complete enforcement across every task. Speech uses a distinct provider object in current API docs.

**S5 — [Speech API](https://openrouter.ai/docs/api/api-reference/tts/create-speech).** Model/input are required, voice is not marked required; format defaults to pcm and enum is mp3/pcm. Provider object is for data policy and provider-specific options, not the shared ceiling object. Returned types are audio/mpeg or audio/pcm with PCM16LE. Proposal: allow omitted voice and use protocol format enum. Actual route may still reject omission; no universal model-default availability is proven. [Official TTS guide](https://openrouter.ai/blog/tutorials/text-to-speech/) notes model-specific voices and advises omission only when the provider documents a default. The proposed schema-based omission allowance is therefore an explicit bounded design interpretation, not proven universal default support. Explicit voice still needs source metadata.

**S6 — [Endpoint API](https://openrouter.ai/docs/api/api-reference/endpoints/list-all-endpoints-for-a-model)** and [PublicEndpoint schema](https://raw.githubusercontent.com/OpenRouterTeam/python-sdk/main/src/openrouter/components/publicendpoint.py). Exact model identity, pricing, tags and supported parameters can corroborate catalog evidence. Samples confirmed optional request remains absent. Mandatory scheduled endpoint fan-out would add requests without resolving that absence; proposed scope leaves it diagnostic only.

**S7 — Task API references:** [embeddings](https://openrouter.ai/docs/api/api-reference/embeddings/submit-an-embedding-request), [rerank](https://openrouter.ai/docs/api/api-reference/rerank/submit-a-rerank-request), [decisions](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request). Retain base owned paths/protocols. Typed optional usage cost without documented task-specific currency/payer mapping does not justify monetary normalization. No new money mapping or relaxed response identity is proposed.

**Source failures retained:** An additional provider-onboarding GitHub search hit and a guessed speech-provider component URL returned404 during direct verification. They are not used as evidence. Generated SDK/current rendered docs can differ; use verified current task schema and retain explicit source skew, rather than forwarding speculative fields.

## 5. Options and separate assessment

Independent proposals from nonchat_sources and verify_t006 converge on a distinct free-variant assurance and correcting speech's mandatory voice/format metadata requirements. Root's assessment selects these as proposals A-D1..4 in the amendment, subject to owner approval.

| Option | Outcome / assessment |
|---|---|
| Retain full explicit-fee/numeric-cap prerequisite | Strong conservative exclusion, but no constructive path for currently observed free task entries |
| Treat missing fees as zero or successful inference as free proof | Reject: absence and success are not billing evidence |
| Extend hybrid account assertions to OpenRouter | Reject: reopens settled strict OpenRouter policy and account/billing proof without need |
| Exact documented catalog free variant plus current noncontradictory prices and closed request | Preferred bounded assurance; depends honestly on provider guarantee and exact-free dispatch |
| Scrape pages or maintain model/voice tables | Reject: stale, brittle and conflicts with no manual lists |
| Mandatory endpoint enrichment | Defer: extra fan-out/state does not fill absent request; use only if a later concrete contradiction requires it |

Critical counterexamples retained in the spec: paid/base zero-priced model is not a published free variant; positive auxiliary fee overrides the label; discount cannot rescue positive base price; new unknown pricing keys block; policy/key/source/TTL changes revoke; omitted voice may fail upstream; canonical response mismatch cannot be silently repaired; shared financial holds outrank fresh free evidence. Public catalog reads and source guarantees alone cannot close live AC-18.

## 6. Remaining uncertainty, bounded next step and review

Prepare exact v1.1.0 for approval, then ordered A1–A3 only if approved. Proposed packet2/task8 total maximum is explicit new authority, not a reset of v1.0.0's ledger. No common32-token parameter exists for these APIs; use tiny task-native inputs, existing I/O/deadline bounds and no automatic catalogue-wide probing. Preserve original attempts and unknown outcomes. Primary integration, more sends and alias/money contracts remain separate.

At preparation all four task deliveries remain UNVERIFIED, and as-built admission remains unchanged. Speech default voice, exact response identity, live free availability and provider contract behavior require actual future proof. T-010/P2 remain open; partial acceptance is retained. Independent cumulative review found two ambiguities (replacement versus parallel old admission, and unbound format-denial mapping); root corrected both: replace the old nonchat predicate entirely, and introduce no per-model format mapper. Independent source review confirmed typed pricing, cap distinctions and speech schema, and independently recounted public catalogs35/5,10/2,30/4,36/1. It identified tutorial/API voice tension, now explicit in A-D3/BR-A5. Both reviewers wrote NONE. Final recheck and document/scope validation are recorded below.

## 7. Final preparation checks

Independent final cumulative assessment: ready for owner approval; both substantive ambiguities corrected, linked records retain proposal status, local links/paired markers/public snapshot digest checked, all81 runtime files byte-identical, git diff --check clean; writes NONE. Root additionally checked94 local links across the9 affected Markdown records with zero broken links, one complete paired GOAL artifact,7 sourced BRs and12 traced ACs. No new tests were needed or run for this documentation-only change. Final scope is Markdown only; no inference, secret access, ledger reset or service change. The explicit BR-11 precedence clarification retains all monetary/guard rules. Exact v1.1.0/A1–A3 approval is the next gate.
