# T-009 implementation evidence

Current disposition: owner-accepted and primary-integrated; see the final dated integration section. Earlier sections retain their historical authorization boundaries.

Date: 2026-10-23. P2 / B-002. Owner approved [v1.0.0](../specs/T-009-adaptive-circuit-breaker.md), R1–R3 and its maximum4-send isolated strict-OpenRouter live packet. Primary integration/restart is excluded.

## Baseline and scope

main HEAD6d49e2a174a111dc0a5bb8745530a97d0e9786da plus preserved existing accepted dirty tree. Starting status `/tmp/t009-implementation-start-status.txt`; recon58-file manifest retains protected baseline hashes. Fresh preparation baseline412 passed/12.47s. No commit/push or `.env` change.

## R1 progress

Shared controller, safe retry metadata and strict base validation implemented. Initial focused run found an eager package import cycle; corrected through lazy adapter imports without changing protected package entrypoints. Focused22 tests PASS. Initial sandbox-wide run could not bind temporary sockets (20 environment failures); rerun with local-socket permission passed434 tests/12.61s. R1 gate passed.

## R2 progress

Shared admission now gates every consumer attempt; API distinguishes known health-blocked503 from unknown404 without changing public schemas. Health finalization is separate from delivery traces and owns cleanup. Existing same-credential429 failover fixtures were migrated to503 because approved429 policy now skips sibling routes; real socket tests prove cross-credential429 failover. Private cooldown mutation fixtures use explicit fresh controller isolation; protected T-006 read-only snapshot remains.

Initial full regression451 passed/16.18s. Additional late-cost/finish-cancel/socket no-replay cases:18 focused tests passed/4.18s. Final full R2 gate457 passed/16.65s. R2 passed before R3 began.

## Live budget

Completed packet: **2 actual inference sends**, one buffered and one SSE, from a maximum4-send grant. At most4 across one buffered and one SSE request, each max32 tokens and at most2 attempts, strict OpenRouter only, isolated settings with account confirmations empty. No primary restart.

## R3 and independent QA repairs

Shared private auth/quota admission, permit rollback and typed origin sidechannel are implemented without editing protected protocol/evidence/billing policy. Qualification in-band401 now reaches existing suspension and shared auth lockout. Initial R3 full462 passed/16.48s.

Independent QA found three root causes, all repaired with regressions: error-body loss could erase an already received HTTP failure/retry bound; uncoded HTTP200 error envelopes were treated as actual502; real terminal-tail transport failure preserved the answer without protecting future requests. Error headers now survive bounded body read failure, synthetic protocol outcomes retain actual200 origin, and terminal-tail transport/timeout records health separately while delivering DONE. Added finite scope-kind/reason diagnostics and budget-admission rollback without extending an unsent recovery.

Latest root full regression493 passed/16.80s (`/tmp/t009-final-tests.txt`). Independent final cumulative review is clear after repairs:81 tests passed/4.32s, protected8 and approved scope verified, no residual substantive defects. The verifier confirmed root493/16.80s; it did not independently pass the whole493-test suite. Its sandbox-wide run had465 passes/28 socket permission failures; automatic approval review rejected its elevated full rerun because of live/provider-validation files. The permitted focused81-test loopback run completed instead. No rejection was bypassed.

## Isolated actual live delivery

