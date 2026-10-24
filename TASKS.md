# Active Work Package B-002: Provider Validation, Cross-Provider Cascade, and Structured Telemetry

**Phase:** P2 (Provider Validation API, Adaptive Circuit Breaker, Structured Telemetry, and Onboarding Agent)  
**Status:** Active  
**History Archive:** Previous work package B-001 archived in [notes/batch-B-001.md](notes/batch-B-001.md).  
**Permission:** Authorized transition to Phase P2 following verified completion of Phase P1 (2026-10-22).

---

## T-005 — Structured Request Telemetry and Correlation ID Cascades
- **Status:** `done` — owner accepted review fixes on 2026-10-22.
- **Why:** Every inference request entering `/v1/chat/completions` must carry a traceable request correlation ID (`X-Request-ID` header or generated UUID) across all cascade failover hops, recording candidate attempt sequence, latency per candidate, failure reasons, and synthetic usage.
- **Specification:** [specs/T-005-structured-telemetry-and-validation.md](specs/T-005-structured-telemetry-and-validation.md) (Version 1.1.0, Approval: approved by owner on 2026-10-22)
- **Deliverable and "Done When":** Incoming requests receive or generate an `X-Request-ID` header; logs emit structured JSON with correlation IDs linking all failover hops; completed and failed request telemetry is recorded for in-memory admin queries (`GET /api/admin/telemetry/recent`, `GET /api/admin/telemetry/stats`).
- **Allowed Paths:** `backend/app/config.py`, `backend/app/api/`, `backend/app/core/telemetry/`, `backend/app/core/balancer/`, `backend/app/main.py`, `backend/tests/`
- **Execution and Verification:**
  - Automated tests: `pytest backend/tests` — 37 passed in 0.25s (AC-1..10).
  - AC-1: Zero regression confirmed across all existing 27 test cases.
  - AC-2, AC-3: Custom client and auto-generated `X-Request-ID` headers verified.
  - AC-4: Error envelopes (401, 404) confirmed to reflect `X-Request-ID`.
  - AC-5: Multi-hop cascade test verifies 2 attempts recorded with respective latencies and error descriptions.
  - AC-6: Structured single-line JSON log emission verified for `backend.app.telemetry` logger.
  - AC-7: `GET /api/admin/telemetry/recent` and `/stats` return structured traces and metrics.
  - AC-8: `TelemetryStore` circular buffer bounds memory and evicts oldest traces.
  - AC-9: Telemetry store exceptions fail safely without breaking completions.
  - AC-10: Master-key authorization enforced for `/api/admin/telemetry/*`.
- **Evidence:** 37 passing unit/integration tests in `backend/tests/test_telemetry.py` and existing suites.
- **Acceptance:** Owner's chat message on 2026-10-22 confirmed the T-005 review fix and all reported defects resolved, then authorized preparation of the next specification. This accepts T-005; it does not approve implementation of T-006 or remote delivery.
- **Latest Regression Check:** On clean HEAD `6d49e2a174a111dc0a5bb8745530a97d0e9786da`, `.venv/bin/pytest backend/tests -q` returned 37 passed in 0.17s. No new external live probe was performed in this session.

---

## T-006 — Provider Validation Admin API
- **Status:** `done` — owner accepted the implementation in chat on 2026-10-22.
- **Why:** Enable operators and the React dashboard to validate new or existing provider credentials without restarting the service or manually inspecting logs.
- **Specification:** [specs/T-006-provider-validation-api.md](specs/T-006-provider-validation-api.md), version 1.0.1, owner-approved in chat on 2026-10-22.
- **Specification Review:** Owner supplied an approval-ready review on 2026-10-22, reporting no substantive gaps. Non-blocking profile, decision links and scripts-path comments addressed in v1.0.1; recommendation to approve is not recorded as implementation approval.
- **Input RECON:** [docs/recon/T-006-provider-validation.md](docs/recon/T-006-provider-validation.md).
- **Permission:** Owner authorized specification preparation in chat on 2026-10-22 following accepted T-005 fixes. Owner subsequently approved v1.0.1 and authorized implementation under PROJECT-PROCESS.md.
- **Deliverable and "Done When":** `POST /api/admin/providers/validate` accepts a provider manifest and optional test key, validates connectivity, parses available models, performs an in-band micro-completion test, and returns structured diagnostics.
- **Allowed Paths:** Exact approved implementation paths and protected contracts are listed in specification v1.0.1; pre-existing recon/specification and AGENTS scripts-path clarification are preserved. Candidate path audit is recorded in HANDOFF and the results note.
- **Dependencies:** T-003, T-005.
- **Result Evidence:** [notes/T-006-validation-results.md](notes/T-006-validation-results.md): final full suite 131 passed in 1.63s; real loopback success/429 and live OpenRouter validation passed. Read-only independent QA found a regex overflow defect, fixed and regression-tested; no remaining material findings. Runtime candidate hashes recorded in the results note.
- **Acceptance:** Owner accepted the completed T-006 result in chat on 2026-10-22 and authorized record synchronization and preparation of the next specification. No commit/push/deployment authorization was given.
- **Continuation:** T-007 was separately approved and implemented; its current operational checkpoint and remaining scope are recorded below.

