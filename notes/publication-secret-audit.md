# Local publication secret audit

Date: 2026-10-24. Baseline: `a4acada74a55582a6ae56fef1ed7aab4e20586a1` on main, clean working tree. Scope: secret-exposure assessment only; no publication, remote configuration, restart or provider inference.

## Checks and observed result

- Official Gitleaks v8.30.1 Darwin/arm64 executable downloaded under/tmp; archive SHA256 matched the release checksum. No repository content was uploaded. Used built-in rules,100% report redaction and ignore-gitleaks-allow so inline allow comments could not suppress findings.
- Scanned reachable Git history with --all, a snapshot of all tracked files, and every reachable blob, including blobs referenced by the two auxiliary Codex tree refs. Baseline inventory:19 reachable commits and211 blobs. Separately scanned all reachable commit messages/metadata: zero findings.
- Gitleaks returned one generic-api-key finding in each of the three content scans, all referring to the same test-table row at notes/T-009-results.md line54. Independent verification of current/committed content and blob confirmed that this is ordinary test-result prose, not a token. No ignore rule or source alteration was added to conceal it.
- In-memory comparison against current local credential values found zero matching reachable blobs. Reports never printed credential values. Earlier precommit comparison also found zero matches in candidate files.
- .env is ignored and untracked. Tracked files and reachable path inventory contain no private environment file, private-key container, credential-store file or recovery bundle. No caches/runtime outputs were committed. Working tree was clean before this audit record.
- Independent read-only verifier confirmed counts, false-positive disposition, exact-key report, refs coverage, ignored environment file and clean status; wrote no files and did not read local secrets.

Local redacted evidence: /tmp/off-publication-secret-audit/{history,tracked,blobs,metadata,exact-key-comparison}.json and associated scanner logs. Temporary evidence may expire; this note preserves the scope/outcome. An independent scanner warning is not represented as an automatically clean scan: the one finding was manually and independently adjudicated.

## Conclusion and limits

No real secret was detected in the checked tracked content or reachable publication history. There is no identified secret-related blocker to publishing the ordinary main branch at this checkpoint. This is a bounded scan result, not an absolute absence guarantee, a full security review or permission to publish.

Unreachable objects, reflogs and private files outside Git were not included. The private history-recovery bundle remains outside the repository and must not be published. Publish a normal branch through Git, not an archive of the entire local workspace/.git directory or a backup bundle. Old historical/private local objects are not certified by this audit. Re-run secret checks when adding new files, keys or commits. T-010 approval/activation and all existing free-only gates remain unchanged.
