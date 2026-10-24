# T-010 implementation and verification ledger

Date: 2026-10-23. P2/B-002. [Approved v1.0.0](../specs/T-010-task-specific-inference.md), [Input RECON](../docs/recon/T-010-task-specific-inference.md).

## Authority and ownership

Owner approved exact v1.0.0 and N1–N4 with the stated admission limits in chat on2026-10-23, authorizing implementation under PROJECT-PROCESS.md. Root owns integration/records; task_protocol wrote only tasks/protocol.py and test_task_protocol.py; task_catalog wrote only tasks/catalog.py and test_task_catalog.py, then separately test_task_discovery.py. Their assigned paths and starting dirty status were saved before dispatch. Independent cumulative QA has no write permission. CLI preparation has a separately bounded scripts/probe_task_inference.py/test_task_probe.py assignment. No unrelated working files may be reverted.

Start: main78a1aa4790293781aafe81e786ee4e3b7f098ef2 plus accepted uncommitted work, `/tmp/t010-implementation-start-status.txt`; byte inventory `/tmp/t010-before-all.json`. No clean release revision or commit is claimed. Primary remains the earlier accepted running process; no T-010 activation/restart is authorized by this implementation approval.

## Ordered implementation gates

| Stage | Actual outcome | Evidence / limits |
|---|---|---|
| N1 | Additive task snapshots/evidence, exact binding, public task query, privileged diagnostics and bounded owned discovery | First full run595 passed/1 failed because a non-owned test source inadvertently launched task jobs; rejecting source overrides fixed the cause without changing existing tests. Full596 passed/32.54s in `/tmp/t010-n1-pytest.txt`; separate API/catalog22 passed/0.19s |
| N2 | Exact task transport, shared credential financial umbrella/auth/quota and task-local service state | Full626 passed/32.73s, `/tmp/t010-n2-pytest.txt`; targeted transport10 passed/0.14s. A fixture initially changed only a normalized trailing slash; corrected it to a genuinely changed endpoint to exercise epoch fencing |
| N3 | Typed decision protocol and fully buffered bounded mp3/pcm protocol, lifecycle/socket delivery | Full631 passed/33.07s, `/tmp/t010-n3-pytest.txt`; real-loopback four-protocol fixture plus invalid-audio checks5 passed/0.55s |
| N4 | Complete within admitted scope: independent cumulative review, finite CLI, actual isolated source checks and final reconciliation | Final full658 passed/36.82s; independent44 passed/0.64s before final conservative source/test additions; four tasks UNVERIFIED/zero inference |

Rerank/speech success paths use an explicitly test-only fictional verified-profile executor inside the loopback test. Production admission remains strict unknown; no request/config flag can enable the fixture. These checks prove protocol/socket delivery, not provider pricing or external free supply. Embedding/decisions production-profile tests use synthetic complete zero prices; current external catalog prices must be checked independently.

## Preserved policies and effective gates

- Default `/v1/models` and `auto:free` remain chat-only. New task public IDs are `openrouter::<raw-id>` in explicit task lists; list reads are memory-only.
- Embeddings/decisions require exact task capability and explicit zero prompt/completion/request prices with no additional unverified price keys; owned zero routing ceilings remain mandatory. No omitted-request exception transfers from chat.
- Rerank/speech remain unknown/unsupported_enforcement under v1.0.0. No external inference is permitted for those profiles. Dimensions/formats are not invented from unavailable metadata.
- No direct-provider account assertion or private chat lease authorizes task inference. No task automatic qualification or new account confirmation is added.
- Financial incidents protect all OpenRouter task/chat scopes sharing the same resolved key within the retained registry; source/epoch/pruning cannot clear the account umbrella. New credentials have independent state; restoring the old credential retains its latch. Auth/quota reuse accepted controllers; service failures remain task-route local. Independent registries remain isolated.
- All nonchat monetary reporting is unavailable pending a sourced payer/currency mapping. Recognized chat cost incidents propagate to tasks. Complete valid answers survive concurrent shared incidents; no started output is replayed/spliced.
- No primary environment/configuration/service change, package dependency, persistent runtime store, commit/push or external deployment.

## Independent findings and fixes

