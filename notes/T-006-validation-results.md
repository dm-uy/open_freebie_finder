# T-006 Provider Validation — Verification Results

- Date: 2026-10-22. Phase P2 / batch B-002.
- Contract: [T-006 v1.0.1](../specs/T-006-provider-validation-api.md), explicitly owner-approved for implementation in chat on 2026-10-22 under the lightweight PROJECT-PROCESS.
- Baseline: `main`, HEAD `6d49e2a174a111dc0a5bb8745530a97d0e9786da`; implementation is an uncommitted working-tree candidate identified by SHA-256 below. Pre-existing documentation edits were retained.
- Result: implementation and required probes completed; owner accepted the result in chat on 2026-10-22. No commit, push, external deployment or key persistence performed.

## Implementation

New isolated validation service and request/report schemas, admin provider router, reproducible probe and behavioral/real-socket tests. The service performs ordered configuration/catalog/completion checks with request-local credentials and fixed safe diagnostics. It never uses the cascade/discovery write paths. API mounting is through the existing admin aggregation module; protected existing runtime files are unchanged.

## Final automated verification

Command (outside the filesystem/network sandbox so fixture-owned loopback servers may bind):

```bash
.venv/bin/pytest backend/tests -q
```

Exit 0. Saved command stdout:

```text
........................................................................ [ 54%]
...........................................................              [100%]
131 passed in 1.63s
```

The original 37 baseline scenarios remain unchanged. The final suite includes 92 new behavioral/adversarial cases and two real loopback socket cases. Counts are observations of this candidate, not future acceptance quotas.

## Final live OpenRouter verification (AC-12)

Started the actual app with:

```bash
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --log-level warning --no-access-log
```

Executed the exact documented direct-file probe, exit 0:

```bash
.venv/bin/python scripts/probe_provider_validation.py --base-url http://127.0.0.1:8000 --provider-id openrouter
```

Saved sanitized stdout (no keys, model IDs, upstream bodies or generated text):

```json
{"valid": true, "eligible_model_count": 20, "total_duration_ms": 1376.25, "checks": [{"name": "configuration", "status": "passed", "code": null, "http_status": null, "duration_ms": 0.12}, {"name": "catalog", "status": "passed", "code": null, "http_status": 200, "duration_ms": 275.62}, {"name": "completion", "status": "passed", "code": null, "http_status": 200, "duration_ms": 1097.29}]}
```

The server used the existing local provider configuration. Catalog and completion were real OpenRouter HTTPS calls, not mocks. The fixture-owned local uvicorn process was stopped after verification. A prior live probe also passed; the output above is the final candidate verification after the regex fix. Background discovery may legitimately update its own production registry; the validation operation itself does not mutate it, as separately checked with isolated state snapshots.

## Acceptance evidence

| AC | Result | Evidence |
|---|---|---|
| AC-1 | PASS | Final full suite above; original test files unchanged; path audit against approved MAY EDIT. |
| AC-2 | PASS | `test_endpoint_success_permissive_master_and_unknown`, `test_redacted_input_errors`, `test_registered_disabled_override_and_exact_request`: both selectors, disabled providers, rejected inputs, unknown provider. |
| AC-3 | PASS | `test_auth_before_parsing_lookup_or_network`: malformed unauthorized JSON returns 401 before service construction; correct master and unset master covered by endpoint success tests. |
| AC-4 | PASS | `test_catalog_rules`, `test_catalog_failure_shapes`, `test_explicit_model_membership`, configuration matrix: four discovery rules, zero pricing, literal ID field, dedup/order, malformed entries, invalid/overflow regex, manual without GET, model mismatch. |
| AC-5 | PASS | Exact request assertion and `test_inline_key_and_completion_url`; `test_completion_protocol` and invalid JSON cases verify response shape without synthesized fields. |
| AC-6 | PASS | HTTP/error matrix across catalog and completion; malformed/oversize bodies, transport failures, stage deadline, total deadline under trickle, cancellation and normal/error closure tests. |
| AC-7 | PASS | Concurrent distinct overrides and failed request; environment/settings/registry/models/cooldowns/telemetry/local-config snapshots unchanged; registered Settings fallback and inline no-saved-key test. |
| AC-8 | PASS | Configuration matrix verifies URL/header/origin guards before I/O. Redirect response produces no second destination request; real loopback case succeeds with invalid ambient proxy settings and local HTTP. |
| AC-9 | PASS | Redacted input/auth/lookup errors; body/exception sentinels, hostile metadata, reflected secret IDs, redacted provider ID; DEBUG library logging is suppressed in validation context and ordinary logging remains visible. |
| AC-10 | PASS | Model-count/list-bound test; real socket `test_health_progress_while_validation_waits` observes health completion while upstream catalog remains blocked; monotonic timings nonnegative. |
| AC-11 | PASS | `backend/tests/test_provider_validation_live.py`: actual app and upstream loopback sockets on ephemeral ports, success and upstream 429, non-mutating state, concurrent health. No external discovery in fixture-owned app. |
| AC-12 | PASS | Final real uvicorn/OpenRouter probe stdout above: valid=true, both remote stages HTTP 200. |

