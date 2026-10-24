# T-007 Implementation and Verification Results

Date: 2026-10-22. Specification: [T-007 v1.1.0](../specs/T-007-multi-provider-discovery-and-cascade.md). Phase P2 / B-002. Status: approved-scope implementation independently reviewed; result acceptance pending. Subsequent owner clarification requires [dynamic-eligibility correction](../specs/T-007-dynamic-free-eligibility.md); the historical evidence below does not claim that new behavior.

## Authorization and candidate identity

The owner explicitly approved T-007 v1.1.0 and implementation under PROJECT-PROCESS.md, supplied Groq/NVIDIA credentials in local .env, and subsequently confirmed both are free access and authorized short live checks. No credentials were printed or persisted by this work. Gemini external generation remains owner-deferred/UNVERIFIED; P2 stays open. Cloudflare is unsupported_profile with zero requests, Cerebras excluded, GitHub Models retired. No commit, push or deployment performed.

Baseline: main, HEAD `6d49e2a174a111dc0a5bb8745530a97d0e9786da`, with accepted uncommitted T-006 and approved T-007 planning records already present. The pre-existing seventeen file paths were preserved. The candidate is the saved working tree identified by SHA-256 below; accepted T-006 implementation files remain unchanged. All T-007 runtime/test/tool writes are within its MAY EDIT. Affected project state/specification approval metadata is synchronized separately. No frontend, database, dependencies, telemetry schema/store or real .env changes.

## Delivered behavior

One startup/periodic orchestrator handles configured manifests, with four concurrent provider slots, no overlapping cycles, a 15-second provider deadline and a 4 MiB decoded catalog limit. Complete valid snapshots replace only the affected provider; empty valid lists clear it, failures retain it until expiry. Eligibility expires after twice the discovery interval and rechecks credentials, enabled state, policy and allowlist in memory before listing and each dispatch. Unsupported/excluded/retired profiles cannot bypass skips through manual lists or keys. Invalid individual manifest/credential state cannot stop healthy providers.

Catalog discovery is separate from free chat admission. Cloud defaults require explicit free_access_confirmed and an exact chat_model_allowlist. Built-in local_ollama with auth none and built-in OpenRouter using openrouter_free are the specific exemptions. Unknown raw identities stay provider-qualified; aliases assert exact identity without creating availability. Tier 1 same-model routing precedes alternatives, with provider diversity within tiers and a configurable 1..10 attempt cap (default three). Budget stops differ from exhaustion.

Buffered and SSE failures use safe diagnostics. First-content buffering supports failover after role-only chunks; after content starts it never restarts. Stream ownership closes upstream responses on cancellation, early close and downstream ASGI disconnect, including before the first body read. HTTP client proxy/redirect use is disabled. Reflected credentials and prompt/upstream bodies do not enter ordinary errors/logs/telemetry.

BR-1 fixture exception: synthetic cloud fixtures in test_telemetry.py now explicitly declare free confirmation and allowlists. Every existing telemetry scenario/assertion remains; no baseline scenario was removed or relaxed. This reflects the new admission contract rather than an auth-none cloud bypass.

## Independent QA and fixes

A separate read-only reviewer inspected the cumulative candidate and reported no remaining material findings after fixes. Findings resolved in scope included cloud auth-none/openrouter admission bypasses, isolation of malformed credentials/manifests, current-policy rechecks during pending failover, case-sensitive identity collisions, and ownership of buffered upstream SSE resources on early close/cancellation/ASGI send failure. Regressions cover those cases. A numeric environment-setting conversion defect found during implementation was fixed at env/dotenv sources while retaining strict direct-constructor bounds. Unresolved templates are rejected in both base and catalog URLs before I/O. The reviewer wrote no files. Final independent evidence verification passed: all ten catalog captures and both proxy captures match this report, all nineteen T-007 and seven protected T-006 SHA-256 values match, local links resolve and specification markers balance. The current thirty-seven changed paths match the saved status; the original seventeen paths remain preserved and no new scope violation was found. The verifier confirmed the reported test/timing figures, effective gate states and named UNVERIFIED limitations; no material discrepancies. It wrote no files, reran no tests/external calls and did not read .env or secrets.

## Automated and real-socket evidence

Command: `.venv/bin/pytest backend/tests -q`, exit 0. Final capture:

```text
........................................................................ [ 36%]
........................................................................ [ 72%]
......................................................                   [100%]
198 passed in 4.14s
```

Run with tool-approved execution outside the sandbox because actual loopback socket binding is required. Existing T-006 real-socket regressions and new T-007 real application/upstream servers ran. The latter starts normal application lifespan discovery, populates snapshots from two real HTTP upstreams, injects a controlled first-provider 429, verifies buffered/SSE success at the second provider, and checks listing/health during slow polling plus shutdown cleanup. These are controlled local failures, not natural external quota exhaustion.

AC-12 command: `.venv/bin/pytest backend/tests/test_multi_provider_routing.py::test_model_listing_memory_only_and_timings -q -s`, exit 0:

```text
{"listing_samples": 30, "fixture_models": 3, "median_ms": 0.192, "p95_ms": 0.273}
.
1 passed in 0.02s
```

Environment: local development Python 3.15.0 on Darwin, warmed ASGI application, three fixture models, thirty listing samples. HTTP and filesystem reads are instrumented to fail during listing and admission revocation. Timing is informational and does not replace zero-I/O assertions or establish a production latency guarantee.

## Final external probes

Every catalog row uses `.venv/bin/python scripts/probe_multi_provider.py --provider-id ID --mode catalog`. Required successes and policy skips exit 0; missing prerequisites and local invalid_catalog exit 1. Captures below are actual final sanitized stdout, with no generated content, key values or raw model IDs. Required catalog probes run against real external endpoints; proxy probes use the real local server, normal lifespan discovery, adapter and external provider, with actual router telemetry checking provider identity, correlation ID and success.

Catalog `openrouter`:

```json
{"outcome": "succeeded", "code": null, "catalog_count": 468, "admitted_count": 20, "duration_ms": 1615.88, "free_access_confirmed": false, "allowlist_count": 0}
```

Catalog `groq`:

```json
{"outcome": "succeeded", "code": null, "catalog_count": 11, "admitted_count": 0, "duration_ms": 327.48, "free_access_confirmed": false, "allowlist_count": 0}
```

Catalog `nvidia_nim`:

```json
{"outcome": "succeeded", "code": null, "catalog_count": 83, "admitted_count": 0, "duration_ms": 735.45, "free_access_confirmed": false, "allowlist_count": 0}
```

Catalog `google_gemini`:

```json
{"outcome": "UNVERIFIED", "code": "missing_credentials"}
```

Catalog `mistral`:

```json
{"outcome": "UNVERIFIED", "code": "missing_credentials"}
```

Catalog `huggingface`:

```json
{"outcome": "UNVERIFIED", "code": "missing_credentials"}
```

Catalog `local_ollama`:

```json
{"outcome": "failed", "code": "invalid_catalog", "catalog_count": 0, "admitted_count": 0, "duration_ms": 32.65, "free_access_confirmed": false, "allowlist_count": 0}
```

Catalog `cloudflare`:

```json
{"outcome": "SKIPPED", "code": "unsupported_profile"}
```

Catalog `cerebras`:

```json
{"outcome": "SKIPPED", "code": "excluded"}
```

Catalog `github_models`:

```json
{"outcome": "SKIPPED", "code": "retired"}
```

Local Ollama is reachable, but its OpenAI endpoint returned HTTP 200 with object=list and data=null; /api/tags confirmed an empty models list (zero installed models). The list-contract parser correctly rejects null as invalid_catalog. Local inference is UNVERIFIED until a model is installed; no download or alternate schema was silently introduced. This is not a successful live local-profile delivery. All supported-profile fixture tests still pass.

Proxy `groq` command: `.venv/bin/python scripts/probe_multi_provider.py --provider-id groq --mode proxy --confirm-free-access --model-id openai/gpt-oss-20b`, exit 0:

```json
{"outcome": "passed", "catalog_count": 11, "admitted_count": 1, "results": [{"stream": false, "http_status": 200, "passed": true}, {"stream": true, "http_status": 200, "passed": true}], "duration_ms": 1566.93, "free_access_confirmed": true, "allowlist_count": 1}
```

Proxy `nvidia_nim` command: `.venv/bin/python scripts/probe_multi_provider.py --provider-id nvidia_nim --mode proxy --confirm-free-access --model-id openai/gpt-oss-20b`, exit 0:

```json
{"outcome": "passed", "catalog_count": 83, "admitted_count": 1, "results": [{"stream": false, "http_status": 200, "passed": true}, {"stream": true, "http_status": 200, "passed": true}], "duration_ms": 3103.34, "free_access_confirmed": true, "allowlist_count": 1}
```

## Effective gates and limitations

| Environment/profile | Effective admission state | Release condition |
|---|---|---|
| Ordinary local application: Groq, NVIDIA, Gemini, Mistral, Hugging Face | free_access_confirmed=false, chat_model_allowlist=[]; keys allow discovery only | Operator explicitly confirms current free entitlement and configures exact chat IDs in the manifest; restart to reload manifest |
| Isolated Groq/NVIDIA proxy probes | free_access_confirmed=true, one allowlisted model, only selected provider loaded | Owner's free-access confirmation and explicit CLI flags; state ends with probe process |
| Ordinary/probe OpenRouter | flag=false, allowlist empty; openrouter_free admits only zero-price models | Preserve verified free-pricing rule and configured credential |
| Ordinary/probe local_ollama | flag=false, allowlist empty; local auth-none exemption, no installed models here | Install a local model and verify live delivery separately |
| Cloudflare / Cerebras / GitHub Models | Disabled in bundled manifest; unconditional unsupported/excluded/retired skip even if enabled | Separate approved scope and prerequisites; keys alone never release these skips |

No remote environment was deployed or changed. Probe-owned servers stopped. Gemini live generation is explicitly owner-deferred/UNVERIFIED until its key is available; Groq/NVIDIA exceptions are not needed because both passed. Mistral/Hugging Face catalog and inference remain UNVERIFIED without credentials. No natural upstream 429 was induced; real controlled loopback failover is the relevant evidence. Fixed cooldown remains; adaptive backoff/recovery is separate proposed T-009. T-008 and P3 onward were not implemented. P2 remains active.

## Acceptance trace

| Criterion | Evidence / disposition |
|---|---|
| AC-1 | Full regression suite above; preserved accepted T-006 and baseline scenarios; path/hash audit |
| AC-2 | All viable bundled profiles plus custom manifest, startup/periodic refresh, concurrency/no overlap, skip/preflight tests |
| AC-3 | Snapshot replacement/empty/failure/staleness, resource limits, cancellation, worker cleanup tests |
| AC-4 | Literal OpenAI mappings, filter/context/dedup and partial-catalog tests; hard no-request profile skips |
| AC-5 | Admission/revocation/secret-reflection tests, including credential and policy changes between attempts |
| AC-6 | Exact aliases/raw/ambiguous/case-sensitive identities and negative version/quantization tests; JSON/SSE masking |
| AC-7 | Provider diversity, explicit priority, 1/3/10 bounds, honest budget/exhaustion tests |
| AC-8 | Buffered/SSE initiation failures, invalid JSON, correlation/privacy and downstream-disconnect cleanup tests |
| AC-9 | Real ephemeral app plus two upstreams: controlled 429, buffered/SSE failover, health/listing concurrency and cleanup |
| AC-10 | OpenRouter/Groq/NVIDIA final real catalogs succeeded; conditional and skipped outcomes explicitly recorded above |
| AC-11 | Groq/NVIDIA buffered and SSE through real local proxy passed; Gemini owner-deferred/UNVERIFIED |
| AC-12 | Instrumented zero HTTP/filesystem reads and revocation plus measured listing timings above |

## Candidate SHA-256

Hashes cover delivered runtime/config/test/tool bytes after the final test and live captures; project records are excluded to avoid circular hashes.

| Path | SHA-256 |
|---|---|
| `backend/app/core/discovery/orchestrator.py` | `b5dfa2c2d4903be6240e78beb7b64f1f1e0a2796cef34a29fdda84355d87b31f` |
| `backend/app/core/discovery/privacy.py` | `5e500ea6a8223d3af6da53a91aa1a2226875f0c3725b4f5e22c87a4b588a3277` |
| `backend/app/core/discovery/openrouter.py` | `9e177d44792f337b47428e0bbf06d3bf347f4b7316e5e00959d446227b9316aa` |
| `backend/app/core/providers/models.py` | `69bfc41efa212386e350570f805a0b6d13b45112b7fcdc7e96778dc4e617efaa` |
| `backend/app/core/providers/registry.py` | `362f945069c82b84c6b2e7eb45e2680c5423c64377b57f89f7c2822a32c5d504` |
| `backend/app/core/providers/providers.yaml` | `7b71bcd537b03ee8782ac28a19b62af66283c9673390e4af28d62abd552091f2` |
| `backend/app/core/providers/model_aliases.yaml` | `0b74c70da8b2d8f39016a7b6fa1032fe3d614b0e4cee3b67db6c8e04fef57a86` |
| `backend/app/core/adapters/openai_client.py` | `740996fd0596ca481e54880ec809bff4c59ffc2b54b7d2cdedc9e41f56930a05` |
| `backend/app/core/balancer/router.py` | `9b9e9f6aef2a50c298f508415657b5fc408ffce9f2d65e30a459bd4edf271bcf` |
| `backend/app/main.py` | `b4d33364d01a4128d15b635c5f004d1a5e1f4b097c64bc372bde43e87768d039` |
| `backend/app/config.py` | `22353bc890bc93576d87ddb8e0327d45c24a1ec3ea33677a20314c52dd809428` |
| `backend/app/api/v1/models.py` | `a354278e64b541da7c70caf971b2a32c5a5a47ce6b497835e30b214526e456c8` |
| `backend/app/api/v1/chat.py` | `311c7820ae318b3284c289a4772cb4f3bb96cbdb391037f3e13c1f7354b066f9` |
| `.env.example` | `1feeba3a17af59a75f11d1aad9f388277566f0216007d733211703d1655db263` |
| `backend/tests/test_multi_provider_discovery.py` | `34ec49820d12f07760c626c2212abdd0a47eb366e4747b558279d1a7c0431ca4` |
| `backend/tests/test_multi_provider_routing.py` | `400dff2dd5c478d7af2fbb383b51f0f60c58fef9034e159919fca6f4a58c91fe` |
| `backend/tests/test_multi_provider_live.py` | `4ee8cda6632546809968edc3fa7a24741611400d3817d72cb9158ba8909d1bd3` |
| `backend/tests/test_telemetry.py` | `817aaff6f0b760a40ecab08017237088e58a9207159cc70f102fef59dc449b34` |
| `scripts/probe_multi_provider.py` | `53314b75f953ab0ad6adfa1bb484d68ecde5d875d25781a85b5141747879bddd` |

## Owner-authorized generation configuration follow-up (2026-10-22)

After the delivery report, the owner explicitly instructed the agent to apply the previously described Groq/NVIDIA generation settings. Both providers now persist free_access_confirmed=true and chat_model_allowlist=[openai/gpt-oss-20b] in providers.yaml. Other cloud policy gates are unchanged. The effective-gates table and SHA-256 table above describe the original tested candidate, before this subsequent configuration authorization.

Verification: instantiate ProviderRegistry with Settings(_env_file=None), assert no invalid profiles, then assert each provider is enabled, free_access_confirmed is true and its exact allowlist is [openai/gpt-oss-20b]. Result: PASS. This check does not load .env or make network requests. Existing real buffered/SSE probes already verified this model for both providers. No new tests or external generations were necessary for the YAML-only change. No application restart was performed; restart the backend to load the changed manifests. No deployment, commit or push occurred.

Updated providers.yaml SHA-256: `ccce0c87933f3b26e6f145a233f7307aae3ce6f5ce2372dcc63a665d18fd126a`.


## Corrective v1.2.0 implementation run — 2026-10-22

Owner explicitly approved exact v1.2.0 with recorded caveats and B1–B4 under PROJECT-PROCESS.md. Result acceptance remains separate; no commit/push/deployment authorized. Start identity: main HEAD 6d49e2a174a111dc0a5bb8745530a97d0e9786da plus pre-existing dirty tree; full path inventory saved in /tmp/t007-v120-start-status.txt. Historical evidence and hashes above identify the earlier candidate, not the correction. Initial startup checkpoint: B1 active and B2–B4 pending (superseded by the completed candidate below). Independent read-only architectural review requested; parent owns implementation and project records.

### Corrective candidate outcome and checkpoint execution

The bounded strict v1.2.0 code is implemented and verified by the final full suite; independent cumulative record verification is recorded below. It does not fulfill full Groq/NVIDIA activation or close T-007/P2. OpenRouter has a newly measured source-field gap: current 468-entry catalog lacks the required request fee everywhere, so no current provider is admitted from these source checks. This is not a successful live inference result; no new external generations were run. The owner requested a separate v1.2.1 source/admission proposal, not a runtime relaxation.