Independent QA identified and verified fixes for three privacy/epoch issues: a configured secret equal to the final prefixed public model ID could leak through catalogs; a key rotated while awaiting I/O could appear in masked model/correlation/event fields; observing a changed credential through a rejected task request had to invalidate the old proof even after key restoration. Final namespace/current-key checks and consumer-entry epoch maintenance now cover these cases. Source/route secrets are not logged. Explicit disconnect ownership cancels and joins the request/observer and closes upstream I/O.

The reviewer reported no remaining material blocker and independently ran44 focused catalog/transport/probe tests in0.64s, with bytecode/cache writes disabled. Root's full suite then passed646/33.68s. Root added stronger real audio socket fault/disconnect coverage and conservative incomplete-page/diagnostic-TTL checks: first socket extension run had5 teardown failures caused by reusing a fixture keepalive pool across different event loops, corrected by disabling fixture keepalive; final socket13 passed/3.88s and catalog25 passed/0.14s. Final complete suite **658 passed in36.82s**, `/tmp/t010-final-pytest.txt`. These are local regression/protocol checks, not external free delivery.

## Actual isolated source/packet outcomes

Each authorized max-sends1 task command ran once through the isolated complete application/lifespan. All returned exit2/UNVERIFIED before any inference. Ledger remains spent0 for all tasks; actual and consumed sends are both0. The tool's transport guard allowed owned catalog GETs and blocked unrelated inference; direct-provider confirmations were runtime-empty in the isolated registry only. No primary environment was changed. Final max-sends0 source preflights repeated the same exclusions against final bytes after conservative source handling changes; these do not reserve/increase the inference packet.

| Task | Dated catalog rows observed | Final reason | Actual/consumed inference | Positive live delivery |
|---|---:|---|---|---|
| embeddings | 35 | price_scope_unknown | 0/0 | UNVERIFIED |
| rerank | 10 | unsupported_enforcement | 0/0 | UNVERIFIED |
| decisions | 30 | price_scope_unknown | 0/0 | UNVERIFIED |
| speech | 36 | unsupported_enforcement | 0/0 | UNVERIFIED |

These are visible inventory counts, not free/working model counts or model-ID allowlists. Reports contain no prompts/vectors/audio/raw keys. Private0600 files `/tmp/t010-{TASK}.json` retain the initial packet, `/tmp/t010-final-{TASK}.json` final data-only preflights, and `/tmp/t010-live-budget.json` durable allowance. Candidate hashes in the final reports match the current application/CLI bytes. Source tariff completeness is not inferred from the presence of a key or a successful catalog GET.

Read-only primary checks returned HTTP200 for `/health` and `/openapi.json`; none of the four T-010 POST routes is loaded there. No buffered/SSE/main-provider inference or restart was performed. Accepted T-009 remains the primary integration checkpoint. T-010 primary loading requires a separate owner integration decision and target checks.

## AC reconciliation

| AC | Status and evidence |
|---|---|
| AC-1 | PASS:658 full tests; all24 pre-existing test files and protected source paths byte-unchanged; scope audit below |
| AC-2 | PASS: catalog/API/real-lifespan tests preserve default chat and isolate same raw IDs/tasks |
| AC-3 | PASS: catalog/discovery tests cover expiry, source failures, duplicates, pagination/overflow, key changes, stale publication and pure reads |
| AC-4 | PASS locally: source/policy tests cover explicit/missing/extra/invalid prices and captured zero ceilings; no external positive pricing claim |
| AC-5 | PASS: production rerank/speech stay unknown, public lists empty and actual isolated inference0 |
| AC-6 | PASS: auth-first/closed JSON/duplicate/NaN/oversized/control-field API/protocol tests; input content stays inert |
| AC-7 | PASS: vector count/index/dimension/finite/model fixtures and actual embedding socket delivery; exact target, no batch split |
| AC-8 | PASS locally: rerank typed index/score validation and fictional-profile socket fixture; external profile still blocked |
| AC-9 | PASS: typed primitive/label/distribution/model protocol tests and actual local Decisions socket |
| AC-10 | PASS locally: real MP3/PCM, wrong MIME/JSON/empty/oversize/truncated audio and client cancellation/disconnect; no partial/replayed audio |
| AC-11 | PASS: shared task/chat financial/auth/quota tests, pruning/key restoration and route-specific service isolation; existing T-009 atomic recovery suite retained |
| AC-12 | PASS: pre-send source/hold race, epoch restoration, cancellation ownership and real disconnected-client closure; shared accepted I/O/controller race tests retained |
| AC-13 | PASS: concurrent valid complete output/shared incident delivery, monetary unavailable, no field-name inference and future sibling blocking |
| AC-14 | PASS: full public-ID/current-key/correlation/voice privacy sentinels; bounded events and unchanged existing chat telemetry schema/tests |
| AC-15 | PASS: actual complete local lifespan and semaphore/fairness/shutdown tests, slow/failure source isolation |
| AC-16 | PASS: actual help/no-credentials CLI plus denied fixture and four actual source commands; bounded/redacted exits and zero blocked inference |
| AC-17 | PASS: independent cumulative code/CLI review after root fixes; final conservative additions and evidence rechecked separately |
| AC-18 | OPEN/UNVERIFIED for all four tasks: source policy denies inference; no positive external free delivery and no full T-010/P2 closure |