---

## T-007 — Multi-Provider Discovery and Safe Cascade Activation
- **Status:** `active` — accepted operational checkpoint is implemented and integrated; remaining provider/provenance obligations stay open. No current implementation/probe is queued under this task.
- **Why / phase:** P2 / B-002; [VISION](VISION.md) key-only dynamic eligible inference without manual model-ID maintenance.
- **Approved contracts:** [v1.1.0 base](specs/T-007-multi-provider-discovery-and-cascade.md), [v1.2.0 correction](specs/T-007-dynamic-free-eligibility.md), [v1.2.1 amendment](specs/T-007-openrouter-price-evidence-amendment.md) and [v1.3.0 hybrid](specs/T-007-hybrid-account-eligibility.md), with their recorded precedence, owner-approved repairs and bounded live packets. These historical grants are not permission for unlimited new provider work.
- **Accepted result:** Strict OpenRouter source/enforcement; explicit nonbillable-account assertions and dynamic private buffered/SSE qualification; NVIDIA Free Endpoint exact intersection; shared cost/output guards; fair probe scheduling; no manual model lists. Account assurance remains user_asserted and cost reporting unavailable for the named direct providers.
- **Acceptance / latest owner request:** Owner accepted the NVIDIA repair and authorized primary Groq/NVIDIA/Mistral integration. After verified delivery, the owner acknowledged the working checkpoint and requested documentation synchronization and next-step planning. This accepts continuation from the operational checkpoint, not blanket closure of all T-007/P2 obligations or a new implementation packet.
- **Current environment:** Primary http://127.0.0.1:8001, current verified listener PID33541 after accepted [T-009 integration](notes/T-009-results.md); port8000 is unrelated oMLX. Local FREE_ACCOUNT_CONFIRMATIONS=["groq","nvidia_nim","mistral"], shipped default/example[], HF unconfirmed; strict OpenRouter unchanged. Only the authorized real.env confirmation entry changed; keys/other entries/provider billing preserved. Main service and normal bounded qualification remain running.
- **Current verification:** [Persistent primary evidence](notes/T-007-primary-activation.md): six final buffered/SSE HTTP200/visible PASS, request cap32, one intended-provider telemetry attempt each, SSEoneDONE. Independent full412 tests/12.67s, protected7 T-006 files+main unchanged. Initialfour and finalsix ordinary checks are separate from automatic qualification. No new live inference/test run is implied by this documentation checkpoint.
- **History / recon:** [Full results](notes/T-007-results.md) retain source/privacy/fairness repairs, earlier OpenRouter334-test proof, safe captures/hashes and partial failures. [Provider recon](docs/recon/T-007-remaining-provider-eligibility.md) and [dated NVIDIA outcomes](notes/T-007-nvidia-free-chat-check.md) are dated evidence, not current model allowlists or account tariff proof.
- **Remaining scope:** HF positive delivery, Gemini live/profile gaps, additional gateway contracts and positive local/cloud execution provenance remain explicit; Cloudflare/Cerebras/GitHub skip policy remains. Individual inconclusive model checks do not require universal catalog coverage or justify weaker admission. Full T-007/P2 is not marked done.
- **Next checkpoint:** The accepted baseline subsequently fed T-009, now accepted and primary-integrated. [Next-step proposal](notes/next-steps-current-checkpoint.md) now places T-010 preparation before T-008, followed by the retained P2 exit and P3 dependencies. No new implementation or additional manual live packet is authorized.

---

## T-008 — Automated Provider Onboarding Agent Prototype
- **Status:** `todo`
- **Why:** Accelerate zero-cost provider expansion by taking arbitrary provider documentation text / endpoints and automatically synthesizing valid YAML manifests for `providers.yaml`.
- **Specification:** To be drafted in Phase P2.
- **Deliverable and "Done When":** Endpoint `POST /api/admin/providers/auto-discover` processes provider docs and emits a validated `ProviderManifest` ready for registry inclusion.
- **Allowed Paths:** `backend/app/core/onboarding/`, `backend/app/api/admin/`, `backend/tests/`
- **Dependencies:** T-003, T-006.

---