| Checkpoint | Implemented / evidence | Outcome and limit |
|---|---|---|
| B1 | Typed source/profile/auth/credential-epoch evidence, independent tariff/catalog freshness, bounded source refresh, duplicate-conflict quarantine, no static certification; strict unsupported/local provenance | Implemented; production-path price/lifecycle/bounds/epoch tests and final full regressions pass. Actual unknown source states remain unverified for positive admission. |
| B2 | Closed text/function-tool request validation, source-specific OpenRouter zero ceilings on every attempt, memory-only rechecks | Implemented; real-loopback socket capture verifies provider-owned caps and pre-I/O rejection. Unknown SDK fields intentionally return unsupported_free_request. |
| B3 | Scoped cost latch, monetary payer semantics, fixed balance holds/recovery permit, COMPLETE-first delivery, partial SSE interruption and terminal trace finalization | Implemented; controlled positive/invalid cost, same-event generation error, concurrency and framing-loss tests pass without paid external requests. |
| B4 | Fail-closed local/cloud distinction, operational evidence CLI, real periodic source free→paid revocation with health/listing progress, actual source probes and cumulative QA | Implemented safety behavior; actual positive provider/provenance delivery remains blocked/UNVERIFIED. No invented classifier or new gateway. |

**Execution deviation:** B2's isolated validator/helper was prepared while an early B1 full run was still failing migrated fixture expectations; the prescribed isolated sequential full gates were not all completed before dependent code preparation. Those early runs were interrupted/failed and never treated as passes; no intermediate application was activated. The final integrated full suite and independent cumulative review cover B1–B4 together. This records a sequencing deviation rather than inventing separate historical checkpoint passes.

**Failures and repairs:** Initial sandbox run: 195 passed / 3 failed solely because local socket bind was prohibited; permission-enabled baseline: 198 passed in 3.98s. Early integration runs exposed migrated test-source assumptions and were corrected. Independent QA found full source/auth binding omissions, post-terminal framing-loss handling, malformed answer/cost ordering, contradictory duplicate IDs and failed recovery renewal; all were repaired with targeted regressions. The complete response is retained before scope cancellation, while actual generation errors stay unsuccessful. A no-output prebuffer is bounded and role-only chunks do not establish semantic output.

**Fixture migration:** Existing routing/telemetry/proxy/manifest/discovery/socket scenarios remain. They explicitly install controlled synthetic evidence from backend/tests/eligibility_fixtures.py rather than granting runtime admission through flags. Original OpenRouter fixture catalogs now include request=0 and text modalities. Intentional replaced assertions: clearing an optional legacy list permits all already-certified models; free_access_confirmed never grants/revokes a certificate; source failure preserves raw visibility but immediately removes eligible admission; stream success is recorded at terminal completion, including close/disconnect failures. No original test function was removed. Synthetic sources/loopback policy injection are internal test construction, not CLI/YAML certification paths.

### Corrective AC trace

| AC | Result / evidence |
|---|---|
| AC-D1 | PASS on final candidate; full backend suite, all seven protected T-006 file hashes match. Historical prior runtime hashes above intentionally describe the earlier candidate. |
| AC-D2 | Synthetic previously unseen IDs auto-admit without list maintenance; actual non-seed catalog IDs automatically classify unknown without YAML/code edits. Positive admission of an actual current OpenRouter model is BLOCKED by missing request price; no false free-live pass. |
| AC-D3 | PASS controlled strict source semantics, malformed/positive/unknown prices, exact source/auth binding and duplicate-conflict tests; real Groq list prices do not certify account cost. |
| AC-D4 | PASS free→paid→free, exact expiry, failed refresh, distinct catalog/source timestamps and no-evidence behavior. |
| AC-D5 | PASS observed key removal/change-away-back and source/auth/endpoint epoch mutations, pending-fetch publication rejection and existing pending-attempt revocation/privacy checks. Unobserved external changes are not claimed. |
| AC-D6 | PASS structural/numeric/fee and client-function-tool cases; nested JSON Schema remains inert and unknown fields fail before I/O. |
| AC-D7 | PASS real sockets capture zero routing caps across attempts and reject client overrides; started-stream guard cases prohibit replay. |
| AC-D8 | PASS strict NVIDIA withholding; prior public-offer capture remains historical insufficient proof. No NVIDIA offer parser introduced. |
| AC-D9 | PASS bounded documents/records/deadlines/concurrency, refresh cancellation, memory-only reads and existing listing timing instrumentation. No per-model-page source implemented, so page cursor/page-fetch work is not exercised or claimed delivered. |
| AC-D10 | PASS real application plus distinct HTTP upstreams: periodic source free→paid revocation without catalog renewal, buffered/SSE cascade, health/listing during slow source read, owned server shutdown. |
| AC-D11 | Real catalog/evidence observations captured; positive Groq/NVIDIA key-scoped eligibility remains UNVERIFIED. Safe unknown is not a passed mandatory provider-delivery criterion. |
| AC-D12 | Independent cumulative source/runtime/evidence review performed; final record/capture verification outcome appended below. Owner result acceptance pending. |
| AC-D13 | PASS controlled buffered/SSE monetary values and shared-scope latch/cancellation/recovery tests. No paid live request induced. |
| AC-D14 | PASS real-socket complete buffered/final-SSE normal delivery, incomplete pre-output fallback and post-text/tools/reasoning interruption; exactly one terminal trace and resource cleanup. |
| AC-D15 | PASS exact billing signals, body-level errors, shared holds, Retry-After bounds/date and one failed/successful post-expiry recovery permit. |
| AC-D16 | PASS safe-unknown/provenance regression behavior; real pure-local provenance and cloud-free-only classification remain UNVERIFIED. No native positive classifier added. |

### Final commands and saved stdout

Final full command: .venv/bin/pytest backend/tests -q (permission-enabled local socket execution); stdout /tmp/t007-v120-final-tests.txt. CLI help: .venv/bin/python scripts/probe_multi_provider.py --help. Source-only commands: same script with --provider-id groq / nvidia_nim / openrouter / mistral / huggingface / local_ollama and --mode evidence. All six source checks exit 1 as UNVERIFIED with zero admitted candidates, never fake pass. Hard-skip profiles retain zero I/O and are not probed externally. Removed CLI --confirm-free-access; --model-id only selects an already dynamically eligible model. The probe generation path cannot certify/bypass unknown.

Capture `/tmp/t007-v120-baseline-tests.txt`:

```text
........................................................................ [ 36%]
........................................................................ [ 72%]
......................................................                   [100%]
198 passed in 3.98s
```

Capture `/tmp/t007-v120-b3-regression.txt`:

```text
........................................................................ [ 31%]
........................................................................ [ 63%]
........................................................................ [ 95%]
...........                                                              [100%]
227 passed in 4.53s
```

Capture `/tmp/t007-v120-b3-focused.txt`:

```text
.......................                                                  [100%]
23 passed in 0.07s
```

Capture `/tmp/t007-v120-final-candidate-tests.txt`:

```text
........................................................................ [ 25%]
........................................................................ [ 50%]
........................................................................ [ 76%]
...................................................................      [100%]
283 passed in 9.79s
```

Capture `/tmp/t007-v120-final-tests.txt`:

```text
........................................................................ [ 25%]
........................................................................ [ 50%]
........................................................................ [ 75%]
.....................................................................    [100%]
285 passed in 9.71s
```

Capture `/tmp/t007-v120-probe-help.txt`:

```text
usage: probe_multi_provider.py [-h] --provider-id PROVIDER_ID
                               --mode {catalog,evidence,proxy}
                               [--model-id MODEL_ID]

Reproducible T-007 catalog and real-loopback proxy checks; prints metadata
only.

options:
  -h, --help            show this help message and exit
  --provider-id PROVIDER_ID
  --mode {catalog,evidence,proxy}
  --model-id MODEL_ID   Optional selection among currently dynamically
                        eligible raw IDs; cannot grant admission.
```

External evidence summary (full sanitized captures in RECON): Groq 11 unknown, NVIDIA 83 unknown, OpenRouter 468 unknown, Mistral 53 catalog IDs / 27 eligible-capability observations unknown, HF 128 unknown, local Ollama one visible ID with unverified provenance. The earlier zero-local-model observation is historical; it is not the current source result. No inference was attempted for any unknown source.

### Corrective saved candidate hashes (after final suite)

These replace neither the earlier tables nor historical captures. They identify the corrected saved code/config/tests/probe at this checkpoint; no documentation hashes are used circularly.

| Path | SHA-256 |
|---|---|
| `.env.example` | `7c1fbf82c08369141ea80205e5ca00408925ed0ebadb8c33675cc87c50ef3130` |
| `backend/app/config.py` | `f1387b1e1f37b63dd400d152a1a369f34a37faaed13024182ed8f30bde38bd87` |
| `backend/app/api/v1/chat.py` | `271077f1152407b56fa6e9a21fbd1713d61054ac2d254fcd0159d3f4e00b03f6` |
| `backend/app/core/providers/models.py` | `b19ccf97fb76309f339d138b0a668d5495a832b60fcd0b6f87ba13af2bcfcb3d` |
| `backend/app/core/providers/registry.py` | `9b7aa310490b435b004e4e3a764bebbe490de5109acd6d19ad8976ba0bc8fd6c` |
| `backend/app/core/providers/providers.yaml` | `641e495e7bf693c012d62a9454158bf0c2548447adef98c7c40756d85dbe5498` |
| `backend/app/core/discovery/orchestrator.py` | `8d5f1e4d9212a863cda2970874b52c5d541f2f5e8634a1e8f4c8fa2f76677bb9` |
| `backend/app/core/adapters/openai_client.py` | `be7ecbfbca053a5d9332456f0e556a112ab87d6b6cce7287bbf961cfb1712903` |
| `backend/app/core/balancer/router.py` | `fd36e5394f4de5fcedbe44bfd596fafe68c6c7ee79a2c117afa0d0f2c123e995` |
| `scripts/probe_multi_provider.py` | `8598a021e60ae1b03b3f09762f6b8166ef0aafd8ddfa55270b4de9183dc17e48` |
| `backend/app/core/eligibility/__init__.py` | `e73a88bc151cde8dd9b7ceb867b605ba89ba0de389795555832f3c18d9e0615b` |
| `backend/app/core/eligibility/billing.py` | `cf867209bf4a3d44a2b32e5c6c8355f59bf907c49f46261d3f791a4f2c37a893` |
| `backend/app/core/eligibility/evidence.py` | `140f973f672a908bea09dbdbea59a5c8af9395cf81ee7b1234ae2e35c8c6001f` |
| `backend/app/core/eligibility/request.py` | `3940ab383adae02290772260d2afacfc68d5135cce29b7817c1fb874c61a1637` |
| `backend/tests/eligibility_fixtures.py` | `cbd8c39325b4bac13e0a9b6e135bb0d5f4ac21c3cd40e99e5ccd97c267e14fdf` |
| `backend/tests/test_dynamic_eligibility.py` | `325a37029dd7dd86eea7acf567121d513fe3552afb33234ae07da38845a6073c` |
| `backend/tests/test_free_request_profile.py` | `13b922a923e82dca811912e3b065ee5a77429caeb3b52d4f524d8f8a7433fa35` |
| `backend/tests/test_billing_guard.py` | `43c8a1fd910785a574ecc49b6fcdc5f207338b50f84c03ab84e57fc5cf7933a2` |
| `backend/tests/test_cascade_failover.py` | `6490a9085d1ef92b659b57c55355c076cb491e05e1778869a207826043e9b54d` |
| `backend/tests/test_openai_proxy.py` | `1788711aec69f1dffb814be99bdc56f486cafe1e3d87929ac5ae7bcd683385c4` |
| `backend/tests/test_openrouter_discovery.py` | `07a15bf513b8dcfd0b87840ede96277dcec3380c43525417c4ca55559e89c3b9` |
| `backend/tests/test_provider_manifests.py` | `2bca067446ea5c5d9c8542656d5406859833b48adb3f154541827f619234e1d6` |
| `backend/tests/test_telemetry.py` | `0e7628fbbadd2ed00f9246188efc72286766f0d5b9fd203ec43db0922896c27a` |
| `backend/tests/test_multi_provider_discovery.py` | `79df0e276a14b9626d4f4b70c99194a5f22247f0fd50b390a3a65d715afdfe76` |
| `backend/tests/test_multi_provider_routing.py` | `c3c1367f3984bd145fde38f73ed91d2373dc0151846d48f0c86a46d377585273` |
| `backend/tests/test_multi_provider_live.py` | `6278f530759b7951e94161052f44a4987c73393d002d604ac2de06e224b79513` |

### Effective gates and environment

Saved manifest: OpenRouter eligibility_profile=openrouter_zero_price; every other provider has unsupported eligibility by default. Legacy cloud certification flags/lists were removed from the bundled manifest (still accepted in the schema, never grant evidence). Billing/request guards are unconditional in corrected code, not a separately disabled feature flag. These code/config changes apply on normal backend restart; no managed application restart or external deployment was performed. All probe-owned app/upstream servers were stopped. Real .env/credentials, accounts and provider plans were unchanged.

Under the measured sources after restart: OpenRouter/Groq/NVIDIA/Mistral/HF and unverified local Ollama have no eligible generation candidates; auto:free remains listed, requests safely report no active free provider. Gemini live deferral remains. Cloudflare/Cerebras/GitHub unconditional skips remain. Releasing unknown requires adequate current evidence under the approved contract; the requested v1.2.1 is a separate pending approval, not active code. Full T-007/P2 remains open. No commit/push/deployment or result acceptance inferred.

Final candidate command outcome: 285 passed in 9.71s. The last additional regression covers ownership of a response returned concurrently by a cancellation-resistant send; the adapter shields response cleanup. Earlier 227/257/283/284 totals describe earlier checkpoints, not this final total. Independent review is read-only; its final verification outcome follows separately.

### Final independent verification and remaining approval

Independent read-only cumulative QA cleared the repaired bounded runtime candidate, including same-event error/cost priority, cancellation-resistant send ownership, source/auth epochs, contradictory pricing and terminal response handling. It matched final stdout 285 passed in 9.71s and protected validation hashes; no remaining material runtime finding in the approved strict scope. It separately checked the v1.2.1 proposal against current official provider-routing/model-price documentation and the sanitized 468/20/one-endpoint capture. This is a review of a proposed contract, not implementation of that amendment. Reviewer writes: none; no tests, authenticated/inference requests or .env reads.

Final local record checks passed for nine affected records, 71 local links/paired markers, all latest corrective candidate hashes and all seven protected T-006 hashes; git diff --check passed. The initial pending-approval preparation state has been superseded only for v1.2.0. Owner result acceptance and v1.2.1 implementation approval remain pending. Full direct-provider/source/provenance delivery and P2 remain open.

Final record-verifier outcome: nine affected records / 71 local links and paired markers passed; all 26 latest corrective candidate hashes and seven protected validation hashes matched, and final 285-test stdout is embedded exactly. Historical startup/preparation status phrases were explicitly qualified after review. Runtime and proposal QA remain clear; no reviewer writes or scope-external mutations were observed.


## OpenRouter v1.2.1 implementation run — 2026-10-22

Owner explicitly approved exact amendment and its prescribed live checks in chat. Lightweight PROJECT-PROCESS.md applies. Start status: /tmp/t007-v121-start-status.txt; v1.2.0 candidate hashes matched before edits. Source predicate/policy coupling, focused/regression verification and bounded live checks are authorized; result acceptance remains separate. Historical hashes/evidence above remain unchanged.

### v1.2.1 implemented behavior and verification

Only absent pricing.request under the exact bound OpenRouter profile selects catalog_zero_tokens_with_request_ceiling / free_enforced. Present zero retains the previous basis; positive is paid; null/bool/malformed/negative/nonfinite stays unknown. Other fee/capability predicates, overrides rejection, TTL/epoch/billing/output rules and other provider gates are unchanged. Raw source metadata is not modified and no monetary zero is synthesized. One owned policy builder supplies both dispatch payload and capability checks. Listing/admission/request rechecks exclude the new basis when the policy, endpoint or auth binding is lost; prepare_dispatch rejects a malformed owned policy.

Amendment verification: first full suite 306 passed in 9.68s; final full suite 311 passed in 10.85s, including parameterized buffered/SSE real-socket cap and no-route/failover cases plus fixed failure-diagnostic redaction. Full commands: .venv/bin/pytest backend/tests -q, git diff --check; CLI --help also executed. All seven protected validation hashes and 19 v1.2.0 candidate paths outside the amendment runtime scope remain unchanged. Runtime changes are exactly evidence.py, request.py, registry.py, the operational probe and the two scoped test modules; no adapter/router/billing/schema/manifest changes.

### v1.2.1 real delivery outcome

Source-only command: .venv/bin/python scripts/probe_multi_provider.py --provider-id openrouter --mode evidence; exit 0, 468 catalog entries, 20 admitted using free_enforced. Current source metadata is observed dynamically without a model selector or model-list edit. Other outcomes: 322 paid, 126 unknown.