## Scope, identity and continuation

No BR/AC/stack/free-assurance deviation was needed. Conservative task source binding rejects non-owned injected source overrides; this preserves accepted fixture/custom chat behavior rather than inheriting its certification. Catalog pagination/TTL hardening narrows incomplete evidence only. A real TaskExecutor for blocked profiles exists, but has no public production admission bypass; test fixture subclasses are confined to tests.

`/tmp/t010-scope-audit.json` compares saved starting bytes; `/tmp/t010-final-runtime.json` binds all backend/test/tool/config bytes, including new files. Protected main/T-006/chat-policy/adapter/account-probe/NVIDIA/manifest paths are unchanged. Only approved integration modules, new task modules/tests/CLI and affected English records changed; no out-of-scope delegated writes were reported or observed. Existing dirty work was preserved. No remote commit/push/history or primary change.

The deliverable is a verified partial implementation ready for owner disposition. Full task delivery needs sourced, separately approved profile amendments resolving absent/extra fee evidence and rerank/speech enforcement, followed by genuinely admissible bounded delivery. Do not clear AC-18 from an empty pool, successful fixture or the owner's implementation approval. Primary activation and acceptance of a partial result are distinct decisions; T-008 and existing T-007/P2 obligations remain.

Final candidate identity:81 files, manifest SHA-256 `4272eedada000b8e8e2f0c35ac7ae0739ff70b9bdc2a6ec13df8e51d80af98c6`. All24 old test files and all protected paths match saved starting bytes; final report app/CLI hashes match current bytes. Final scope audit found no violations. No production source changed after the final658-test run/source preflights.

Final independent recheck confirmed the refreshed81-file manifest/current bytes, all protected24 existing test files, report hashes and scope audit without findings. Affected local links/paired markers and12 README shell blocks passed offline checks. This remains specification-scoped partial acceptance material; no independent full-suite execution or positive external delivery is claimed.

## Owner acceptance of partial result (2026-10-23)

The owner explicitly accepted the partial implementation and authorized read-only reconnaissance plus a T-010 amendment to enable all four tasks while preserving dynamic free determination and no manual lists. This accepts the verified v1.0.0 source result; it does not close AC-18 or authorize implementation of an unapproved amendment, more generation, primary activation, commit/push or deployment. The next preparation record is docs/recon/T-010-admission-amendment.md.

## Admission amendment prepared (2026-10-23)

[Remaining-admission RECON](../docs/recon/T-010-admission-amendment.md) and [v1.1.0 candidate](../specs/T-010-free-variant-admission.md) propose published free-variant assurance, typed prices, optional speech voice/default pcm and ordered A1–A3 with a finite isolated8-send maximum (2/task). Independent source/cumulative review found and resolved admission/format ambiguities; voice source tension remains explicitly bounded for approval. Public catalog reads only, no keys or inference. The81-file runtime remains unchanged; original ledger and every UNVERIFIED live outcome remain. Implementation, new packet and primary activation are not yet authorized.

## Local source checkpoint (2026-10-24)

Owner authorized committing all accumulated changes. Runtime/tests/tools are saved in `d160000`; task admission/runtime bytes remain identical to the accepted81-file manifest. Fresh full backend regression658 passed/36.72s after granting loopback socket permission; the initial restricted37 socket failures/621 passes were environmental, resolved without code changes. Output `/tmp/off-precommit-pytest.txt`. Current documentation includes pending v1.1.0 as a proposal only. No new provider inference, ledger reset, primary restart or push occurred.
