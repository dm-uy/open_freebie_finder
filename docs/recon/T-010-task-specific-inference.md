# T-010 Input RECON — Task-specific free inference

Date: 2026-10-23. Status: measured input for specification preparation, not implementation approval.

## Authority, route and measured baseline

The owner requested synchronization of affected project records, placement of this work as the nearest route item, then reconnaissance and a separate specification for embeddings, rerank, decisions and speech under PROJECT-PROCESS.md. Dynamic free determination and task-separated catalogs are settled constraints. T-010 now precedes T-008 within P2/B-002; existing T-007/P2 obligations and P3/P4/P5 dependencies remain. Implementation, provider inference, primary restart and publication are not authorized by preparation.

Branch main; reachable HEAD `78a1aa4790293781aafe81e786ee4e3b7f098ef2`, plus accepted uncommitted T-006/T-007/T-009 work. Old `6d49e2a` references in dated proofs predate the authorized process-file history rewrite. Starting inventory: `/tmp/t010-start-status.txt`. Runtime/test/config byte inventory: `/tmp/t010-runtime-before.json`. Neither HEAD nor a clean checkout alone represents the running accepted implementation.

Fresh `.venv/bin/pytest backend/tests -q`: **493 passed in 16.62s**, output `/tmp/t010-baseline-pytest.txt`. First sandbox run returned465 passed/28 failed because loopback `socket.bind` was denied; rerunning the existing suite with permitted loopback access passed. These are local synthetic/fixture tests, not new live provider inference. No production secret file was inspected; no service lifecycle action occurred.

## Existing producers, consumers and non-reusable assumptions

| Source inspected | Observation | Consequence |
|---|---|---|
| `backend/app/api/v1/__init__.py`, `models.py` | Only chat/models mounted; default model listing is in-memory eligible canonical chat IDs plus auto:free | Preserve default picker and zero-I/O listing; add explicit task views |
| `core/providers/models.py`, `registry.py` | DiscoveredModel has no task field; provider snapshot registration replaces that provider's entire list; canonical alias map assumes chat | Do not feed task inventories through destructive chat registration or share ambiguous alias resolution |
| `core/discovery/orchestrator.py` | Single lifespan owner, bounded GET, chat-oriented parser; nontext output is filtered | Add task-specific snapshots/scheduling without another unowned worker or loss of chat freshness |
| `core/eligibility/evidence.py` | Evidence indexed by provider/raw ID; one captured scope binds chat endpoint/source/profile; output must be exactly text | Chat eligibility cannot certify another task. Mutating its manifest/source for task discovery would revoke chat assertions |
| `core/eligibility/account.py`, `probes.py` | Explicit provider account assertion and private paired chat qualification; bounded send budgets | Existing confirmation is not approval for nonchat probes; no automatic task generation on startup |
| `core/eligibility/request.py`, `adapters/openai_client.py` | Closed text-chat request schema; chat URL builder and JSON/SSE framing | New task validators/transport are required; a generic path substitution is unsafe |
| `core/balancer/router.py` | May fall back to a different chat model, with requested identity masking | Unsuitable for embedding vector space and task-specific semantic contracts |
| `core/eligibility/billing.py` | Recognizes pinned profile monetary mapping; active I/O and pruning depend on scope | Share account protection across tasks without inventing cost fields or allowing prune/scope escape |
| `core/balancer/resilience.py` | Registry-owned route/quota/auth gates with generation fencing; auth identity distinct from endpoint scope | Task routes need distinct service state but common credential protection; preserve recovery ownership |
| `core/telemetry/models.py` | Completion-specific trace has no task field | Keep old chat schema stable; new task diagnostics must not silently relabel chat metrics |
| `main.py`, admin provider validation and protected tests | Existing lifespan integrates orchestrator; validation deliberately isolated | Mount through existing routers/lifecycle hooks; preserve protected T-006/main files |

DEC-002 favors declarative provider identity with owned protocol handling, not arbitrary outbound URLs. DEC-003's masking and alternative-model fallback are chat rules, not proof of vector equivalence. DEC-005's financial/source/credential precedence remains binding. No persistent runtime schema/database is used for these new tasks.

## Official source register and verified interfaces

Sources read on2026-10-23; source descriptions below are observations, not a promise that a free model is available for the owner's key.