Bounded generation command: .venv/bin/python scripts/probe_multi_provider.py --provider-id openrouter --mode proxy; exit 1. It used an isolated real loopback application with normal discovery/lifespan, actual CascadeRouter/adapter and real outbound HTTP transport. A request hook verified the actual outbound model, max_tokens=32 and all zero ceilings before transport. max_failover_attempts=1; no fake transport/provider reply. Exactly one buffered generation attempt occurred and returned proxy HTTP 503; its trace had one attempt. Billing hold was null and cost reporting unavailable, which does NOT prove no charge. The provider's exact upstream failure status/cause was not retained by that probe revision and cannot be reconstructed from its pool-budget envelope. Do not assert that it was a no-route, auth, rate-limit or price-enforcement error.

The probe stopped after that failure and did not execute SSE; no retry or second external generation occurred. AC-O7 is UNVERIFIED/failed external delivery, not PASS. The implemented diagnostic omission was corrected afterwards: future runs retain fixed attempt status/HTTP code and actual outbound HTTP response status, without raw provider error text, model IDs, secrets or generated text. The correction has a regression test and is included in the final suite. No new generation was performed to exercise it: the approved one-buffered allowance was already used. A further buffered diagnostic attempt needs a new explicit bound/authorization; the failed run is preserved rather than overwritten.

| AC | Outcome |
|---|---|
| AC-O1 | PASS — full suite 311 passed; protected validation and unrelated runtime hashes preserved. |
| AC-O2 | PASS — absent-vs-present price matrix and unchanged metadata assertions. |
| AC-O3 | PASS — token/other-fee/override/modality/tool boundary regressions retained. |
| AC-O4 | PASS — dispatch profile, owned policy definition/capability, source and auth mutation tests remove admission before I/O. |
| AC-O5 | PASS — real-socket buffered/SSE 429 and no-route 404 failover retain all caps; client routing override rejected before I/O. Actual live hook also verified outbound zero caps. |
| AC-O6 | PASS source observation — actual current catalog/evidence admits 20 dynamic offers with explicit basis/reason/age; no manual ID selector/certification. This is not generation delivery proof. |
| AC-O7 | UNVERIFIED — buffered proxy 503; SSE NOT RUN after failure. Upstream cause unknown, no charge claim. |
| AC-O8 | Independent cumulative local QA clear; final records/hash/capture verification recorded below. Result acceptance remains pending. |

### v1.2.1 captures

Capture `/tmp/t007-v121-focused-tests.txt`:

```text
...........................................................              [100%]
59 passed, 1 deselected in 0.21s
```

Capture `/tmp/t007-v121-first-regression.txt`:

```text
........................................................................ [ 23%]
........................................................................ [ 47%]
........................................................................ [ 70%]
........................................................................ [ 94%]
..................                                                       [100%]
306 passed in 9.68s
```

Capture `/tmp/t007-v121-final-tests.txt`:

```text
........................................................................ [ 23%]
........................................................................ [ 46%]
........................................................................ [ 69%]
........................................................................ [ 92%]
.......................                                                  [100%]
311 passed in 10.85s
```

Capture `/tmp/t007-v121-probe-help.txt`:

```text
usage: probe_multi_provider.py [-h] --provider-id PROVIDER_ID
                               --mode {catalog,evidence,proxy}
                               [--model-id MODEL_ID]

Reproducible T-007 catalog and real-loopback proxy checks; prints metadata
only.

options:
  -h, --help            show this help message and exit
  --provider-id PROVIDER_ID
  --mode {catalog,evidence,proxy}
  --model-id MODEL_ID   Optional selection among currently dynamically
                        eligible raw IDs; cannot grant admission.
```

Capture `/tmp/t007-v121-openrouter-evidence.jsonl`:

```text
{"outcome": "verified", "catalog_outcome": "succeeded", "code": null, "catalog_count": 468, "admitted_count": 20, "duration_ms": 664.83, "eligibility": {"states": {"free": 20, "paid": 322, "unknown": 126}, "reasons": {"free_enforced": 20, "paid": 322, "price_scope_unknown": 119, "invalid_evidence": 7}, "bases": ["catalog_effective_price", "catalog_zero_tokens_with_request_ceiling", "none"], "source_ids": ["openrouter_zero_price"], "observed_at": "2026-10-22T21:34:10.841268+00:00", "expires_in_seconds": 119.991}, "billing": {"kind": null}, "source_ids": ["openrouter_zero_price"], "bases": ["catalog_effective_price", "catalog_zero_tokens_with_request_ceiling", "none"], "source_age_seconds": 0.009, "observed_at": "2026-10-22T21:34:10.841268+00:00", "expires_in_seconds": 119.99}
```

Capture `/tmp/t007-v121-openrouter-live.jsonl`:

```text
{"outcome": "failed", "catalog_count": 468, "admitted_count": 20, "results": [{"stream": false, "http_status": 503, "passed": false, "protocol_valid": false, "semantic_output": false, "cost_reporting": "unavailable", "attempt_count": 1, "basis": "catalog_zero_tokens_with_request_ceiling", "reason": "free_enforced", "billing": {"kind": null}, "wire": [{"stream": false, "max_tokens": 32, "zero_caps_verified": true, "model_matches": true}]}], "duration_ms": 2129.76, "eligibility": {"states": {"free": 20, "paid": 322, "unknown": 126}, "reasons": {"free_enforced": 20, "paid": 322, "price_scope_unknown": 119, "invalid_evidence": 7}, "bases": ["catalog_effective_price", "catalog_zero_tokens_with_request_ceiling", "none"], "source_ids": ["openrouter_zero_price"], "observed_at": "2026-10-22T21:35:12.975194+00:00", "expires_in_seconds": 118.554}}
```

Capture `/tmp/t007-v121-openrouter-live-stderr.txt`:

```text
All pool candidates exhausted: Failover attempt budget reached.
```

### v1.2.1 saved candidate hashes

Historical tables identify previous candidates; this table identifies only the amendment's verified runtime/test/probe bytes.

| Path | SHA-256 |
|---|---|
| `backend/app/core/eligibility/evidence.py` | `11f3497084c70f2fb9ee5311b95056c3e88bb2fe0f149e4e03f00031eff725f9` |
| `backend/app/core/eligibility/request.py` | `4d323bc3b2b86c941358a1f33334abfd81348afbc33667b7604e7b2d70e8ea46` |
| `backend/app/core/providers/registry.py` | `bfd2632b119236c1f89484b7c476058126a7b7f1ea07a992d03ecb0439fc33ef` |
| `scripts/probe_multi_provider.py` | `f6b5326145e4b274f7c9fd98d6e3dce36a3e56950daaba87076c444375e8e4cd` |
| `backend/tests/test_dynamic_eligibility.py` | `fcf91e1b967e95c0e1eb21b218a0daffa3f620840b93fa7f9aca26f76b516051` |
| `backend/tests/test_free_request_profile.py` | `9a129ea1dfd40f1f9c91a7706bfdffd4392ff1c3c757d97a8ffd7074b0a6436e` |

### v1.2.1 environment and gates

The existing OpenRouter profile is enabled in the saved manifest, and the amended basis is unconditional in corrected source; no new feature flag or manifest/model list was added. Saved code applies on normal backend restart; no managed application restart or external deployment performed. Isolated live/test app and outbound clients were closed. Current live source admits 20 OpenRouter offers under the provider-enforced guarantee, with only one generation attempt observed and failed; other providers' strict unknown/exclusion/deferral policies remain unchanged. Full T-007/P2 and result acceptance remain open. No .env/key/account/plan change, commit, push or deployment.

### v1.2.1 final independent record verification

Read-only cumulative verification found no remaining local runtime/record issue. It matched all seven amendment captures, final 311 passed / 10.85s, all six latest candidate hashes, 19 out-of-scope v1.2.0 baseline hashes and seven protected validation hashes. Eight affected records / 57 local links and paired markers passed. AC-O8 local review is complete; AC-O7 remains UNVERIFIED as recorded, so no overall external-delivery completion or owner acceptance is claimed. Reviewer writes, tests, network and .env reads: none. Final git diff --check passed. Any repeated buffered external attempt requires a renewed explicit bound; no further request was sent.


## v1.2.1 renewed bounded diagnostic run — 2026-10-22

Owner explicitly authorized one new buffered and one SSE probe at 32 output tokens each with improved diagnostics and requested investigation of 503. Start inventory: /tmp/t007-v121-reprobe-start-status.txt. Before using the allowance, the probe was extended to classify fixed redacted error reasons from a bounded in-memory identity-encoded response observation; adapter reads remain unchanged and no provider text is persisted. No tariff/admission/output/account-policy change. Probe-only regression tests pass; independent pre-live verification follows.

### Renewed attempts and wire-format repair

The renewed allowance was used exactly once per mode: one buffered attempt and one SSE attempt, each max_tokens=32 and max_failover_attempts=1. Both returned upstream HTTP 400 and proxy HTTP 503; the router's exhausted-attempt envelope accounts for the outward 503. The buffered run stopped before SSE; the separate SSE-only command did not repeat buffered generation. No valid answer or monetary report was received. Billing hold null does not establish zero charge. AC-O7 remains UNVERIFIED.

Safe diagnostics retained fixed status/reason enums and whitelisted field references only. The SSE error referenced provider/request but did not expose a specific type-validation reason. Raw provider text, model IDs, credentials and generated content were not persisted. The stream observer preserves transport bytes and closes its underlying stream; its diagnostic prefix is bounded to 65536 bytes. Tests cover nested encoded error redaction and stream cleanup.