## T-009 — Adaptive Circuit Breaker and Credential Lockout (Accepted)
- **Status:** `done` — owner accepted T-009; primary integration explicitly authorized and verified on2026-10-23.
- **Why:** P2 exponential recovery for the accepted pool, preserving VISION free-only inference and transparent failover.
- **Specification / input:** [v1.0.0](specs/T-009-adaptive-circuit-breaker.md), [Input RECON](docs/recon/T-009-adaptive-resilience.md). The earlier baseline used fixed cooldown; the accepted primary now implements adaptive recovery.
- **Implemented deliverable:** Shared adaptive route state, conservative credential quota pause, inference401 lockout, atomic single recovery and independent upstream-health/delivery outcomes. Automatic auth/balance recovery and new APIs are excluded. Primary activation was outside R1–R3, then separately owner-authorized and completed.
- **Scope / gates:** Exact MAY EDIT, protected paths, BR/AC, ordered R1–R3 and maximum4-send strict-OpenRouter smoke are in the spec; implementation and the2-send packet are complete. The subsequent exact owner approval authorizes these implementation stages and that packet; primary integration was separately owner-authorized and completed.
- **Evidence:** [Results and AC matrix](notes/T-009-results.md): root493 tests/16.80s, independent81/4.32s after QA repairs; actual isolated strict-OpenRouter buffered/SSE PASS,2 sends total at32-token caps with observed zero cost. Protected8 unchanged. Subsequent owner-authorized primary restart and buffered/SSE checks PASS; confirmations and free policy unchanged.
- **Dependencies:** Accepted T-007 operational baseline; full T-007/P2 remain open. Owner selection is settled; owner result acceptance and primary integration are settled; two actual primary32-token buffered/SSE checks PASS.

## T-010 — Task-Specific Free Catalogs and Inference APIs
- **Status:** `active` — owner accepted the v1.0.0 partial implementation on2026-10-23 and authorized remaining-admission recon/amendment preparation. AC-18/full task remains open.
- **Route / value:** P2 / B-002; extends VISION's key-only dynamically eligible inference to embeddings, rerank, decisions and speech while preserving chat interoperability.
- **Authority:** Owner's chat on 2026-10-23 explicitly selects this as the nearest route item and requests a separate specification under PROJECT-PROCESS.md. No implementation, new inference packet, restart, commit/push or deployment is implied.
- **Deliverables:** [Input RECON](docs/recon/T-010-task-specific-inference.md), [approval candidate](specs/T-010-task-specific-inference.md); task-separated catalog and dispatch contracts, endpoint-specific dynamic free assurance, bounded verification and preserved chat regression gates.
- **Scope for preparation:** Affected English Markdown records and public read-only source/code reconnaissance; independent proposal/source verification; local baseline tests. No real keys or inference needed.
- **Dependencies:** Accepted T-007/T-009 operational baseline, DEC-002/DEC-003/DEC-005. Existing T-007 and T-008 obligations remain open; T-010 does not waive P2 exit.
- **Approved scope:** v1.0.0, stages N1–N4. OpenRouter-first; exact task targets; strict evidence gaps remain unknown. Rerank/speech external admission is gated; four positive free live deliveries are required for full task closure.
- **Preparation baseline:** Existing suite493 passed/16.62s; initial sandbox loopback failures resolved by rerun with socket permission. No new provider inference.
- **Review:** Independent source and cumulative specification assessments clear after corrections; details in Input RECON.
- **Implementation authority:** Owner explicitly approved exact v1.0.0 and N1–N4 in chat on2026-10-23, retaining dynamic free admission and separate task catalogs. This covers only the bounded isolated packet; primary lifecycle/publication remain separate.
- **Result:** [Implementation, independent QA and delivery ledger](notes/T-010-results.md). Four actual isolated source checks returned UNVERIFIED with zero inference/consumed sends: embeddings/decisions price_scope_unknown, rerank/speech unsupported_enforcement. No positive external free delivery claimed.
- **Partial acceptance:** Owner explicitly accepted the verified partial implementation in chat on2026-10-23. No new implementation or primary activation is authorized by that acceptance.
- **Admission amendment:** [v1.1.0 candidate](specs/T-010-free-variant-admission.md), [measured recon](docs/recon/T-010-admission-amendment.md). Proposes exact published free-variant assurance, typed pricing, optional speech voice/default pcm, ordered A1–A3 and isolated maximum8 sends (2/task); source guarantee is distinct from complete numeric caps and live delivery. Independent cumulative/source reviews completed with clarifications; implementation approval pending.
- **Next step:** Owner review of exact v1.1.0/A1–A3 and proposed finite packet. Current v1.0.0 gates remain effective; no new inference/primary activation is queued.

### Current continuation

T-010 remaining-admission recon/amendment is nearest, before T-008. Preserve accepted T-009 primary integration and all free-access gates. Implementation of T-010 v1.0.0/N1–N4 is now owner-authorized. Existing T-007/P2 gaps remain open; P3/P4/P5 dependencies are unchanged. No provider activation, additional inference/restart, commit/push or external deployment is queued.