Command: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/probe_multi_provider.py --mode proxy --provider-id openrouter --generation both --max-attempts 2`. Capture `/tmp/t009-live.json`; stderr `/tmp/t009-live.stderr`. Process exited0 and its ephemeral backend/worker stopped. Existing tooling created a strict-OpenRouter-only registry with account confirmations[]; the real primary/environment were not edited or restarted.

| Mode | HTTP / protocol / visible output | Actual sends | Request max_tokens | Monetary reporting | Delivery |
|---|---|---|---|---|---|
| Buffered | 200 / valid / yes | 1 | 32 | zero | PASS;30 reported completion tokens, length finish |
| SSE | 200 / valid / yes | 1 | 32 | zero | PASS; exactly one DONE |

Total2 of at most4 authorized inference sends; no repeat packet, forced failures, account qualification, paid fallback or disabled free gates. Observer verified owned zero-price routing ceilings, current dynamic eligibility and wire/telemetry count agreement. Live catalog snapshot468 entries,18 admitted; dated observation, not a future free-access promise. Both attempts used strict source/enforcement assurance. Total checker duration3060.21ms. Only safe metadata retained; prompts/answers/keys are not copied here. Costzero is observed here rather than synthesized for unavailable reporting.

Live capture SHA-256: `3233d853681de39439df08c40669e97c43172afa292d7b3d9141dde684012cbc`. Source manifest `/tmp/t009-final-runtime.json` covers62 files; SHA-256 `71fd82b716668224b0bb7686e72644af9a5d0f0e35cee18c3d74be0fd5947881`. Seven T-006 files and main.py match the recon baseline. Actual upstream401/429 were not induced; protection branches are proved by counted real loopback fixtures and concurrency tests.

## Acceptance matrix

| AC | Result and evidence |
|---|---|
| 1 | PASS:493 full regressions; protected8 unchanged, helper/constructor compatibility retained |
| 2–3 | PASS:fake-clock sequences, strict settings, long/invalid/date/deferred retry hints in test_resilience.py |
| 4 | PASS:HTTP headers survive broken bodies; actual/effective/synthetic origin and billing precedence tested |
| 5–7 | PASS:stale/duplicate generations, one recovery owner, cleanup cancellation, auth identity/source epoch/key restore, capacity fail-closed |
| 8–10 | PASS:cross-credential quota/auth, private/consumer recovery race, no extra budget or partial lease, source401 exclusion |
| 11 | PASS:existing source/assertion/epoch/permit/lease/billing race regressions plus skipped-send tests |
| 12–13 | PASS:late terminal cost/cancel/transport cases; actual local TCP buffered/SSE failover/no-replay with counted requests |
| 14–15 | PASS:known blocked503 vs unknown404 and zero attempts, protected listing/auth/request/privacy regressions; internal finite state/reason/scope-kind diagnostics |
| 16 | PASS:independent local cumulative review after repairs plus actual strict-OpenRouter buffered/SSE smoke within2 sends; source candidate ready for owner acceptance |

## Environment disposition

T-009 is implemented and verified in the source candidate and isolated smoke environment; it is not integrated into the running primary. No breaker bypass switch is added. Cooldown base default remains60; new validation requires integer1..300 in new processes only. The earlier primary retains T-007 code and local FREE_ACCOUNT_CONFIRMATIONS=[groq,nvidia_nim,mistral] under prior acceptance. Isolated smoke used[]; shipped default/example[]; HF remains unconfirmed. No free/provider gate was enabled on any environment by this task. T-007/P2 remain open, and primary restart plus target buffered/SSE verification requires a separate owner integration grant. No commit/push or external deployment.

Final read-only evidence audit independently confirmed the live capture, both recorded SHA-256 digests,62 unchanged current manifest hashes, protected8,71 local links, balanced markers and clean whitespace. No reviewer writes or additional inference occurred.

## Accepted primary integration — 2026-10-23

The owner accepted T-009 and explicitly authorized restarting the primary and one buffered/SSE32-token check. Verified old listener PID3119, port8001, uvicorn command and project cwd before graceful SIGTERM. Launched the same ordinary command from the same cwd as PID33541, preserving environment/key files and confirmations[groq,nvidia_nim,mistral]; default base60 and max attempts3. Port8000 was untouched. Fresh source still matches the62-file accepted manifest. Primary HTTP health and post-check listener pass.

The actual primary `/v1/models` supplied a dynamically eligible Groq-only canonical route, without a model admission list. Both requests went to127.0.0.1:8001 and their unique correlations matched real primary admin telemetry.

| Mode | Result | Request cap / observed completion tokens | Actual telemetry attempts |
|---|---|---|---|
| Buffered | HTTP200, valid visible response PASS | 32 / 10 | 1, Groq success |
| SSE | HTTP200, valid visible response PASS, one DONE | 32 / 10 | 1, Groq success |

Two ordinary verification requests, two actual consumer upstream attempts, no repeat packet. The already authorized normal background qualification worker separately continues within its fixed budgets; two is not a total inference count including worker activity. Account assurance remains user_asserted, effective monetary reporting unavailable, never zero. Strict OpenRouter, current source/assertion/epoch/leases, BillingGuard and no-replay rules remain active. No keys, `.env`, provider manifest or eligibility policy changed. No new provider opt-in. No commit/push or external deployment.

T-009 is owner-accepted and integrated on the primary with actual target verification. Earlier candidate/pending-integration paragraphs above describe the historical checkpoint and are superseded by this dated section. T-007/P2 remain open. Checker exited; primary/worker remain running. PID file `/tmp/open-freebie-finder-main.pid`, log `/tmp/open-freebie-finder-main.log`. Safe restart/check captures are supplementary; hashes below bind their summaries.

- `/tmp/t009-primary-restart.json` SHA-256: `b718c9f8b7a76306f01660f1197486fffbfa1af7836b9b539ad1816b6383d255`

- `/tmp/t009-primary-checks.json` SHA-256: `5d17c041fa9dabb9e471e111784a7309af634ad409e46d867cfb8cfca562e4d7`

- `/tmp/t009-primary-checks.jsonl` SHA-256: `515108d677b59b781458d99cd600fee45ff825b6db54fd8c81d13b971195a3c8`

Independent read-only integration audit confirmed the new listener33541, both target responses/telemetry, unchanged62 source hashes and protected8, all three capture digests and valid local links/markers. No reviewer writes, tests, API calls, inference or secret-file access. Current TASKS PID/continuation were synchronized to the completed integration.