## Independent QA and fixes

A read-only independent reviewer examined implementation and tests against the approved contract. Found one material defect: Python regex compilation can raise OverflowError for a short excessive repeat count. Fixed the root cause by treating regex compilation errors, overflow and recursion as invalid_configuration before network I/O; added `a{4294967296}` regression. Final full suite and external probe rerun after the fix. Reviewer rechecked the fix and reported no remaining material defects. Reviewer made no file changes; final record/evidence verification follows separately.

Final independent evidence verification matched all seven candidate hashes and both saved stdout captures, confirmed links and the 14 changed task/preparation paths. Corrected one stale TASKS sentence that still described preparation-only scope. No runtime findings remained. Local documentation link/marker checks and `git diff --check` passed.

## Failed attempts and limitations

- First real-socket test run inside the sandbox failed to bind loopback (`PermissionError: Operation not permitted`). Reran the actual full suite outside the sandbox with tool approval; socket tests passed. This was an environment restriction, not a mock substitute.
- Initial test collection referred to a nonexistent router factory. Corrected the test to use the actual `CascadeRouter` constructor before further runs; production contracts were unchanged.
- Historical P1 real upstream 429 remains unverified. T-006's loopback 429 is controlled local evidence, not a claim that OpenRouter rate limits were reached.
- All-available discovery and one passing micro-completion do not establish zero pricing, broad provider compatibility, future quota, generated-answer quality or durable availability.
- Trusted operator regexes and local HTTP destinations retain the approved risk boundary; full regex isolation and DNS/SSRF policy are outside this contract.
- Feature gates: no new flags. Validation is mounted in the local application, protected by existing optional master-key policy; no remote environment deployment occurred and no gated change is being held back.
- Deviations from approved BR/AC/scope: none. Shared runtime adapters, registry/schema, discovery, balancer, telemetry, configuration, main.py and dependency files untouched.

## Candidate identity

SHA-256 of the delivered runtime/tool/test files (documentation changes do not alter these hashes):

| Path | SHA-256 |
|---|---|
| `backend/app/api/admin/__init__.py` | `62592e17c167f1dd09fe86b4a243b3bcd5920d7226e3b5ee1b2b8780a4e78c1d` |
| `backend/app/api/admin/providers.py` | `d600bbe5f82ed45a137df83a3ca572c07cc2b98b5caa1be1d371f292c6c51960` |
| `backend/app/core/providers/validation.py` | `5a283b8ddc62cee30f12905f7ed8053084a5263fa75b965978b3d242fe24825d` |
| `backend/app/core/providers/validation_models.py` | `8801a260047f2ee904d58929881b4c2034cbfc3a27fd89f4ef614938220423e7` |
| `backend/tests/test_provider_validation.py` | `64c9b856fa1b19dc3681b978e3306ccc940f0cb37e96ffe90a9d5c8904822d35` |
| `backend/tests/test_provider_validation_live.py` | `e43260d6554ce4172ddc980522e451523f532c135659c111852e4d795a1d513c` |
| `scripts/probe_provider_validation.py` | `55283a8ed6efe71863fe5d730027a2741a5d233ce803d88119ca013e9954d431` |