| ID | Primary source | Verified fact / limit |
|---|---|---|
| S1 | [Models guide](https://openrouter.ai/docs/guides/overview/models) | Unfiltered API model catalog defaults to text; explicit output_modalities filters/all cover other tasks. Website filter URLs are not the production discovery contract |
| S2 | [Embedding request](https://openrouter.ai/docs/api/api-reference/embeddings/submit-an-embedding-request) and [embedding catalog](https://openrouter.ai/docs/api/api-reference/embeddings/list-all-embeddings-models) | POST `/api/v1/embeddings`; separate GET `/api/v1/embeddings/models`; vector request/response differs from chat |
| S3 | [Rerank request](https://openrouter.ai/docs/api/api-reference/rerank/submit-a-rerank-request) | POST `/api/v1/rerank`; query/documents produce indexed relevance results; search-unit usage exists |
| S4 | [Decisions request](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request) | POST `/api/alpha/decisions`; state/questions produce typed answers; alpha surface; example includes usage.cost |
| S5 | [Speech request](https://openrouter.ai/docs/api/api-reference/tts/create-speech) | POST `/api/v1/audio/speech`; raw audio, provider-specific voices; mp3/pcm in current reference; not SSE chat framing |
| S6 | [ProviderPreferences](https://openrouter.ai/docs/client-sdks/python/components/providerpreferences) | Shared routing preference schema includes max_price/require_parameters; task SDK methods link it for embeddings/rerank/decisions. Schema acceptance alone does not prove every task fee is capped |
| S7 | [SpeechRequestProvider](https://openrouter.ai/docs/client-sdks/python/components/speechrequestprovider) | Speech provider object documents data policy/options, not the same zero-price routing controls |
| S8 | [Speech tutorial](https://openrouter.ai/blog/tutorials/text-to-speech/) | Voice/format support varies; a raw audio result does not carry a JSON usage.cost body |

Old rerank `create-rerank` documentation URL returned404; canonical S3 works. Some Markdown-reference fetches failed through the research tool; their HTML references above were readable. Descriptions mentioning upstream `/v1/systemone` do not replace OpenRouter's S4 URL. The four original website-filter pages did not reliably render through the research tool; no result counts are inferred from them.

Public unauthenticated catalog observations by the source researcher show zero-token-price candidates for embedding/decisions with omitted request pricing; omission is not zero. Inventory is volatile and no observed model IDs become admission lists. Speech pricing can use different units; interpreting every prompt price as tokens would be incorrect. No key-based entitlement or actual free delivery was checked in this preparation.

## Confirmed gaps and bounded interpretation

1. There are two exclusions: OpenRouter's text-default API catalog and our chat-only parser/evidence. Removing only the output filter would expose unserviceable/nonfree tasks through chat.
2. Nonchat price coverage is not established by T-007 v1.2.1's chat-specific omitted-request exception. Shared ProviderPreferences permits a policy object structurally, but neither that nor token-zero rows proves request/search/audio/character fees are enforced to zero. Missing coverage must remain unknown.
3. Speech has no verified equivalent of the chat zero-ceiling contract or synchronous monetary body. It must remain undispatchable under strict mode until sufficient independently verified evidence exists. Endpoint support and positive free live supply are separate completion claims.
4. Existing account assertions and budgets cover chat qualification. Broadening them to other task/provider combinations would need a separately approved profile; this specification proposes OpenRouter as the first upstream only.
5. Embedding indexes require a stable model/revision vector space. Same dimensions or matching canonical spelling is not equivalence. No generic alternative-model cascade should be reused.

## Independent proposals and assessment

Read-only native code researcher `verify_t006` and public-source researcher `nonchat_sources` had write permission NONE; starting dirty status was saved before dispatch. Their proposals converge on additive task catalog/evidence, default chat listing, exact-target inference and shared account guards. Root assesses the proposals in the specification's Options table; choices remain proposals submitted for owner approval, not pre-approved architecture.

Alternatives retained: expand the existing chat model registry versus an additive task layer; a combined public model list versus default chat with explicit task query; automatic generic-model fallback versus exact-target retries; stream speech bytes versus bounded full buffering; provider-wide expansion versus OpenRouter-first scope. Favor preserving established clients, account protection and proof boundaries over broader nominal model counts.

## Next permitted step

Complete [T-010 specification](../../specs/T-010-task-specific-inference.md), independently review source claims/traceability/scope, synchronize affected records and present the exact version for approval. Source gaps are deterministic exclusions, not authority to invent a working billing profile. Retain all previous accepted implementation/integration evidence and uncommitted files. No new task may be called live-passed from mocks or an empty eligible list.

## Specification review and preserved implementation state

Root prepared v1.0.0 with N1–N4 and18 AC. Independent source review by nonchat_sources initially identified four overclaim/budget risks: Decisions cost payer/currency not proven by an example, task-specific cache fee meanings not sourced, missing dimensions/format catalog metadata, and isolated lifespan accidentally inheriting chat qualification. All four were corrected and the source reviewer confirmed PASS against the saved specification. This reviews sources/specification, not implementation or provider delivery. Independent cumulative specification review by verify_t006 found one ownership ambiguity: protection across registry recreation could conflict with isolated applications. BR-10 was corrected to retain guards across router/orchestrator recreation within the retained registry/controller, with independent registries remaining separate ownership domains and hot primary registry replacement unsupported. The reviewer confirmed the blocker resolved and cumulative review clear; this is specification quality assessment, not owner implementation approval.

Preparation changes only affected project Markdown; both delegated researchers report writes NONE. Runtime/test/config byte inventory remains unchanged. Local links and paired document markers/BR-AC inventory pass; git diff whitespace check passes. No provider inference, secret-file access, account/configuration change, primary lifecycle action, commit/push or external deployment. Existing accepted automatic primary work was not stopped.

## Subsequent approved implementation

The owner subsequently approved exact v1.0.0/N1–N4 on2026-10-23. This document retains the pre-change measured input; it is not the current implementation/status home. [T-010 results](../../notes/T-010-results.md) records implemented source, independent QA, all regression/source checks, protected-path identity and the still-open positive external delivery criterion. No source gap was reinterpreted as free admission.