The current official [OpenAPI schema](https://openrouter.ai/openapi.json), ProviderPreferences.properties.max_price, requires string values for prompt/completion/request/image (also audio). Previous dispatch sent numeric zero for all four required axes. This is a demonstrated wire-schema defect, missed by earlier socket tests that mirrored the numeric assumption. It is a plausible explanation of the upstream 400, not proof of its sole cause. The builder, strict validator, wire observer and regression assertions now require canonical string "0" for all four limits, retaining require_parameters=true. Numeric legacy policy is rejected; no ceiling was omitted or relaxed. A public unauthenticated schema GET and an offline typed comparison confirmed the discrepancy and corrected payload types; neither performed inference.

Final full regression: 323 passed in 11.02s. Independent read-only delta QA confirmed the official schema, current wire types, diagnostics, captures and retained financial/source bindings. No post-fix external generation has been performed: the renewed one-buffered/one-SSE allowance is exhausted. Post-fix delivery and exact upstream causality remain unverified; no live-pass or result acceptance is claimed.

Actual commands (each executed once):

```text
.venv/bin/python scripts/probe_multi_provider.py --provider-id openrouter --mode proxy
.venv/bin/python scripts/probe_multi_provider.py --provider-id openrouter --mode proxy --generation sse
```

The following are exact sanitized captures. Historical zero_caps_verified=true refers to numeric zeros verified by the observer at that checkpoint, not proof of the corrected string wire type.

Capture /tmp/t007-v121-reprobe-live.jsonl:

```text
{"outcome": "failed", "catalog_count": 468, "admitted_count": 20, "results": [{"stream": false, "http_status": 503, "passed": false, "protocol_valid": false, "semantic_output": false, "cost_reporting": "unavailable", "attempt_count": 1, "attempts": [{"status": "http_error", "http_status": 400}], "basis": "catalog_zero_tokens_with_request_ceiling", "reason": "free_enforced", "billing": {"kind": null}, "wire": [{"stream": false, "max_tokens": 32, "zero_caps_verified": true, "model_matches": true}]}], "duration_ms": 1960.25, "eligibility": {"states": {"free": 20, "paid": 322, "unknown": 126}, "reasons": {"free_enforced": 20, "paid": 322, "price_scope_unknown": 119, "invalid_evidence": 7}, "bases": ["catalog_effective_price", "catalog_zero_tokens_with_request_ceiling", "none"], "source_ids": ["openrouter_zero_price"], "observed_at": "2026-10-22T21:54:52.387257+00:00", "expires_in_seconds": 118.807}, "upstream_http_statuses": [400], "upstream_diagnostics": [{"http_status": 400, "error_status": 400, "reason": "upstream_request_rejected"}]}
```

Capture /tmp/t007-v121-reprobe-sse.jsonl:

```text
{"outcome": "failed", "catalog_count": 468, "admitted_count": 20, "results": [{"stream": true, "http_status": 503, "passed": false, "protocol_valid": false, "semantic_output": false, "cost_reporting": "unavailable", "attempt_count": 1, "attempts": [{"status": "http_error", "http_status": 400}], "basis": "catalog_zero_tokens_with_request_ceiling", "reason": "free_enforced", "billing": {"kind": null}, "wire": [{"stream": true, "max_tokens": 32, "zero_caps_verified": true, "model_matches": true}]}], "generation_modes": ["sse"], "duration_ms": 2215.98, "eligibility": {"states": {"free": 20, "paid": 322, "unknown": 126}, "reasons": {"free_enforced": 20, "paid": 322, "price_scope_unknown": 119, "invalid_evidence": 7}, "bases": ["catalog_effective_price", "catalog_zero_tokens_with_request_ceiling", "none"], "source_ids": ["openrouter_zero_price"], "observed_at": "2026-10-22T21:57:13.323719+00:00", "expires_in_seconds": 118.807}, "upstream_http_statuses": [400], "upstream_diagnostics": [{"http_status": 400, "error_status": 400, "reason": "upstream_request_rejected", "field_references": ["provider", "request"], "validation": []}]}
```

Capture /tmp/t007-v121-max-price-schema.json:

```text
{"source": "https://openrouter.ai/openapi.json", "schema": "ProviderPreferences.properties.max_price", "observed_at": "2026-10-22T21:59:31.021738+00:00", "http_status": 200, "wire_types": {"audio": "string", "completion": "string", "image": "string", "prompt": "string", "request": "string"}}
```

Capture /tmp/t007-v121-wire-schema-check.json:

```text
{"source": "https://openrouter.ai/openapi.json", "schema": "ProviderPreferences.properties.max_price", "previous_numeric_type_mismatches": ["prompt", "completion", "request", "image"], "current_wire_types_match": true, "all_current_limits_exact_zero": true, "generation_requests": 0}
```

Capture /tmp/t007-v121-string-ceilings-tests.txt:

```text
........................................................................ [ 22%]
........................................................................ [ 44%]
........................................................................ [ 66%]
........................................................................ [ 89%]
...................................                                      [100%]
323 passed in 11.02s
```

### Renewed diagnostic candidate hashes

This table supersedes earlier hashes only for the current six amendment paths.

| Path | SHA-256 |
|---|---|
| `backend/app/core/eligibility/evidence.py` | `11f3497084c70f2fb9ee5311b95056c3e88bb2fe0f149e4e03f00031eff725f9` |
| `backend/app/core/eligibility/request.py` | `2588a80c9729437903a50bf08bf233b85d324409a13b070a4dabb3575d13fa21` |
| `backend/app/core/providers/registry.py` | `bfd2632b119236c1f89484b7c476058126a7b7f1ea07a992d03ecb0439fc33ef` |
| `scripts/probe_multi_provider.py` | `608fe41be3aa24a1f060b3c0cc433135305aef17e3f2fe993effa27fa10415f8` |
| `backend/tests/test_dynamic_eligibility.py` | `fcf91e1b967e95c0e1eb21b218a0daffa3f620840b93fa7f9aca26f76b516051` |
| `backend/tests/test_free_request_profile.py` | `7567d8226c69c152d365ab345e80d6f2ef524d6f6c5e0c393b554847fb2790e2` |

No manifest, .env, key, provider account/plan or financial policy change. OpenRouter remains enabled in saved configuration; corrected source requires normal backend restart, which was not performed. Other provider gates remain unchanged. No deployment, commit or push. Reviewer write paths: none.

### Renewed run final independent record verification

Read-only verification matched all five final captures, 323 passed / 11.02s, six latest candidate hashes, 19 out-of-scope baseline hashes and seven protected T-006 hashes. Local links, paired markers and git diff --check passed. Records correctly retain both single-attempt 400 → 503 outcomes, the proven wire-type defect with qualified causal inference, exhausted allowance and AC-O7 UNVERIFIED. Reviewer writes/tests/network/.env reads: none. No write outside the reviewer's allowed paths occurred (allowed write paths: none).

## Post-fix bounded live checks — 2026-10-22 local / 2026-10-23 UTC

Owner explicitly authorized one additional buffered and one SSE attempt after the string-wire fix, 32 output tokens each. Pre-run status: /tmp/t007-v121-postfix-start-status.txt. Both actual attempts were used exactly once, with one trace attempt each and all four canonical string-zero ceilings verified by the outbound observer. Both still received upstream HTTP 400 and proxy HTTP 503; no valid answer, semantic output or monetary report was received. AC-O7 remains UNVERIFIED. This disproves the expectation that changing the price value types alone restores delivery; the exact remaining rejection cause is unresolved. Do not describe the string fix as sufficient or a confirmed sole cause.

The first sandbox invocation failed during transport/configuration setup (no results/wire/attempt data); its failure capture is retained separately. The permission-enabled buffered invocation reached OpenRouter once. The SSE invocation used a temporary diagnostic wrapper importing the unchanged repository probe; it added only fixed phrase-match labels from the bounded in-memory error payload. No match was observed; no raw provider text or credentials were printed or persisted. The wrapper's process exit status was zero because it did not propagate main()'s return, so only the JSON outcome determines result: failed. No inference was retried and no caps were removed.

Commands:

```text
.venv/bin/python scripts/probe_multi_provider.py --provider-id openrouter --mode proxy --generation buffered
.venv/bin/python /tmp/t007_postfix_sse.py
```

The temporary SSE wrapper selected --provider-id openrouter --mode proxy --generation sse and changed diagnostics only. Its path is an ephemeral run artifact, not maintained application code.

Capture /tmp/t007-v121-postfix-buffered.jsonl:

```json
{"outcome": "failed", "code": "probe_transport_or_configuration_error"}
```

Capture /tmp/t007-v121-postfix-buffered-network.jsonl:

```json
{"outcome": "failed", "catalog_count": 468, "admitted_count": 20, "results": [{"stream": false, "http_status": 503, "passed": false, "protocol_valid": false, "semantic_output": false, "cost_reporting": "unavailable", "attempt_count": 1, "attempts": [{"status": "http_error", "http_status": 400}], "basis": "catalog_zero_tokens_with_request_ceiling", "reason": "free_enforced", "billing": {"kind": null}, "wire": [{"stream": false, "max_tokens": 32, "zero_caps_verified": true, "model_matches": true}]}], "generation_modes": ["buffered"], "duration_ms": 2085.04, "eligibility": {"states": {"free": 20, "paid": 322, "unknown": 126}, "reasons": {"free_enforced": 20, "paid": 322, "price_scope_unknown": 119, "invalid_evidence": 7}, "bases": ["catalog_effective_price", "catalog_zero_tokens_with_request_ceiling", "none"], "source_ids": ["openrouter_zero_price"], "observed_at": "2026-10-23T00:06:21.496922+00:00", "expires_in_seconds": 118.755}, "upstream_http_statuses": [400], "upstream_diagnostics": [{"http_status": 400, "error_status": 400, "reason": "upstream_request_rejected", "field_references": ["provider", "request"], "validation": []}]}
```

Capture /tmp/t007-v121-postfix-sse.jsonl:

```json
{"outcome": "failed", "catalog_count": 468, "admitted_count": 20, "results": [{"stream": true, "http_status": 503, "passed": false, "protocol_valid": false, "semantic_output": false, "cost_reporting": "unavailable", "attempt_count": 1, "attempts": [{"status": "http_error", "http_status": 400}], "basis": "catalog_zero_tokens_with_request_ceiling", "reason": "free_enforced", "billing": {"kind": null}, "wire": [{"stream": true, "max_tokens": 32, "zero_caps_verified": true, "model_matches": true}]}], "generation_modes": ["sse"], "duration_ms": 2603.93, "eligibility": {"states": {"free": 20, "paid": 322, "unknown": 126}, "reasons": {"free_enforced": 20, "paid": 322, "price_scope_unknown": 119, "invalid_evidence": 7}, "bases": ["catalog_effective_price", "catalog_zero_tokens_with_request_ceiling", "none"], "source_ids": ["openrouter_zero_price"], "observed_at": "2026-10-23T00:07:02.010698+00:00", "expires_in_seconds": 118.522}, "upstream_http_statuses": [400], "upstream_diagnostics": [{"http_status": 400, "error_status": 400, "reason": "upstream_request_rejected", "field_references": ["provider", "request"], "validation": [], "diagnostic_matches": []}]}
```

No repository code changed during this checkpoint, so the previous six candidate hashes and 323-test regression remain applicable; the suite was not rerun. No backend restart, deployment, .env/account/plan change, commit or push. Temporary isolated proxy servers/clients closed. The new allowance is exhausted. Further authorized work can investigate protocol compatibility locally or via public documentation; additional generation requires a new explicit bound. Missing cost information is not proof of zero charge.

Independent read-only checkpoint verification: all three new captures match records, six current candidate hashes unchanged, 40 local links and paired markers valid, git diff --check clear. Both post-fix failures, unresolved cause, previous regression without rerun and exhausted allowance are accurately recorded. Reviewer writes/tests/network/.env reads: none. Start/end git status inventories match; no agent write outside allowed paths (none).

## HTTP 400 investigation and text-output admission repair — 2026-10-23

### Authorization and root finding

Owner explicitly authorized the necessary repeated short checks, each capped at 32 output tokens with all free constraints retained, until generation works. This supersedes earlier exhausted-allowance stops for this investigation. Start inventory: /tmp/t007-rootcause-start-status.txt. Live checks were stopped after a fully successful buffered/SSE pair; no further generation is needed for this checkpoint.

The exact error chain is now established: the first selected route returned a nested provider INVALID_ARGUMENT / "Request contains an invalid argument" error; OpenRouter returned HTTP 400, and the isolated proxy's one-attempt budget exposed HTTP 503. The provider did not identify the rejected argument. Do not claim a specific invalid field, or that the prior string-wire repair was the sole cause.

A concrete admission defect explains why this inappropriate route was selected: the first two candidates in the actual zero-token-price public catalog were Lyria music endpoints, advertising text+audio outputs and zero prompt/completion prices, while official pages document per-song charges. [Lyria Clip](https://openrouter.ai/google/lyria-3-clip-preview) documents $0.04 per clip and [Lyria Pro](https://openrouter.ai/google/lyria-3-pro-preview) $0.08 per song. Existing evidence required only that output modalities contain text, so these endpoints wrongly received the text_chat_v1 guarantee despite uncovered audio/song scope. Public unauthenticated source snapshots are /tmp/t007-rootcause-public-models.json and /tmp/t007-rootcause-lyria-public.json. They contain public catalog data only, no account or credentials.

The correction is structural, not a model list: source_verdict now requires output_modalities exactly ["text"]. Mixed/other outputs remain unknown / unsupported_output_modality, even with zero token prices; multiple text input modalities do not enable media input in the closed request profile. No description parser, suffix rule, model blacklist, account attestation, weakened ceiling or new generation parameter was introduced. This conservative tightening was performed under the owner's explicit root-cause repair grant. The older approved contains-text predicate remains historical; it is superseded for current execution by this stricter text-only-output boundary.

Current source snapshot: 468 catalog entries; 18 admitted, 322 paid, 128 unknown. Unknown reasons: price_scope_unknown 107, unsupported_output_modality 16, invalid_evidence 5. The two formerly admitted music models are no longer routable. Historical successful-looking music responses are NOT evidence of valid free text chat. No positive charge was reported in retained results, but unavailable cost is not proof of zero charge; numerical token ceilings do not establish that song generation is free.

### Diagnostic and live-proof repairs

The probe now classifies the fixed provider_invalid_argument reason, supports a candidate index within the current eligible set, optional normal auto:free routing and an attempt budget bounded by configured max_failover_attempts (default probe budget remains one). Every actual hop is still capped at max_tokens=32 and checked for all four canonical string-zero ceilings plus require_parameters=true, current model eligibility and trace/wire identity correspondence. No maintained model-ID list or change to production routing/order was introduced.

The live-proof criterion was corrected: actual visible nonwhitespace content or client tool-call output is required in both modes. A role-only/reasoning-only stream, or buffered null/empty content, is not a PASS even when protocol framing is valid. Runtime complete-answer and no-replay semantics were not changed. Captures 02 (music route), 05 (empty buffered response and earlier SSE reasoning criterion) and other pre-fix protocol-only outcomes must not be promoted to valid current text-chat proof.

Several valid text endpoints returned HTTP 200 / reported cost zero but no visible answer at completion_tokens=32, finish_reason=length with reasoning present. This establishes budget exhaustion with no answer, not that all tokens were proven reasoning tokens. Other transient outcomes included 429, 403, 404 and timeout. Structured-JSON, function-tool and documented assistant-prefill checks used only existing closed-profile fields in temporary wrappers; no reasoning control field was added. The stable probe prompt is the minimal text question 1+1=?.

### Actual final delivery proof

The sequential short scan stopped at the first full pair passing the corrected criteria. Candidate index 12 refers only to that current dynamic source ordering and is not saved in provider configuration. Both modes returned HTTP 200 with actual visible content, one successful trace attempt each, reported usage.cost=0, no billing hold, and all zero ceilings/identity checks true. Buffered completion used 13 tokens within the 32-token cap; SSE had exactly one DONE and valid framing. This verifies AC-O7 for the corrected OpenRouter text-chat profile, not every offer, provider, account or full T-007/P2.

Final actual command reached by the scan:

```text
.venv/bin/python scripts/probe_multi_provider.py --provider-id openrouter --mode proxy --candidate-index 12
```

Exact final capture /tmp/t007-rootcause-scan-12.jsonl:

```json
{"outcome": "passed", "catalog_count": 468, "admitted_count": 18, "candidate_index": 12, "attempt_budget": 1, "auto": false, "results": [{"stream": false, "http_status": 200, "passed": true, "protocol_valid": true, "semantic_output": true, "answer_shape": {"content_chars": 29, "reasoning_present": false, "finish_reason": "stop", "completion_tokens": 13}, "cost_reporting": "zero", "attempt_count": 1, "attempts": [{"status": "success", "http_status": 200}], "basis": "catalog_zero_tokens_with_request_ceiling", "reason": "free_enforced", "billing": {"kind": null}, "wire": [{"stream": false, "max_tokens": 32, "zero_caps_verified": true, "model_matches": true}]}, {"stream": true, "http_status": 200, "passed": true, "protocol_valid": true, "semantic_output": true, "answer_shape": null, "cost_reporting": "zero", "attempt_count": 1, "attempts": [{"status": "success", "http_status": 200}], "basis": "catalog_zero_tokens_with_request_ceiling", "reason": "free_enforced", "billing": {"kind": null}, "wire": [{"stream": true, "max_tokens": 32, "zero_caps_verified": true, "model_matches": true}]}], "generation_modes": ["buffered", "sse"], "duration_ms": 3487.87, "eligibility": {"states": {"free": 18, "paid": 322, "unknown": 128}, "reasons": {"free_enforced": 18, "paid": 322, "price_scope_unknown": 107, "unsupported_output_modality": 16, "invalid_evidence": 5}, "bases": ["catalog_effective_price", "catalog_zero_tokens_with_request_ceiling", "none"], "source_ids": ["openrouter_zero_price"], "observed_at": "2026-10-23T09:48:58.749060+00:00", "expires_in_seconds": 116.84}, "upstream_http_statuses": [200, 200], "upstream_diagnostics": [{"http_status": 200, "error_status": null, "reason": null, "field_references": [], "validation": []}, {"http_status": 200, "error_status": null, "reason": null, "field_references": [], "validation": []}]}
```

Final regression command:

```text
.venv/bin/python -m pytest backend/tests -q
```

Exact capture /tmp/t007-rootcause-final-tests.txt:

```text
........................................................................ [ 21%]
........................................................................ [ 43%]
........................................................................ [ 64%]
........................................................................ [ 86%]
..............................................                           [100%]
334 passed in 11.20s
```

The first non-escalated focused run had four expected sandbox socket-bind failures; permission-enabled targeted and full regressions passed. Final suite includes four mixed-output rejection cases, one nested provider-error classification case and six answer-output cases. No unrelated runtime, router/adapter, billing or telemetry implementation was changed at this checkpoint.

### Complete short-check ledger

Each row represents an actual captured mode; all captured outbound hops verified max_tokens=32 and zero caps. Captures are historical evidence from successive diagnostic candidates, not interchangeable certification. Each file resides in /tmp; only redacted metadata is retained. Temporary wrappers: /tmp/t007_rootcause_probe.py, /tmp/t007_tool_probe.py, /tmp/t007_json_probe.py, /tmp/t007_prefill_probe.py. Sequential scan: /tmp/t007_short_scan.py; stops on success, positive/invalid monetary report or billing hold. No raw upstream body, generated answer or credentials were persisted.

| Capture | Mode | Proxy HTTP | Visible output | Monetary report | Probe PASS at that checkpoint |
|---|---|---|---|---|---|
| `t007-rootcause-01.jsonl` | buffered | 503 | no | unavailable | False |
| `t007-rootcause-02.jsonl` | buffered | 200 | yes | zero | True |
| `t007-rootcause-03.jsonl` | SSE | 200 | not established | unavailable | False |
| `t007-rootcause-04.jsonl` | buffered | 503 | no | unavailable | False |
| `t007-rootcause-05.jsonl` | buffered | 200 | no | zero | True |
| `t007-rootcause-05.jsonl` | SSE | 200 | not established | zero | True |
| `t007-rootcause-06.jsonl` | buffered | 200 | no | zero | False |
| `t007-rootcause-07.jsonl` | buffered | 200 | no | zero | False |
| `t007-rootcause-08.jsonl` | buffered | 200 | no | zero | False |
| `t007-rootcause-09.jsonl` | buffered | 503 | no | unavailable | False |
| `t007-rootcause-10.jsonl` | buffered | 503 | no | unavailable | False |
| `t007-rootcause-11.jsonl` | buffered | 200 | no | zero | False |
| `t007-rootcause-12.jsonl` | buffered | 200 | no | zero | False |
| `t007-rootcause-13.jsonl` | buffered | 200 | no | zero | False |
| `t007-rootcause-14.jsonl` | buffered | 200 | no | zero | False |
| `t007-rootcause-15.jsonl` | buffered | 503 | no | unavailable | False |
| `t007-rootcause-16.jsonl` | buffered | 200 | no | zero | False |
| `t007-rootcause-17.jsonl` | buffered | 503 | no | unavailable | False |
| `t007-rootcause-18.jsonl` | buffered | 200 | no | zero | False |
| `t007-rootcause-19.jsonl` | buffered | 503 | no | unavailable | False |
| `t007-rootcause-20.jsonl` | buffered | 200 | no | zero | False |
| `t007-rootcause-scan-10.jsonl` | buffered | 200 | no | zero | False |
| `t007-rootcause-scan-11.jsonl` | buffered | 200 | no | zero | False |
| `t007-rootcause-scan-12.jsonl` | buffered | 200 | yes | zero | True |
| `t007-rootcause-scan-12.jsonl` | SSE | 200 | yes | zero | True |
| `t007-rootcause-scan-3.jsonl` | buffered | 503 | no | unavailable | False |
| `t007-rootcause-scan-5.jsonl` | buffered | 200 | yes | zero | True |
| `t007-rootcause-scan-5.jsonl` | SSE | 503 | no | unavailable | False |
| `t007-rootcause-scan-6.jsonl` | buffered | 503 | no | unavailable | False |
| `t007-rootcause-scan-7.jsonl` | buffered | 200 | yes | zero | True |
| `t007-rootcause-scan-7.jsonl` | SSE | 503 | no | unavailable | False |

Total telemetry attempts across this investigation: 31. Every captured mode had one attempt; the optional three-attempt auto check succeeded at protocol level on its first hop but failed the visible-answer criterion. No deliberately paid stress test or billing/account change was made.

### Current repaired candidate hashes

| Path | SHA-256 |
|---|---|
| `backend/app/core/eligibility/evidence.py` | `9b67ffa2d825cc9d5a9c2939ad1148dee49c8031a7825e03cf603540706d20f8` |
| `backend/app/core/eligibility/request.py` | `2588a80c9729437903a50bf08bf233b85d324409a13b070a4dabb3575d13fa21` |
| `backend/app/core/providers/registry.py` | `bfd2632b119236c1f89484b7c476058126a7b7f1ea07a992d03ecb0439fc33ef` |
| `scripts/probe_multi_provider.py` | `017dcec5433e51a325eaf32adf393959cced519f05994d7a0b3e6ac3d0ed0941` |
| `backend/tests/test_dynamic_eligibility.py` | `23792f02efa7b40755d0f8951323b28ed58ebb56f6d792acbde7d3a5ec4723d0` |
| `backend/tests/test_free_request_profile.py` | `7598da9beb35a274e1ddda10efc6273f2ae6c402f1bf260c837baf2d98957b08` |

OpenRouter remains enabled in saved configuration; the stricter evidence predicate applies on a normal backend restart, which was not performed on the managed service. Isolated live/test servers and clients were closed. No new feature flag, environment/key/account/plan edit, commit, push or deployment. Other provider gates/deferrals remain unchanged. Independent cumulative delta review and final record verification follow; result acceptance and full T-007/P2 remain open.

Current CLI help was executed locally after the final code changes and captured at /tmp/t007-rootcause-help.txt; it includes --max-attempts, --auto and --candidate-index. No external generation was performed by this help check. Historical SSE ledger cells whose old broad semantic flag could include reasoning are explicitly marked not established as visible output.

### Final independent cumulative verification

Independent read-only review found no material current code or final live-proof defect. It verified the final 334 passed / 11.20s capture, actual successful buffered/SSE scan12 pair with visible output and reported zero cost, all 31 unique recorded attempts and their 32-token/zero-cap bounds. Six latest candidate hashes match; exactly evidence.py, probe_multi_provider.py, test_dynamic_eligibility.py and test_free_request_profile.py differ from the preceding checkpoint. All seven protected T-006 hashes and 19 unaffected baseline hashes match. Eight affected records / 61 local links and fragments, paired markers, status inventory and git diff --check passed. The historical SSE visible-output wording was corrected as requested. AC-O7 and AC-O8 are verified for the repaired amendment candidate; result acceptance and full T-007/P2 remain open. Reviewer writes/tests/network/.env reads: none; no writes outside its allowed paths (none).

## Accepted repair and primary local backend verification — 2026-10-23

Owner accepted the correction and explicitly authorized restarting the primary backend and checking buffered/SSE there at 32 tokens with all free constraints. This is approval of the repaired result and its local activation, not closure of full T-007/P2 or permission to push/deploy externally. Start inventory: /tmp/t007-main-restart-start-status.txt.

### Actual process state and activation

No running local backend process belonging to this project was found in command/cwd inspection. Port 8000 was occupied by unrelated oMLX; port 8123 belonged to unrelated OpenIntelligentUI. Neither was stopped or changed. The project backend was therefore started from its stopped state on the free loopback endpoint http://127.0.0.1:8001 using ordinary uvicorn, not the isolated probe application and without monkeypatches, fake providers or registry/client replacement.

Exact start capture /tmp/t007-main-start.json:

```json
{"action": "start_previously_stopped_backend", "pid": 37372, "base_url": "http://127.0.0.1:8001", "command": ["/Users/a1111/Dev/open_freebie_finder/.venv/bin/python", "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8001", "--log-level", "warning", "--no-access-log"], "cwd": "/Users/a1111/Dev/open_freebie_finder", "policy_hash": "9b67ffa2d825cc9d5a9c2939ad1148dee49c8031a7825e03cf603540706d20f8", "request_policy_hash": "2588a80c9729437903a50bf08bf233b85d324409a13b070a4dabb3575d13fa21", "started_at_unix": 1792749960.49031}
```

Persistent process metadata: /tmp/open-freebie-finder-main.pid; log: /tmp/open-freebie-finder-main.log. The normal service is left running. Runtime host/port are explicit CLI overrides; .env/configuration files, accounts, manifests and keys are unchanged. Before any future stop/restart, verify process identity and listener again rather than relying on a stale PID file. No OS autostart/launch-agent configuration was installed.

### Actual primary-service checks

The external client /tmp/t007_probe_main.py called this existing service's /health, /v1/models, /v1/chat/completions and /api/admin/telemetry/recent. It did not create or instrument a server. The live /v1/models list was authoritative for eligibility; public metadata selected only among currently admitted offers. The first client revision compared raw catalog IDs directly with canonical API IDs, selecting the generic free router instead of the intended candidate. Its buffered answer passed, but its SSE exhausted 32 tokens without visible output; it was not a complete pair pass. The client mapping was corrected using the existing canonical_name rule (OpenRouter removes :free); this changed only the temporary client, not the backend or accepted code.

Initial real-service capture /tmp/t007-main-live.jsonl:

```json
{"outcome": "failed", "base_url": "http://127.0.0.1:8001", "health_status": 200, "listed_count": 19, "openrouter_admitted_count": 18, "non_text_outputs_in_active_set": 0, "candidate_index": 0, "zero_ceiling_source_policy_verified": true, "wire_observation": false, "results": [{"stream": false, "http_status": 200, "passed": true, "protocol_valid": true, "visible_output": true, "cost_reporting": "zero", "completion_tokens": 23, "done_count": null, "correlation_verified": true, "trace_verified": true, "request_max_tokens": 32, "attempts": [{"status": "success", "http_status": 200}]}, {"stream": true, "http_status": 200, "passed": false, "protocol_valid": true, "visible_output": false, "cost_reporting": "zero", "completion_tokens": 32, "done_count": 1, "correlation_verified": true, "trace_verified": true, "request_max_tokens": 32, "attempts": [{"status": "success", "http_status": 200}]}], "observed_at_unix": 1792750041.297486}
```

Final real-service capture /tmp/t007-main-live-final.jsonl:

```json
{"outcome": "passed", "base_url": "http://127.0.0.1:8001", "health_status": 200, "listed_count": 19, "openrouter_admitted_count": 18, "non_text_outputs_in_active_set": 0, "candidate_index": 12, "zero_ceiling_source_policy_verified": true, "wire_observation": false, "results": [{"stream": false, "http_status": 200, "passed": true, "protocol_valid": true, "visible_output": true, "cost_reporting": "zero", "completion_tokens": 32, "done_count": null, "correlation_verified": true, "trace_verified": true, "request_max_tokens": 32, "attempts": [{"status": "success", "http_status": 200}]}, {"stream": true, "http_status": 200, "passed": true, "protocol_valid": true, "visible_output": true, "cost_reporting": "zero", "completion_tokens": 13, "done_count": 1, "correlation_verified": true, "trace_verified": true, "request_max_tokens": 32, "attempts": [{"status": "success", "http_status": 200}]}], "observed_at_unix": 1792750127.336884}
```

The corrected pair passed both HTTP 200, visible content, protocol checks, correlation and actual main-service telemetry. Both reported usage.cost=0; buffered used 32 completion tokens and SSE 13, with exactly one DONE and a terminal frame. Each mode had one successful attempt to an OpenRouter offer present in the current admitted set. Four actual main-service generation requests were sent across the initial and corrected pairs, each requesting max_tokens=32; no positive/invalid cost was reported, and no further inference was sent after the complete success.

The main process was not instrumented to retain outbound wire data: wire_observation=false is intentional. Financial constraints are established here by the accepted unchanged source hashes/policy, actual text-only admission, normal routing/billing code and delivered monetary reports, together with the earlier real-wire/socket evidence for these exact policy bytes. Do not claim a new packet-level cap capture or main-memory billing-hold inspection. No request supplied a client provider override, media payload or new reasoning parameter.

Post-generation health/process evidence /tmp/t007-main-postcheck.json:

```json
{"pid": 37372, "base_url": "http://127.0.0.1:8001", "health_http": 200, "app_identity_verified": true, "models_http": 200, "listed_count": 19, "evidence_hash_matches_start": true, "request_policy_hash_matches_start": true}
```

Actual command/process /tmp/t007-main-process.txt:

```text
37372     1 /opt/homebrew/Cellar/python@3.15/3.15.0_1/Frameworks/Python.framework/Versions/3.15/Resources/Python.app/Contents/MacOS/Python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001 --log-level warning --no-access-log
```

Listener /tmp/t007-main-listener.txt:

```text
COMMAND   PID  USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
Python  37372 a1111   12u  IPv4 0x2c237ef063dabefc      0t0  TCP 127.0.0.1:8001 (LISTEN)
```

Primary runtime state: OpenRouter enabled with openrouter_zero_price and strict exact-text-output admission; 18 admitted offers plus auto:free (19 API entries). Groq/NVIDIA and other unproven profiles retain their unknown/provenance gates; Gemini live remains deferred; Cloudflare/Cerebras/GitHub remain skips; OpenCode/Kilo/Ollama Cloud not activated. No gate relaxation, financial/account policy change, .env edit, application code change, new feature flag, commit, push or external deployment. The previously verified 334-test candidate remains unchanged; tests were not rerun for this process-only activation. Independent final verification follows.

### Primary-service final independent verification

Read-only verification confirmed the actual final primary buffered/SSE pair: both HTTP 200, visible output, reported zero cost, one attempt each; buffered 32 tokens, SSE 13 and one DONE. All four main-service requests and the initial failed pair are honestly retained. All six captures match the note exactly; six current candidate hashes, seven T-006 hashes and 19 unaffected baseline hashes match. Thirty-four local links, paired markers, status inventory and git diff --check pass. Current lsof independently confirms PID 37372 listening on 127.0.0.1:8001. The unchanged 334-test result and absence of a new wire capture/billing-memory inspection are correctly qualified. Reviewer writes/tests/network/.env reads: none; no writes outside allowed paths (none). The owner-accepted correction is now verified on the primary local runtime and the process remains running.


## T-007 v1.3.0 specification preparation (2026-10-23)

Owner accepted the hybrid design and requested the complete [v1.3.0 correction](../specs/T-007-hybrid-account-eligibility.md). Exact implementation approval is pending. The proposed H1–H4 packet retains strict OpenRouter and adds default-off user-asserted nonbillable accounts with bounded dynamic buffered/SSE qualification for Groq/NVIDIA/Mistral/HF. It explicitly supersedes strict-only NVIDIA handling only for that named conditional mode. It introduces no manual model lists, account API proof, generic monetary scanner or unconditional no-charge guarantee.

Preparation updates the specification, historical pending cross-references and affected VISION/DEC-002/architecture/task/roadmap/handoff records. No application/manifest/example-environment source change, key/account/real-environment edit, inference, activation, restart, commit/push or deployment. The historical accepted 334-test result is not a new test run. Scope/inventory baseline: /tmp/t007-hybrid-spec-start-status.txt; runtime before-hashes: /tmp/t007-hybrid-runtime-before.json. Independent review and final document checks are recorded below when complete.

### Final independent specification review

Read-only reviewer verified the actual v1.3.0 text, source interpretation, resource math, affected records, links and protected runtime state. Three pre-approval ambiguities were fixed and independently rechecked: continued exploration/atomic replacement with a full five-route pool; immediate revocation on failed renewal with explicit retry/403 TTL; and automatic-probe suspension for consumer-origin as well as probe-origin balance holds, including honest process-local CLI limits. No remaining material findings. This is specification readiness, not implementation/result acceptance.

Verification: 11 affected documents, 91 existing local Markdown links, balanced paired specification markers, clean git diff --check. All 52 captured backend/scripts/example-environment file hashes, including the seven protected T-006 files, remain unchanged; no new runtime file. Expanded untracked inventory matches the preparation baseline except the new specification and intended record edits. Reviewer write scope NONE; actual writes outside it NONE. No tests, authenticated/inference requests, .env reads or service actions by the reviewer. Root performed documentation checks only; the running backend and real environment remain untouched. Check report: /tmp/t007-hybrid-doc-checks.json.

Next step: owner exact approval of v1.3.0 and its H1–H4/isolated live packet. The accepted hybrid design alone does not authorize implementing or activating it. Existing accepted OpenRouter service remains unchanged; no commit/push/external deployment.


## T-007 v1.3.0 implementation — owner authorized 2026-10-23

Owner approved the exact specification, H1–H4 and its bounded isolated live packet. Architecture: Registry owns AccountEligibility alongside existing EligibilityStore/BillingGuard. Account source snapshots and probe leases remain separate; private permits bind route/scope/revision, with ordinary admission computed from both clocks. Existing discovery lifecycle owns a separate bounded qualification worker; the shared adapter validates structured probe outcomes without changing ordinary completion/SSE semantics. HF stores pinned outbound IDs with independent route health and existing canonical base identity. Implementation gates: H1 deterministic assertion/evidence tests; H2 bounded worker/socket tests; H3 profiles/routing/full regression; H4 independent cumulative QA and at most eight 32-token inference sends/provider in an isolated process. Primary service and real configuration remain unchanged. Baseline captured before edits at /tmp/t007-h13-before.json and /tmp/t007-h13-status.txt.

H1 gate: targeted assertion/evidence/OpenRouter/request/T-006 tests — 196 passed in 2.61s. Initial sandbox-only run had 192 pass and four socket permission errors; rerun with authorized loopback capability passed. No inference or primary restart. H2 implementation follows.

H2 gate: 33 assertion/probe tests passed in 1.05s, including actual loopback TCP buffered/SSE for all four exact profiles; invalid framing/content, key-change cancellation, budget partitions and consumer-origin balance suspension. H3 discovery plus assertion regression: 60 passed in 1.71s. Full H3 regression and independent code/contract review follow. No external inference yet.

Independent pre-live core review found two defects, repaired with focused regressions: exhausted exploration budget could starve renewals and revoke a valid lease without an HTTP send; raw SSE could accept semantic data after a terminal finish. Selection now alternates available partitions with separate cursors; first-send local deferral preserves the old expiry, while partial/failed pairs revoke; raw qualification rejects choices after terminal while allowing a usage-only tail. Additional TCP scenarios verify ordinary buffered/SSE routing and absence of public telemetry during internal qualification. An expanded test initially compared ordinary empty-message requests against the fixed probe prompt; test inputs were corrected to send that prompt. No production protocol relaxation. Fresh cumulative gate follows.


### H4 bounded live outcomes and final candidate (2026-10-23)

Independent pre-live cumulative review cleared the owned assertion/worker/HF/guard paths and CLI before external inference. The approved isolated packet then ran once per provider using existing keys privately, process-local explicit nonbillable assertions, real HTTP/socket proxies and a hard eight-send/32-token hook. No real .env, account settings or primary service changed. The packet tried catalog order without saved model IDs or name heuristics.

| Provider | Inference sends | Qualification | Ordinary proxy buffered / SSE | Outcome |
|---|---:|---|---|---|
| Groq | 4 | Buffered and SSE actual200, visible text, 10 reported completion tokens each | Both actual200/PASS, one attempt each; buffered10, SSE32 completion tokens and one DONE | Conditional account delivery PASS; cost unavailable |
| NVIDIA | 3 | Three different catalog candidates returned404 on buffered qualification | Not sent: no qualified route | UNVERIFIED; catalog availability is not inference delivery |
| Mistral | 3 | Three candidates returned200 but failed strict buffered protocol qualification | Not sent: no qualified route | UNVERIFIED; actual protocol rejection cause was not captured |
| HF | 1 | First pinned candidate returned402 | Not sent: billing_access_unverified hold and automatic-probe suspension | UNVERIFIED; no paid fallback or background recovery |

Total11 inference sends, every outbound request max_tokens=32 and auth_bound=true; per-provider limits respected. NVIDIA/Mistral each consumed the allowed three-candidate exploration limit; do not silently start another packet or use remaining nominal eight-send headroom to expand that limit. HF stopped on the first balance-related hold. Groq stopped after both delivery modes passed. No positive/zero effective charge reporting is established for these profiles: all charge status unavailable, not zero. Free-account trust remains the operator premise.

Safe exact captures (including source/probe ages, lease, assertion time, route fingerprints, attempts and wire metadata):

- groq: `/tmp/t007-h13-live-groq.jsonl`; SHA-256 `74a007bdb415b6b268195e5b782156ac951cbf34e17c50fb8052435376bf31ca`.
- nvidia_nim: `/tmp/t007-h13-live-nvidia_nim.jsonl`; SHA-256 `a99cd682b0f046819e0636ae382ca5edf34e900c53a8e096b4060443356957e2`.
- mistral: `/tmp/t007-h13-live-mistral.jsonl`; SHA-256 `02329e7b2da21f843b1c0759a8bb3a1c240da5c5f4001e19cfeb54920bb58f31`.
- huggingface: `/tmp/t007-h13-live-huggingface.jsonl`; SHA-256 `0968d1e189e8b8b3c7c1f71df9c90922658d50912fbd83ce8c5b807d0ebd06e6`.

Persisted compact observations from those captures:

```json
{
  "groq": {
    "outcome": "PASS",
    "provider": "groq",
    "code": "conditional_account_delivery",
    "inference_sends": 4,
    "qualification": [
      {
        "provider": "groq",
        "stream": false,
        "status": 200,
        "passed": true,
        "completion_tokens": 10,
        "cost_status": "unavailable",
        "code": "available"
      },
      {
        "provider": "groq",
        "stream": true,
        "status": 200,
        "passed": true,
        "completion_tokens": 10,
        "cost_status": "unavailable",
        "code": "available"
      }
    ],
    "results": [
      {
        "stream": false,
        "http_status": 200,
        "passed": true,
        "visible_output": true,
        "completion_tokens": 10,
        "done_count": null,
        "attempt_count": 1,
        "cost_reporting": "unavailable",
        "assurance": "user_asserted"
      },
      {
        "stream": true,
        "http_status": 200,
        "passed": true,
        "visible_output": true,
        "completion_tokens": 32,
        "done_count": 1,
        "attempt_count": 1,
        "cost_reporting": "unavailable",
        "assurance": "user_asserted"
      }
    ],
    "billing": {
      "kind": null
    }
  },
  "nvidia_nim": {
    "outcome": "UNVERIFIED",
    "provider": "nvidia_nim",
    "code": "no_qualified_route_within_packet",
    "inference_sends": 3,
    "qualification": [
      {
        "provider": "nvidia_nim",
        "stream": false,
        "status": 404,
        "passed": false,
        "completion_tokens": null,
        "cost_status": "unavailable",
        "code": "upstream_http_error"
      },
      {
        "provider": "nvidia_nim",
        "stream": false,
        "status": 404,
        "passed": false,
        "completion_tokens": null,
        "cost_status": "unavailable",
        "code": "upstream_http_error"
      },
      {
        "provider": "nvidia_nim",
        "stream": false,
        "status": 404,
        "passed": false,
        "completion_tokens": null,
        "cost_status": "unavailable",
        "code": "upstream_http_error"
      }
    ],
    "results": [],
    "billing": {
      "kind": null
    }
  },
  "mistral": {
    "outcome": "UNVERIFIED",
    "provider": "mistral",
    "code": "no_qualified_route_within_packet",
    "inference_sends": 3,
    "qualification": [
      {
        "provider": "mistral",
        "stream": false,
        "status": 200,
        "passed": false,
        "completion_tokens": null,
        "cost_status": "unavailable",
        "code": "probe_inconclusive"
      },
      {
        "provider": "mistral",
        "stream": false,
        "status": 200,
        "passed": false,
        "completion_tokens": null,
        "cost_status": "unavailable",
        "code": "probe_inconclusive"
      },
      {
        "provider": "mistral",
        "stream": false,
        "status": 200,
        "passed": false,
        "completion_tokens": null,
        "cost_status": "unavailable",
        "code": "probe_inconclusive"
      }
    ],
    "results": [],
    "billing": {
      "kind": null
    }
  },
  "huggingface": {
    "outcome": "UNVERIFIED",
    "provider": "huggingface",
    "code": "held",
    "inference_sends": 1,
    "qualification": [
      {
        "provider": "huggingface",
        "stream": false,
        "status": 402,
        "passed": false,
        "completion_tokens": null,
        "cost_status": "unavailable",
        "code": "upstream_http_error"
      }
    ],
    "results": [],
    "billing": {
      "kind": "billing_access_unverified",
      "latched": false,
      "observed_at": "2026-10-23T11:33:29.746434+00:00",
      "retry_in_seconds": 59.595
    }
  }
}
```

### Post-live compatibility fix and evidence limits

Reviewing Mistral inconclusive responses exposed a definite existing adapter bug: valid text responses carrying optional tool_calls=null or [] were rejected. The official [Mistral OpenAPI](https://docs.mistral.ai/openapi.yaml), AssistantMessage and DeltaMessage schemas, explicitly permit array/null; the [chat documentation](https://docs.mistral.ai/studio/conversations/chat-completion) also distinguishes string content from richer chunks. The adapter now permits null/empty absent calls while retaining validation of actual calls. Stream deltas permit null calls as well. No rich content-chunk normalization, new output modality or request option was added. Regression fixtures exercise nullable fields through actual isolated proxy sockets.

This source-supported bug fix is **not proof** that nullable fields caused the three actual Mistral failures: raw responses were intentionally not retained, and no response-shape diagnostic established that cause. No post-fix Mistral generation is claimed. Rich/nontext/unknown completion shapes remain excluded. A further live diagnostic needs a separately bounded allowance because the three-candidate packet is consumed. NVIDIA's exact underlying404 reason is also unknown beyond the actual HTTP result.

The live packet predates this narrow adapter fix. The preceding full candidate passed376 tests/12.51s; subsequent root runs passed378/12.40s and379/12.50s. Final independent full suite: **382 passed/12.44s**, with bytecode/pytest cache writes disabled by the reviewer. Additional tests cover cumulative SSE body bounds, two-global/one-credential concurrency and owned cancellation, absolute deadlines, and account-wide HF holds. No runtime source changed after this final independent run.

Live/final candidate SHA-256 manifest: every row except the adapter is identical. This distinguishes actual external proof from subsequent local protocol regression proof.

| Runtime path | Live SHA-256 | Final SHA-256 |
|---|---|---|
| `backend/app/config.py` | `be370c75e2ee0b61e1d3681dc170d505ed152bd4a24add6d0271bf6a6ea6fe8e` | `unchanged` |
| `backend/app/core/providers/models.py` | `5a99cdb6ccba552e1992a49c1c75979c424ef0e4737ddaad73356f2900e5d3e9` | `unchanged` |
| `backend/app/core/providers/providers.yaml` | `f4a851cd059a59f82e881267a7bb3613ddacbd2f363cfe227cc6b31c60b6d441` | `unchanged` |
| `backend/app/core/providers/registry.py` | `fcf8cc5a6c5b69af5f8e90df1876b534e146af10c5eed7e2068b243efb0b3826` | `unchanged` |
| `backend/app/core/discovery/orchestrator.py` | `c9862e94d38fe15598940bb1e68de84d7071ed0c8d18efa3c79b8ed411e92b37` | `unchanged` |
| `backend/app/core/eligibility/account.py` | `7f117b072b38e5cf2ab22b54777526ade6847e3a18d6afa30bc991d00436c437` | `unchanged` |
| `backend/app/core/eligibility/probes.py` | `b73efe378dc381eeb98ffea6770299011eb1764a3997638c462116ee600ba2d8` | `unchanged` |
| `backend/app/core/eligibility/protocol.py` | `e53dbc459523841c443d3919b3d1660932e7f0b0e2738f9b859942a8df1383f2` | `unchanged` |
| `backend/app/core/eligibility/evidence.py` | `eb7eb61f0ea742738f0cd0d863527019aa6c798f7cdc1becc75af5ce59ee553e` | `unchanged` |
| `backend/app/core/eligibility/billing.py` | `e48f51fe56aa4444953f4677dd04f9c4a7c814aad7d621ba7289d8f497c43473` | `unchanged` |
| `backend/app/core/adapters/openai_client.py` | `41a77c579407a569256a2d6c29903c21f591dd6d71c187c599fba1d8243c4dbe` | `331d96ea1d6c2c2d2c3b37b93ca8074b35a1a26dcfe989e6eae10c9169d76ce4` |
| `scripts/probe_multi_provider.py` | `62f69b49954d8b0491e7e6aab49fe193d3af7f62f28dd708bd08e1b6ff7d79be` | `unchanged` |

Final manifest capture: /tmp/t007-h13-final-candidate-hashes.json. Seven protected T-006 files and backend/app/main.py match the pre-implementation baseline, not merely clean HEAD. Application/record writes are within the approved MAY EDIT set; no router strategy, API module, aliases, telemetry schema/store, dependency, real environment or account mutation. Root test runs generated ignored .pytest_cache/bytecode outside the source edit set; no such files were treated as deliverables or reverted. Independent reviewer made no source edits and disabled those caches; authorized temporary socket resources only.

### AC evidence matrix

| AC | Evidence / status |
|---|---|
| H1 | Accepted OpenRouter pricing/closed-request/zero-cap/output/billing suites retained; new setting rejects OpenRouter. PASS locally. |
| H2 | test_account_eligibility strict parsing/default/legacy tests and pending-no-admission tests; no automatic key-only inference. PASS locally. |
| H3 | Observed-key restore/setting toggle, changed binding, source/capability/route replacement and in-flight cancellation tests; independent lifecycle review. PASS locally. |
| H4 | Dynamic catalogs, negative metadata, tool capability, HF rows and new route tests; no model list. PASS locally. |
| H5 | Private one-use mode permit, exact fixed payload and source/epoch/budget gates; pending routes never handed to router. Tests/review PASS. |
| H6 | Strict raw framing, late content, missing/repeated DONE, null/empty/reasoning/tool/media/token failures and both-mode requirement. PASS locally. |
| H7 | Separate source/availability clocks, source removal/capability changes, expiry and cap-safe cached recovery. Tests/review PASS. |
| H8 | Sliding partitions, renewal-vs-exploration, recreation-preserved quota, concurrency, body/deadline bounds and full-pool replacement. PASS locally. |
| H9 | Four-profile TCP capture includes pinned HF selectors; duplicate/provider conflicts and shared HF account hold tested. PASS locally. |
| H10 | Injected documented financial incident aborts pair; unrecognized cost stays unavailable; existing universal financial/output race regressions retained. PASS locally. |
| H11 | Fixed negative/backoff/retry outcomes, immediate failed-pass revocation and consumer-origin balance suspension; no background recovery. Tests/review PASS. |
| H12 | Accepted complete-delivery/pre-output fallback/post-output no-replay suites unchanged; four-profile ordinary TCP buffered/SSE. PASS locally. |
| H13 | Qualification emits no public request trace; existing memory-only listing/privacy suites retained; cancellation/owned cleanup tests. PASS locally. |
| H14 | Actual loopback TCP for all four source/inference profiles and ordinary routing, CLI TCP proxy plus existing real-socket cascade/guard regressions. PASS locally. |
| H15 | Final independent382 suite; seven protected T-006 plus main baseline hashes unchanged; edit scope reviewed. PASS locally. |
| H16 | README/default-empty example/explicit diagnostic flag disclose assurance, restart, billing path, unavailable charges and process-local budgets. Reviewed. |
| H17 | Packet executed within limits with honest outcomes above. Groq conditional delivery PASS on pre-nullability-fix candidate; NVIDIA/Mistral/HF delivery UNVERIFIED. This does not close mandatory NVIDIA delivery or full T-007/P2. |
| H18 | Final cumulative independent runtime/tests/evidence review clear; final records/link audit follows below. Owner result acceptance and primary activation remain pending. |

### Environment / release state

- Primary: existing accepted OpenRouter-only positive runtime remains PID37372, 127.0.0.1:8001; lsof capture /tmp/t007-h13-primary-listener.txt and process capture /tmp/t007-h13-primary-process.txt. No restart/reload or new primary generation. Account mode was not activated there.
- Local candidate defaults: FREE_ACCOUNT_CONFIRMATIONS=[]; four account profiles declared but no unconfirmed inference.
- Isolated live processes: exactly one named provider confirmation each, temporary only; processes exited, no service/setting persists. These were operator assertions, never account API certificates.
- Release decision: owner result acceptance and explicit primary account activation, naming provider IDs, are separate next actions. No commit/push/external deployment. Gemini/local provenance/gateways, T-008/T-009 and full P2 remain open.

### Final record audit and handoff

Independent final record review is clear: live observations/compact capture SHA values and code-hash tables match actual captures; all affected local links and paired markers resolve; git status and diff checks are clean of unintended source changes. The final independently tested candidate remains382 passed/12.44s; no runtime edit after that run. Seven T-006 files and main.py retain baseline hashes. Reviewer source writes/cache/authenticated-network/inference/.env inspection: NONE in the final audit. No new tests were run for this final documentation-only sync. Candidate is ready for owner result review; unresolved provider delivery remains explicit, and primary account activation is not performed.


## NVIDIA404 / post-fix Mistral follow-up — authorized 2026-10-23

Owner explicitly authorized investigation of NVIDIA404 and a new bounded32-token live packet for NVIDIA/Mistral after the nullable fix. Prior assertion/free-only and output/guard limits remain. Working ceiling: at most eight additional inference sends per provider (six qualification sends, then one ordinary buffered/SSE pair), no other providers; all sends/failed attempts/retries count, stop on financial hold or success. Read-only source inspection does not grant admission. Dynamic selection only, no manual IDs; no primary restart, .env/account changes or commit/push. Preserve seven T-006 files and main. Baseline /tmp/t007-h13-followup-before.json and /tmp/t007-h13-followup-status.txt. Improved safe structural/error diagnostics precede probes.


### Follow-up completed: exact NVIDIA error and post-fix Mistral delivery

The owner-authorized additional packet used **NVIDIA5 / Mistral4 inference sends**, nine total, each max_tokens=32 and auth_bound=true. Limits were eight additional sends/provider, with six qualification sends and two ordinary delivery sends reserved. No Groq/HF generation. No new primary configuration/restart, real .env/account/billing changes, external deployment, commit or push.

Mistral post-fix result is now **conditional PASS**: raw buffered/SSE qualification and ordinary real-socket proxy buffered/SSE all actual200, visible text, reported32 completion tokens each; ordinary modes one attempt each, SSE exactly one DONE. Buffered shape is string content with null tool_calls, now accepted. This proves the fixed candidate works on the actual account and validates nullability handling; it still does not recover the precise shape of earlier discarded responses. Monetary reporting remains unavailable, not a zero invoice. Checks stopped after success.

NVIDIA's diagnosed404 is a provider JSON error matching the fixed `function_not_found_for_account` pattern. It is not a generic missing local HTTP route. The owned client used the official HTTPS origin/path, bearer key and dynamically cataloged model selector. Actual error establishes that NVIDIA could not find/expose that inference function for this account/request; it does **not** distinguish missing entitlement, retired deployment, or a provider mapping fault. No proxy URL/price parameter can be claimed to repair the provider's function registry. Catalog200 is not a credential entitlement certificate.

| Additional NVIDIA attempt | Fresh catalog offset | Safe route fingerprint | Actual observation |
|---|---:|---|---|
| 1 | 0 | 539eb051501d26e9 | 404, function_not_found_for_account; repeats the first previously failing route for diagnosis |
| 2 | 9 | b54642966ca82cf8 | 404, same provider function/account error |
| 3 | 82 | 26f56e65693b0c6f | No HTTP status before the15s deadline; not mislabeled404 |
| 4 | 25 | 7c7236d102e8ee5e | 404, same provider function/account error |
| 5 | 42 | c0763fa1f0bd96f3 | No HTTP status before the15s deadline; not mislabeled404 |

No NVIDIA route passed qualification or ordinary delivery. NVIDIA remains **UNVERIFIED**, with no admission override. Three sends remain below the eight-send cap, but a complete qualification plus ordinary buffered/SSE proof needs four; no additional request was made merely to consume allowance. Timeouts did not prove a function was accessible, and no deadline/token/financial condition was weakened.

### Dynamic reference check; bounded interpretation

Read-only current catalog snapshot:84 IDs, only id/object/created/owned_by fields for the inspected rows. First three previously failing fingerprints still appear. The official [NVIDIA LLM API reference](https://docs.api.nvidia.com/nim/reference/llm-apis) specifies the exact integrate origin and POST /v1/chat/completions. A bounded read-only HTML-table parser selected rows whose endpoint description mentions chat/conversation, yielding50 reference IDs and13 exact intersections with the current84-ID catalog. This is a diagnostic candidate-selection aid, not a new production capability/eligibility source. The first three old candidates have no match in this parsed index; that absence does not prove retirement or incompatibility.

Offsets9/82/25/42 were selected from that freshly observed intersection; their actual outbound fingerprints match the source observation. No raw model-ID allowlist, saved model selector, guessed API path or manifest rewrite. Two current-reference matches still produced the same404, so absence from the index is not a complete explanation. The reference page can be incomplete or change; it does not establish account access or zero pricing. Evidence: /tmp/t007-h13-followup-nvidia-catalog.json and /tmp/t007-followup-nvidia-reference.json; bounded source script /tmp/t007_nv_reference_check.py.

Public NVIDIA-hosted forum reports describe similar function/account404 despite catalog access: [August report](https://forums.developer.nvidia.com/t/404-function-not-found-for-account-on-v1-chat-completions/381319), [October report](https://forums.developer.nvidia.com/t/request-api-key-public-access-getting-http-error-404/385259). These are user reports with no staff confirmation of this account's cause; their Public API Endpoints entitlement hypothesis is **not** recorded as a proven fix or authorization to alter account settings. Diagnosis of the underlying provider permission/deployment mapping requires NVIDIA-side account/service inspection. No message was sent to NVIDIA or anyone else.

### Scoped implementation and regression evidence

- Probe diagnostics now retain only fixed body/choice/message/content/call types, safe finish enums, visible-text presence and a bounded known-error code. No raw error text, prompts/answers, model/account/function IDs, headers or credentials. Monetary normalization/guards and normal delivery semantics unchanged.
- The recognized NVIDIA404 becomes the existing one-hour route-negative/incompatible result, invalidated by relevant scope/source change. It never creates a provider-wide financial/account hold and does not block a separately qualified route. This handles unavailable advertised functions without repeatedly retrying them every minute.
- CLI supports bounded candidate offset/limit and a lower send ceiling. All values are strictly checked before loading keys; remaining ceilings across this packet were8,7,6,5,4 for NVIDIA. Every failed/timeout send counts. Numeric positions are computed against fresh catalogs and do not confer eligibility.
- Root targeted41 tests passed1.49s; root full391 passed12.57s. Final independent full suite: **391 passed12.60s**, with bytecode/pytest cache disabled by the reviewer. Independent code/capture review found no material issue. Seven T-006 files and main.py match the follow-up baseline. No runtime edit after this independent run. Mistral's successful live capture preceded only the subsequent NVIDIA-specific negative-cache addition and diagnostic reason counts; its successful adapter/request/admission path was unchanged. Final cumulative tests cover that local final candidate; no redundant Mistral generation followed success.

Raw safe captures and checksums:

- `/tmp/t007-followup-nvidia_nim-1.jsonl` SHA-256 `2f8b175f16a78cb8da5508f93458940f25b20f4d81c5c9f6f06ae32c9a320569`; 1 sends, UNVERIFIED.
- `/tmp/t007-followup-nvidia_nim-2.jsonl` SHA-256 `818625a513923dc27a60c64991b51f13b1fddf84308fd8137c701cc5788e4568`; 1 sends, UNVERIFIED.
- `/tmp/t007-followup-nvidia_nim-3.jsonl` SHA-256 `eef991e22e6f25a1fd4eca348673e562f994d6eb94c41e1703d5a6f133508858`; 1 sends, UNVERIFIED.
- `/tmp/t007-followup-nvidia_nim-4.jsonl` SHA-256 `f4625f98f5ed9fc9f4bcfb0ec52ca784cd1feb0061e21c1a286c79bc4b90bc58`; 1 sends, UNVERIFIED.
- `/tmp/t007-followup-nvidia_nim-5.jsonl` SHA-256 `f589e956f4e241ba3a818c87fbe91693fa0579c29c818053e721fa5c71457aef`; 1 sends, UNVERIFIED.
- `/tmp/t007-followup-mistral-1.jsonl` SHA-256 `1f93661786897d08f25aa99d9d5bc86e54c358415d9da2c882981ee9cb94f0de`; 4 sends, PASS.

Persisted compact capture observations:

```json
{
  "nvidia_nim": [
    {
      "outcome": "UNVERIFIED",
      "provider": "nvidia_nim",
      "inference_sends": 1,
      "candidate_offset": 0,
      "send_limit": 8,
      "qualification": [
        {
          "provider": "nvidia_nim",
          "stream": false,
          "status": 404,
          "passed": false,
          "completion_tokens": null,
          "cost_status": "unavailable",
          "code": "upstream_http_error",
          "diagnostics": {
            "body_kind": "object",
            "error_kind": "null",
            "choices_kind": "null",
            "usage_kind": "null",
            "error_contract": "function_not_found_for_account"
          }
        }
      ],
      "results": [],
      "billing": {
        "kind": null
      }
    },
    {
      "outcome": "UNVERIFIED",
      "provider": "nvidia_nim",
      "inference_sends": 1,
      "candidate_offset": 9,
      "send_limit": 7,
      "qualification": [
        {
          "provider": "nvidia_nim",
          "stream": false,
          "status": 404,
          "passed": false,
          "completion_tokens": null,
          "cost_status": "unavailable",
          "code": "upstream_http_error",
          "diagnostics": {
            "body_kind": "object",
            "error_kind": "null",
            "choices_kind": "null",
            "usage_kind": "null",
            "error_contract": "function_not_found_for_account"
          }
        }
      ],
      "results": [],
      "billing": {
        "kind": null
      }
    },
    {
      "outcome": "UNVERIFIED",
      "provider": "nvidia_nim",
      "inference_sends": 1,
      "candidate_offset": 82,
      "send_limit": 6,
      "qualification": [
        {
          "provider": "nvidia_nim",
          "stream": false,
          "status": null,
          "passed": false,
          "completion_tokens": null,
          "cost_status": "unavailable",
          "code": "probe_inconclusive",
          "diagnostics": {}
        }
      ],
      "results": [],
      "billing": {
        "kind": null
      }
    },
    {
      "outcome": "UNVERIFIED",
      "provider": "nvidia_nim",
      "inference_sends": 1,
      "candidate_offset": 25,
      "send_limit": 5,
      "qualification": [
        {
          "provider": "nvidia_nim",
          "stream": false,
          "status": 404,
          "passed": false,
          "completion_tokens": null,
          "cost_status": "unavailable",
          "code": "upstream_http_error",
          "diagnostics": {
            "body_kind": "object",
            "error_kind": "null",
            "choices_kind": "null",
            "usage_kind": "null",
            "error_contract": "function_not_found_for_account"
          }
        }
      ],
      "results": [],
      "billing": {
        "kind": null
      }
    },
    {
      "outcome": "UNVERIFIED",
      "provider": "nvidia_nim",
      "inference_sends": 1,
      "candidate_offset": 42,
      "send_limit": 4,
      "qualification": [
        {
          "provider": "nvidia_nim",
          "stream": false,
          "status": null,
          "passed": false,
          "completion_tokens": null,
          "cost_status": "unavailable",
          "code": "probe_inconclusive",
          "diagnostics": {}
        }
      ],
      "results": [],
      "billing": {
        "kind": null
      }
    }
  ],
  "mistral": [
    {
      "outcome": "PASS",
      "provider": "mistral",
      "inference_sends": 4,
      "candidate_offset": 0,
      "send_limit": 8,
      "qualification": [
        {
          "provider": "mistral",
          "stream": false,
          "status": 200,
          "passed": true,
          "completion_tokens": 32,
          "cost_status": "unavailable",
          "code": "available",
          "diagnostics": {
            "body_kind": "object",
            "error_kind": "null",
            "choices_kind": "array",
            "choices_count": 1,
            "finish_reason": "length",
            "message_kind": "object",
            "content_kind": "string",
            "tool_calls_kind": "null",
            "visible_text": true,
            "usage_kind": "object",
            "completion_tokens_kind": "integer"
          }
        },
        {
          "provider": "mistral",
          "stream": true,
          "status": 200,
          "passed": true,
          "completion_tokens": 32,
          "cost_status": "unavailable",
          "code": "available",
          "diagnostics": {}
        }
      ],
      "results": [
        {
          "stream": false,
          "http_status": 200,
          "passed": true,
          "visible_output": true,
          "completion_tokens": 32,
          "done_count": null,
          "attempt_count": 1,
          "cost_reporting": "unavailable",
          "assurance": "user_asserted"
        },
        {
          "stream": true,
          "http_status": 200,
          "passed": true,
          "visible_output": true,
          "completion_tokens": 32,
          "done_count": 1,
          "attempt_count": 1,
          "cost_reporting": "unavailable",
          "assurance": "user_asserted"
        }
      ],
      "billing": {
        "kind": null
      }
    }
  ]
}
```

Final runtime SHA-256 values (follow-up):

| Path | SHA-256 |
|---|---|
| `backend/app/config.py` | `be370c75e2ee0b61e1d3681dc170d505ed152bd4a24add6d0271bf6a6ea6fe8e` |
| `backend/app/core/providers/models.py` | `5a99cdb6ccba552e1992a49c1c75979c424ef0e4737ddaad73356f2900e5d3e9` |
| `backend/app/core/providers/providers.yaml` | `f4a851cd059a59f82e881267a7bb3613ddacbd2f363cfe227cc6b31c60b6d441` |
| `backend/app/core/providers/registry.py` | `fcf8cc5a6c5b69af5f8e90df1876b534e146af10c5eed7e2068b243efb0b3826` |
| `backend/app/core/discovery/orchestrator.py` | `c9862e94d38fe15598940bb1e68de84d7071ed0c8d18efa3c79b8ed411e92b37` |
| `backend/app/core/eligibility/account.py` | `2712ca4e46f1d0bb9d7a9839609231083addc6f27f302d046e67ea0961cfcafd` |
| `backend/app/core/eligibility/probes.py` | `8ae8211c8cac73505674c42f1348011043b13a7c553e9397fc29f56de8797b31` |
| `backend/app/core/eligibility/protocol.py` | `60060fc9f26066da93d61639db87567bed3db827c2f9c41b4db09b07435705b6` |
| `backend/app/core/eligibility/evidence.py` | `eb7eb61f0ea742738f0cd0d863527019aa6c798f7cdc1becc75af5ce59ee553e` |
| `backend/app/core/eligibility/billing.py` | `e48f51fe56aa4444953f4677dd04f9c4a7c814aad7d621ba7289d8f497c43473` |
| `backend/app/core/adapters/openai_client.py` | `2389a41eb79f6ab96f61067e8c55e2beca30088cf3a0150bbb664d5421eb9f8a` |
| `scripts/probe_multi_provider.py` | `fa6bca0853ccf0c4850eb0debf59f9df456649a2f7b80fbbd11d027dabaef9a4` |

Follow-up baseline /tmp/t007-h13-followup-before.json; final manifest /tmp/t007-followup-final-hashes.json. Edits are limited to protocol diagnostics, adapter diagnostic plumbing, account/worker route-negative handling, CLI, related tests, README and affected records. No protected/API/telemetry/dependency/alias/model-list/real-environment changes. Root tests generated ignored local caches; reviewer source/cache writes NONE, authorized temporary test sockets only.

Primary listener rechecked after probes: PID37372 at127.0.0.1:8001, /tmp/t007-followup-primary-listener.txt. Primary remains accepted OpenRouter-only positive runtime; new account mode is not activated there. Local candidate defaults FREE_ACCOUNT_CONFIRMATIONS=[]; isolated NVIDIA/Mistral assertions were ephemeral and their processes exited. Result acceptance and primary activation remain separate. Groq's earlier conditional PASS persists as historical proof; Mistral now has current post-fix conditional PASS. NVIDIA and HF delivery, Gemini/provenance/gateways and full T-007/P2 remain open. Final independent record audit follows below.

### Follow-up final independent record audit

Independent record review found no material contradiction: all compact capture observations and capture SHA values match actual files; reference counts50/13/84 remain bounded selection observations; provider causes are not overstated. All final runtime hashes and eight protected files (including main.py) match their captures/baselines. Local links, paired markers, status and diff checks pass. No new tests or network actions for the final documentation sync; reviewer write audit NONE. Final candidate remains391 independent tests/12.60s; primary activation and owner result acceptance remain separate.

### NVIDIA Free Endpoint coverage clarification (2026-10-23)

Read-only public source check: [NVIDIA Build Models](https://build.nvidia.com/models) currently shows43 Free Endpoints. This dynamic count describes models/endpoints, not independent providers, and includes reranking, embedding and protein models alongside chat models. The five follow-up probes selected routes from the generic API catalog plus the LLM reference; they did not exhaust or specifically select the current Free Endpoint filtered pool. No working NVIDIA route is confirmed by these captures, but they do not establish that every NVIDIA chat endpoint fails for this key. Fresh Free Endpoint chat-capability/exact-route discovery remains a recon direction; no new production eligibility source is implemented by this clarification. No inference, account mutation or primary restart was performed. Existing391-test evidence remains applicable to unchanged runtime code.

### Owner-authorized NVIDIA Free Endpoint discovery repair (2026-10-23, in progress)

Authorization: owner explicitly requested the current free chat list, necessary short32-token key-bound checks, working routes and a discovery repair while preserving all free constraints. This extends the prior completed follow-up; it does not activate the primary or authorize account/billing/.env changes. P2/T-007 and key-only dynamic discovery remain the purpose. No full-framework run is adopted; PROJECT-PROCESS.md controls.

Measured input: public NGC ENDPOINT search with label nim_type_preview, page0/pageSize100, returned43 total endpoints,17 playgroundtype_chat rows,11 with AVAILABLE=true and PREVIEW=true. Ten of these have an exact publisher/name match in the keyed84-ID catalog. The remaining available row has no exact API match; no slug/ID alias is guessed. This is source selection, not key-scoped free pricing or working-inference proof. Captures: /tmp/t007-nvidia-free-source.json, /tmp/t007-nvidia-current-api-catalog.json. The public gemma page and its embedded API example confirm the exact integrate.api.nvidia.com/v1/chat/completions route and publisher/name model ID for that row. Vendor labels are an observed public interface, not a stability guarantee.

Repair contract: intersect the complete bounded public Free Endpoint/chat/available/nondeprecated snapshot with exact IDs from the credential-bound API catalog. No arbitrary/provider-returned URLs or auth forwarding to NGC. Missing/partial/malformed/unavailable sources fail closed; refresh/removal revokes admission. Selection never admits a pending candidate or replaces the operator assertion and both-mode qualification. Existing response/deadline/minute/day/lease/guard limits and strict OpenRouter remain. Scope: discovery/nvidia.py, orchestrator fetch integration, account source metadata, relevant tests and affected T-007 records; all previous protected paths remain protected. Source implementation and local verification precede live qualification.

Bounded live plan for this grant: explore at most the current ten exact matched candidates, with no more than40 inference sends total (at most one32-token buffered/SSE qualification pair and one ordinary buffered/SSE proof per successful route), at most eight sends in any existing isolated CLI packet. Preserve production two qualification sends/provider/minute; separate CLI processes wait at least60s between packets so process recreation cannot accelerate that rate. Global new-qualification partition consumption is at most20 sends, below64; no other provider is probed in this repair. Stop on account/financial hold or auth revocation; no retries with weaker settings, longer deadline, larger token limit or model-specific prompt/options. Source rechecked before every qualification; missing candidates are skipped rather than rebound by saved IDs. All outputs metadata-only, primary untouched. Tests and actual live outcomes will be recorded below.

NVIDIA repair local verification: targeted61 tests/1.52s passed before the credential-isolation hardening; independent review found that injected AsyncClient defaults could merge auth/cookies/headers into public reads. Fixed both catalog reads to build explicit HTTP requests and use auth=None, with an injected-defaults regression. Post-fix targeted97 tests/2.48s and independent full411 tests/12.42s PASS; no remaining material code finding. Earlier test-collection typo was corrected; local socket checks required the authorized sandbox escalation, not test weakening. Public-source interface constants and schema fail closed. Existing eight protected file hashes match the scoped baseline; later YAML edit changes only the NVIDIA description, without model IDs or gates. No adapter/router/CLI/request/guard behavior change is part of this repair.

First live packet explored fresh offsets0..2 with only3 actual buffered sends: offsets0/2 reached15s no-status deadlines; offset1 returned HTTP200/visible text with8 reported completion tokens, but the second-mode permit was unavailable because two provider sends already occupied the minute window. No SSE request was sent for that partial pair and no lease was published. A later isolated one-candidate offset1 packet after the enforced pause completed qualification plus ordinary buffered/SSE delivery. This local reservation deferral is not an NVIDIA SSE failure. The bounded plan permits this justified repeat within the same40-send aggregate ceiling; no partial proof is reused for admission. Subsequent one-candidate packets preserve at least61s between packet completion and next start.

Current confirmed delivery routes include google/diffusiongemma-26b-a4b-it, meta/llama-3.2-11b-vision-instruct and nvidia/nemotron-3-ultra-550b-a55b, each with fresh source/assertion, raw buffered/SSE qualification and actual ordinary real-loopback proxy buffered/SSE PASS, visible text, one ordinary attempt and one SSE DONE. Each of their four sends requests max_tokens32; buffered usage8/8/30 respectively, SSE completion usage absent. Never report the request cap as actual missing usage. No recognized financial hold and no zero-cost assertion is inferred from missing cost reporting.

An additional route, nvidia/nemotron-3-nano-omni-30b-a3b-reasoning, passed both qualification modes and ordinary buffered delivery, but its ordinary SSE returned proxy503 without visible output. The retained metadata does not identify the upstream status or root cause, so full delivery remains UNVERIFIED, not a provider-failure or local-defect diagnosis. meta/muse-glimmer-30b returned HTTP200/length/32 reported completion tokens with null content, which is inconclusive under the unchanged visible-answer contract. Neither result justifies prompt adaptation, extra options, larger limits or silently claiming a full pass. Final complete packet counts and capture hashes belong in the dated snapshot and final audit below.

### NVIDIA repair final packet and checkpoint

All ten currently exact-matched Free Endpoint chat routes were exercised: three complete qualification+ordinary buffered/SSE delivery PASS; three15s no-status timeouts; threeHTTP200/length/null-content outcomes at32 reported completion tokens; one successful qualification/ordinary buffered but ordinarySSE503. Actual23 inference sends:15 qualification and8 ordinary proxy, every max_tokens32/auth_bound=true, within the40-send plan. No auth/financial hold, unrelated provider probe or weaker retry. Nine isolated packets completed; the runner exited normally. Later packets respected the61s inter-packet delay. Full exact IDs, source/capture SHA values and outcomes: [dated NVIDIA snapshot](T-007-nvidia-free-chat-check.md). No primary account activation.

Compact retained observations (all requests capped32; unavailable cost/user_asserted throughout):

```json
[
  {
    "candidate_offset": 0,
    "outcome": "UNVERIFIED",
    "sends": 3,
    "wire": [
      {
        "phase": "qualification",
        "stream": false,
        "fingerprint": "17567520b81b6487"
      },
      {
        "phase": "qualification",
        "stream": false,
        "fingerprint": "00de91117ce05b3b"
      },
      {
        "phase": "qualification",
        "stream": false,
        "fingerprint": "410fa9a7b0347bd0"
      }
    ],
    "qualification": [
      {
        "stream": false,
        "status": null,
        "passed": false,
        "code": "probe_inconclusive",
        "completion_tokens": null
      },
      {
        "stream": false,
        "status": 200,
        "passed": true,
        "code": "available",
        "completion_tokens": 8
      },
      {
        "stream": true,
        "status": null,
        "passed": false,
        "code": "permit_unavailable",
        "completion_tokens": null
      },
      {
        "stream": false,
        "status": null,
        "passed": false,
        "code": "probe_inconclusive",
        "completion_tokens": null
      }
    ],
    "ordinary": []
  },
  {
    "candidate_offset": 1,
    "outcome": "PASS",
    "sends": 4,
    "wire": [
      {
        "phase": "qualification",
        "stream": false,
        "fingerprint": "00de91117ce05b3b"
      },
      {
        "phase": "qualification",
        "stream": true,
        "fingerprint": "00de91117ce05b3b"
      },
      {
        "phase": "proxy",
        "stream": false,
        "fingerprint": "00de91117ce05b3b"
      },
      {
        "phase": "proxy",
        "stream": true,
        "fingerprint": "00de91117ce05b3b"
      }
    ],
    "qualification": [
      {
        "stream": false,
        "status": 200,
        "passed": true,
        "code": "available",
        "completion_tokens": 8
      },
      {
        "stream": true,
        "status": 200,
        "passed": true,
        "code": "available",
        "completion_tokens": null
      }
    ],
    "ordinary": [
      {
        "stream": false,
        "http_status": 200,
        "passed": true,
        "visible_output": true,
        "completion_tokens": 8,
        "done_count": null,
        "attempt_count": 1,
        "cost_reporting": "unavailable",
        "assurance": "user_asserted"
      },
      {
        "stream": true,
        "http_status": 200,
        "passed": true,
        "visible_output": true,
        "completion_tokens": null,
        "done_count": 1,
        "attempt_count": 1,
        "cost_reporting": "unavailable",
        "assurance": "user_asserted"
      }
    ]
  },
  {
    "candidate_offset": 3,
    "outcome": "PASS",
    "sends": 4,
    "wire": [
      {
        "phase": "qualification",
        "stream": false,
        "fingerprint": "96899a5ea5d4c8b8"
      },
      {
        "phase": "qualification",
        "stream": true,
        "fingerprint": "96899a5ea5d4c8b8"
      },
      {
        "phase": "proxy",
        "stream": false,
        "fingerprint": "96899a5ea5d4c8b8"
      },
      {
        "phase": "proxy",
        "stream": true,
        "fingerprint": "96899a5ea5d4c8b8"
      }
    ],
    "qualification": [
      {
        "stream": false,
        "status": 200,
        "passed": true,
        "code": "available",
        "completion_tokens": 8
      },
      {
        "stream": true,
        "status": 200,
        "passed": true,
        "code": "available",
        "completion_tokens": null
      }
    ],
    "ordinary": [
      {
        "stream": false,
        "http_status": 200,
        "passed": true,
        "visible_output": true,
        "completion_tokens": 8,
        "done_count": null,
        "attempt_count": 1,
        "cost_reporting": "unavailable",
        "assurance": "user_asserted"
      },
      {
        "stream": true,
        "http_status": 200,
        "passed": true,
        "visible_output": true,
        "completion_tokens": null,
        "done_count": 1,
        "attempt_count": 1,
        "cost_reporting": "unavailable",
        "assurance": "user_asserted"
      }
    ]
  },
  {
    "candidate_offset": 4,
    "outcome": "UNVERIFIED",
    "sends": 1,
    "wire": [
      {
        "phase": "qualification",
        "stream": false,
        "fingerprint": "ed29abbe146ddb50"
      }
    ],
    "qualification": [
      {
        "stream": false,
        "status": null,
        "passed": false,
        "code": "probe_inconclusive",
        "completion_tokens": null
      }
    ],
    "ordinary": []
  },
  {
    "candidate_offset": 5,
    "outcome": "UNVERIFIED",
    "sends": 1,
    "wire": [
      {
        "phase": "qualification",
        "stream": false,
        "fingerprint": "bf7f21a45c57e0f7"
      }
    ],
    "qualification": [
      {
        "stream": false,
        "status": 200,
        "passed": false,
        "code": "probe_inconclusive",
        "completion_tokens": 32
      }
    ],
    "ordinary": []
  },
  {
    "candidate_offset": 6,
    "outcome": "UNVERIFIED",
    "sends": 4,
    "wire": [
      {
        "phase": "qualification",
        "stream": false,
        "fingerprint": "0959cf6545aa26e5"
      },
      {
        "phase": "qualification",
        "stream": true,
        "fingerprint": "0959cf6545aa26e5"
      },
      {
        "phase": "proxy",
        "stream": false,
        "fingerprint": "0959cf6545aa26e5"
      },
      {
        "phase": "proxy",
        "stream": true,
        "fingerprint": "0959cf6545aa26e5"
      }
    ],
    "qualification": [
      {
        "stream": false,
        "status": 200,
        "passed": true,
        "code": "available",
        "completion_tokens": 25
      },
      {
        "stream": true,
        "status": 200,
        "passed": true,
        "code": "available",
        "completion_tokens": null
      }
    ],
    "ordinary": [
      {
        "stream": false,
        "http_status": 200,
        "passed": true,
        "visible_output": true,
        "completion_tokens": 24,
        "done_count": null,
        "attempt_count": 1,
        "cost_reporting": "unavailable",
        "assurance": "user_asserted"
      },
      {
        "stream": true,
        "http_status": 503,
        "passed": false,
        "visible_output": false,
        "completion_tokens": null,
        "done_count": 0,
        "attempt_count": 1,
        "cost_reporting": "unavailable",
        "assurance": "user_asserted"
      }
    ]
  },
  {
    "candidate_offset": 7,
    "outcome": "PASS",
    "sends": 4,
    "wire": [
      {
        "phase": "qualification",
        "stream": false,
        "fingerprint": "ad7decc9ae94df12"
      },
      {
        "phase": "qualification",
        "stream": true,
        "fingerprint": "ad7decc9ae94df12"
      },
      {
        "phase": "proxy",
        "stream": false,
        "fingerprint": "ad7decc9ae94df12"
      },
      {
        "phase": "proxy",
        "stream": true,
        "fingerprint": "ad7decc9ae94df12"
      }
    ],
    "qualification": [
      {
        "stream": false,
        "status": 200,
        "passed": true,
        "code": "available",
        "completion_tokens": 24
      },
      {
        "stream": true,
        "status": 200,
        "passed": true,
        "code": "available",
        "completion_tokens": null
      }
    ],
    "ordinary": [
      {
        "stream": false,
        "http_status": 200,
        "passed": true,
        "visible_output": true,
        "completion_tokens": 30,
        "done_count": null,
        "attempt_count": 1,
        "cost_reporting": "unavailable",
        "assurance": "user_asserted"
      },
      {
        "stream": true,
        "http_status": 200,
        "passed": true,
        "visible_output": true,
        "completion_tokens": null,
        "done_count": 1,
        "attempt_count": 1,
        "cost_reporting": "unavailable",
        "assurance": "user_asserted"
      }
    ]
  },
  {
    "candidate_offset": 8,
    "outcome": "UNVERIFIED",
    "sends": 1,
    "wire": [
      {
        "phase": "qualification",
        "stream": false,
        "fingerprint": "57b7e204b183bff6"
      }
    ],
    "qualification": [
      {
        "stream": false,
        "status": 200,
        "passed": false,
        "code": "probe_inconclusive",
        "completion_tokens": 32
      }
    ],
    "ordinary": []
  },
  {
    "candidate_offset": 9,
    "outcome": "UNVERIFIED",
    "sends": 1,
    "wire": [
      {
        "phase": "qualification",
        "stream": false,
        "fingerprint": "a741d960ae90c248"
      }
    ],
    "qualification": [
      {
        "stream": false,
        "status": 200,
        "passed": false,
        "code": "probe_inconclusive",
        "completion_tokens": 32
      }
    ],
    "ordinary": []
  }
]
```

Final scoped runtime/test SHA-256 values:

| Path | SHA-256 |
|---|---|
| `backend/app/core/discovery/nvidia.py` | `53e114d4944503817064b5487fa2aa8bcba832b1f6435db856800c916a5ed4a2` |
| `backend/app/core/discovery/orchestrator.py` | `78825ac74622b426e01e254eb44fcdc5e8c7f6cf99f6b5c54262843ff242f259` |
| `backend/app/core/eligibility/account.py` | `6cda695e6bef6d84e8644e43c89c2b474fdbe91bc2067c005c20b616068e3042` |
| `backend/app/core/providers/providers.yaml` | `22b45e06d258b5d2c32ddec0beb94e1757671050f0b587a5aa18b52f064aa40b` |
| `backend/tests/test_nvidia_discovery.py` | `317a89027d3124f01da0d69b607c148a1bd93dffbbf054af37eb9373bbec09a8` |
| `backend/tests/test_account_probes.py` | `52a010d91464800e2916d94cb3a51b299aebe6b4c85251e73da9e9d725763b4c` |

AC-H4/H7 now include public-source exact intersection, disappearance/failure revocation and no generic fallback; AC-H13 includes credential-free public fetches under injected client defaults. AC-H15 full independent411 tests/12.42s and protected8 hashes pass; AC-H16 documentation preserves conditional assurance/default off. AC-H17 original eight-send packet remains historical; the separately authorized repair proves current NVIDIA delivery within its own recorded bounds, without claiming HF or primary recovery. AC-H18 final record/capture review follows. Primary listener independently unchanged by read-only lsof: PID37372 on127.0.0.1:8001. No primary HTTP generation/restart/reload, account/.env mutation, commit/push or external deployment. Existing dirty state preserved; root ignored test caches reported. Result acceptance and primary account activation remain pending; full T-007/P2 and HF/Gemini/provenance/gateways/T-008/T-009 remain open.

### NVIDIA repair final independent audit

Read-only verifier confirmed the complete nine-packet ledger:23 sends (15 qualification/8 ordinary),10 distinct exact current-source routes,3 full PASS/3 timeout/3 null-content/1 partial SSE503; every send max_tokens32 and auth-bound, no holds. Inter-packet completion-to-next-assertion spacing was at least61.241s. All compact observations, capture SHA values, six final runtime/test hashes and eight protected files match. Ten affected records/68 local links, paired markers, status and diff-check pass. No material current-state contradiction or out-of-scope implementation write was found. Prior independent post-fix full suite411 passed/12.42s stands; no additional tests, network or writes were performed for this audit. Root's final documentation append changes no implementation or capture. Conditional NVIDIA delivery is verified; primary account mode remains inactive and result acceptance/activation separate. The repair is ready for owner review with the partial-route and unavailable-cost limitations retained.

## Accepted NVIDIA repair and primary account activation (2026-10-23, in progress)

The owner accepted the concrete discovery repair and explicitly authorized enabling Groq/NVIDIA/Mistral on the main backend, restarting it and checking buffered/SSE at32 tokens while retaining all free constraints. This supersedes the preceding no-activation/real.env restriction solely for that named local integration; no account/billing/key change, HF activation, commit/push or external deployment is included. Full T-007/P2 closure remains separate.

Read-only preflight confirmed the existing PID37372 command and project cwd at127.0.0.1:8001; port8000 was not touched. Only FREE_ACCOUNT_CONFIRMATIONS was added/updated in the ignored real.env to ["groq","nvidia_nim","mistral"]; every other environment-file entry was preserved and key presence checked without outputting values. The selected setting is also explicitly set in the launched process, matching that file. Shipped default/example remains[]; HF remains unconfirmed, OpenRouter strict. No runtime source edit is required. Baseline: /tmp/t007-activation-start-status.txt and /tmp/t007-activation-runtime-before.json; safe config report /tmp/t007-activation-config.json.

Old service received SIGTERM after command/cwd verification and exited; the same ordinary uvicorn command on127.0.0.1:8001 was started detached as PID1128 with warning/no-access logging. PID file /tmp/open-freebie-finder-main.pid and log /tmp/open-freebie-finder-main.log retained. Safe restart report /tmp/t007-activation-restart.json; lsof confirms new listener. Its normal lifespan owns fresh source polling and private qualification; no seeded IDs, fake leases or process-local isolated registry is used. Automatic probes retain the accepted32-token/minute/day/deadline/guard limits. Provider qualification starts cold after the intentional restart.

Primary checks use its public memory-only /v1/models pool to select unique-provider eligible canonical routes dynamically. Up to six consumer requests total, one buffered/SSE each for the three named providers, all max_tokens32; verify HTTP200/visible text/SSE oneDONE, request correlation, telemetry success, exactly one attempt belonging to the intended provider. A fallback answer from another provider is not a pass. No larger limit/alternate request profile or eligibility bypass. Polling the listing while qualification warms does not initiate inference. Captures /tmp/t007-primary-account-activation.jsonl and safe summary /tmp/t007-primary-account-activation.json. Actual outcomes and independent review follow below.

### Primary cold-start fairness defect and scoped repair

The first primary run confirmed four ordinary checks (Groq/Mistral buffered/SSE) but NVIDIA was not yet eligible. Its consumer checker was stopped after those four completed requests, without issuing an NVIDIA consumer request. Initial captures were preserved as /tmp/t007-primary-account-activation-initial.jsonl and .json, not overwritten. This observation prompted investigation; the waiting duration alone does not establish the cause.

A deterministic regression reproduced the root scheduling defect: ten manifest entries and60 one-second idle polls phase-lock the unconditional provider_cursor increment with minute-budget windows, repeatedly scheduling Groq/Mistral and starving the third account. Old code failed with launch order Groq,Mistral,Groq,Mistral. The root fix changes only probes.py scheduling cursor advancement: move it to the provider after the last actual task launch; idle/blocked polls leave it unchanged. The regression checks three windows and idle stability, expected Groq,Mistral,NVIDIA,Groq,Mistral,NVIDIA. No request budget, deadline, guard, pending-admission rule, model ordering/IDs, source contract or concurrency limit is weakened. This repairs the already-approved AC-H8 fairness contract within the owner's requested activation, without a new feature or approval gate. Root-only paths probes.py/test_account_probes.py; protected bytes unchanged. Fresh independent full QA and the authorized corrective primary restart follow before final delivery checks. The final checker will issue six new32-token ordinary requests; with the initial four, this activation session will have ten ordinary verification requests if all finish. Normal background qualification is separate and retains its fixed budgets; do not claim ten as the total upstream inference count.

Fairness fix gate: root targeted34 tests/1.11s and fresh independent full412 tests/12.67s PASS. Independent scope review confirms only probes.py/test_account_probes.py differ from the activation source baseline; protected7T-006+main unchanged, no budgets/guards/source/normal-router changes. The verified PID1128 exited, and the same command/cwd/three confirmations restarted as PID3119 on8001 to apply the fix. Current loaded-source manifest /tmp/t007-activation-final-runtime.json; safe restart report /tmp/t007-activation-restart.json, prior restart retained as -initial.json. The first immediate checker launch hit connection refusal on /health before readiness and sent no inference; readiness retry was added only to the temporary external checker, then it was relaunched against the established listener without another server restart. Final six consumer checks are in progress with fresh normal qualification; initial four remain separately captured. No process-budget reset is represented as a durable spend firewall or primary balance recovery.

### Primary activation completed

Final PID3119 passed allsix ordinary verification requests on the actual main backend: Groq/NVIDIA/Mistral buffered+SSE HTTP200/visible, exactly one target-provider attempt and correct request correlation; SSEoneDONE, every request max_tokens32. Observed completion tokens buffered/SSE Groq10/10, Mistral32/32, NVIDIA9/unavailable. NVIDIA appeared in the normal memory-only eligible listing at183.8s; the checker finished at185.9s, with one eligible route per named provider in that captured snapshot. These are observations, not fixed model-count/latency promises. Its normal source/private qualification, not seeded IDs or fake evidence, established admission.

The final six summary observations exactly match JSONL and were independently verified; initialfour remain separate. All57 current loaded-source hashes and eight protected files match. Current lsof confirms PID3119/8001/project cwd. No runtime edits followed fresh independent412 tests/12.67s; only affected records were synchronized. The primary and its normal bounded worker remain running, consumer checker exited. Active confirmations are exactly Groq/NVIDIA/Mistral in the ignored real.env and launched process; shipped default/example[] and unconfirmed HF unchanged. Strict OpenRouter/free-profile guards preserved. [Persistent primary evidence](T-007-primary-activation.md) retains full safe final summary and all capture hashes. Result acceptance/activation for this named repair is fulfilled by the owner's explicit grant plus live verification; full T-007/P2/HF/Gemini/provenance/gateways/T-008/T-009 remain open. No keys/other.env entries/provider-account billing changes, commit/push or external deployment. Final independent current-record audit follows.

### Primary activation final independent audit

Read-only final audit is clear: allsix primary delivery checks, three active confirmations, PID3119/8001 and the independently verified412-test checkpoint are consistent. Persistent summary, eight capture SHA values, all57 current loaded-source hashes and eight protected files match. Only scheduler/tests differ from activation baseline. Defaults, user_asserted/unavailable-cost qualification and separate accounting of ordinary checks/background probes are stated correctly. Fifteen reviewed documents/125 local links, paired markers, status and diff-check pass. No new tests, HTTP/inference, real.env inspection or writes by the reviewer; write audit NONE. Root's final record-only append changes no runtime or capture. The requested local activation is complete; full T-007/P2 remains open.

### Owner checkpoint acknowledgment and next-step planning (2026-10-23)

After the verified primary integration, the owner acknowledged that most of the current work is sufficiently closed to move forward and requested documentation synchronization and consideration of next steps. Record acceptance of the operational checkpoint, not blanket T-007/P2 closure or permission for a new implementation. TASKS stale PID/pending-activation wording and ARCHITECTURE target/as-built labeling are corrected; current proofs remain the six primary PASS checks and independent412-test checkpoint. [Planning comparison](next-steps-current-checkpoint.md) recommends preparing T-009 before T-008, then P3 under unchanged phase dependencies; independent read-only assessment agrees. Remaining provider/provenance obligations are preserved. This documentation pass does not restart the primary, edit configuration, inspect secrets, run a new test suite or initiate manual inference. Normal background qualification remains running under its existing grant. No commit/push or external deployment.

Independent documentation audit is clear: seven affected records/52 local links, markers, status and diff-check pass; all57 runtime hashes remain unchanged. Preserved six primary PASS and412-test evidence are correctly labeled as retained verification. The recommended T-009/T-008/P3 sequence is explicitly a proposal, with no new implementation grant or blanket phase closure. Reviewer writes/tests/network/secret-file inspection NONE.
