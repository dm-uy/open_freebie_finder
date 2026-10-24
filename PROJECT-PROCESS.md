# Harness Instructions: File-Based Project Management

Maintain the project's high-level state so that another agent can continue without the chat history. These instructions are self-contained: no plugins, engines or Sombrero source code are required. They define a lightweight documentation process, not the framework's full internal software-development cycle.

Apply them within the owner's request and the project's rules. Receiving these instructions alone does not authorize changes to other projects, implementation, commits or deployment. Existing approved decisions and constraints remain in force.

## 1. Quick Start for Every Session

1. Read `AGENTS.md`, then the documents at the paths it specifies. The default order is `VISION.md` → `ROADMAP.md` → `HANDOFF.md` → `TASKS.md`, followed by `ARCHITECTURE.md` and the decisions, specifications and notes relevant to the task.
2. Check the actual state: branch, HEAD and staged/unstaged/untracked files; for example, `git status --short --untracked-files=all`, `git branch --show-current`, `git rev-parse HEAD`. If Git is absent, record that; do not initialize it automatically.
3. Recover why the project exists, its active phase and task, existing authorization, what has been verified, what blocks progress and the next permitted step. Compare the records with the actual artifacts.
4. Find the owner's earlier answers relevant to this work. Explicit approval of the same scope remains valid; ask again only for a missing or changed decision.
5. Continue unfinished authorized work. If records contradict code or each other, record the discrepancy and check the source. Do not silently choose the convenient version.

A missing preferred filename does not make an existing project new. First find equivalent documents, README, code and earlier decisions. If asked to establish project management, fill actual gaps only. For a status request, read and answer without rewriting records.

## 2. Documentation Map: One Role, One Home

The paths below are defaults. Preserve existing names and locations and identify them in `AGENTS.md`. If the project uses `TASK.md`, it serves the role of `TASKS.md`; do not create a second active task register.

| File / location | What it contains | When to update |
|---|---|---|
| `AGENTS.md` | Brief operating rules, document map, reading order, record owners, verification commands and prohibitions | When rules, paths or responsibilities change with approval |
| `VISION.md` | Audience, value, goal and observable success criterion, scope, constraints and deliberate deferrals | When goals, audience or constraints change |
| `ARCHITECTURE.md` | Components and responsibilities, interfaces, data flows, storage, external dependencies, invariants and launch arrangement | When the system's structure changes through verification or approval |
| `ROADMAP.md` | Phases with outcomes, dependencies and completion criteria; current focus | At phase start/completion, dependency changes or approved replanning |
| `TASKS.md` | Current task or bounded batch: authorized scope, executors, statuses, checks and results | During planning, authorization, start, blocking events and significant results |
| `HANDOFF.md` | Actual continuation state: blockers, latest verification, next permitted step and traps | When continuation changes significantly and before ending/handing over a session |
| `docs/decisions/DEC-NNN.md` | A durable decision: question, options, choice, rationale, authority and consequences | When a decision is adopted that future contributors must follow |
| `docs/recon/…md` | Measured reconnaissance of the existing state before a new specification | Before specifying a substantial change |
| `specs/…md` | Required change: requirements, boundaries, acceptance criteria and actual delivery verification | When preparing or making an approved change to a substantial task |
| `notes/…md` | Detailed results, evidence, errors, limitations and completed-batch history | When an event needs more detail than a short task entry |

The first five process roles—AGENTS, VISION, ROADMAP, TASKS and HANDOFF—form the core. Software projects also maintain architecture. Create other records as needed. Use `CONVENTIONS.md` when conventions no longer fit in a short AGENTS, and `OPEN_QUESTIONS.md` when many questions remain open. A small choice can stay in its task.

Project records live in Git as Markdown under the project's conventions. README explains the product and launch; AGENTS guides the working agent. Do not maintain parallel editable copies of the same state for another harness. If a harness reads a different entry file, put a short pointer to the shared rules there.

## 3. Minimum File Contents

These are outlines, not established facts. Fill them with actual information and mark unknowns explicitly. Inherit the project's language, metadata and statuses; absent a convention, write documents in English. Do not renumber stable IDs.

### AGENTS.md

```markdown
# Working on the Project
Goal and brief profile: …
Read at startup: … [actual paths in the adopted order]
Map: goal → …; architecture → …; phases → …; tasks → …;
handoff → …; decisions → …; evidence → …
Records and allowed write paths for each executor: …
Launch and verification commands: …
Constraints and actions requiring an owner decision: …
Rules: recover goal/task/authorization; link the task to its phase outcome;
distinguish planning, execution, verification and acceptance; update only
affected records; leave continuation independent of the chat history.
```

Read the existing AGENTS in full. Add missing rules only within authorized scope; preserve its original instructions and order rather than replacing it with a template.

### VISION.md

```markdown
# Vision
Audience and need: …
Goal and value: …
We have succeeded when: … [observable conditions]
Included in the project: …
Excluded: …
Hard constraints and their sources: …
Deferred: …; reason and return condition: …
```

VISION describes intent. It is not a current bug list or session report.

### ARCHITECTURE.md

```markdown
# Architecture
Scope and description status: … [as-built / proposal, revision]
Components and responsibilities: …
Entry points, interfaces and contracts: …
Main scenarios and data flows: …
Stores, schemas and external dependencies: …
Invariants, trust boundaries and material limitations: …
Launch, environments and configuration: … [no secret values]
Decisions and rationale: … [DEC links]
Known discrepancies and proposed changes: …
```

Separate verified structure from proposed design. Code and the actual schema are the sources for claims about the implementation; a diagram or description does not prove it exists. Record discrepancies with observations and how they were checked. Keep deep details in existing subsystem documents and link to them.

### ROADMAP.md

```markdown
# Roadmap
Goal: … [VISION link]
P1 — outcome: …; complete when: …; status: done; evidence: …
P2 — outcome: …; complete when: …; status: active ← current focus
P3 — outcome: …; depends on: P2; status: planned
Deferred: …; reason: …; return when: …
```

A phase is an achieved outcome, not an activity such as "work on the API." Close it only against its own criteria, including integration when required. Update any diagram together with the text; dependencies and statuses must agree. A backlog idea does not become authorized work merely by appearing on the roadmap.

### TASKS.md / TASK.md

```markdown
# Current Batch B-001
Phase: P2. Authorization: … [source, date, exact scope or pending]
## T-001 — Task outcome
- Status: todo / active / blocked / review / done / deferred / cancelled
- Why: … [link to P2 and product value]
- Deliverable and done when: …
- Allowed paths; executor: …
- Do not touch: …
- Inputs and dependencies: … [decisions, recon, specification]
- Execution approach and required checks: …
- Stop if: …
- Evidence: … [revision, command/output or results link]
- Next step / unblock condition: …
```

A single task does not need an artificial large batch. Before replacing the current batch, preserve its original scope, authorization and all outcomes in existing history/notes. Unfinished and cancelled tasks retain their IDs, reasons and disposition. `done` requires evidence against the criterion; separately record result acceptance and integration.

### HANDOFF.md

```markdown
# HANDOFF
## Blocked on the owner
Required decision, concrete question and link. Otherwise, "nothing."
## State
Active phase/task; completed work; result and evidence;
last verified revision; uncommitted files and their owners;
unverified items, failed attempts and open effects.
## Queue
Current batch/task; exact next permitted step;
entry command or path; what remains deferred and why.
## Traps
Material errors, environmental limitations, prohibitions and permitted
workarounds; links to details.
```

HANDOFF is short and current, not an accumulating transcript. Keep detailed history behind links. Do not delete failures or blockers to make the status look better.

## 4. From ROADMAP to a Feature Specification

The record chain is **VISION → ROADMAP phase → TASKS task → Input RECON → SPEC → verified result → TASKS/HANDOFF**. Include mutual links and the phase ID in the task/specification; update the roadmap after result acceptance. A phase may need several bounded specifications. Do not turn the entire ROADMAP into one enormous specification.

A specification is a portable outcome contract. It can be handed to a person, one agent or another engine. It requires no DevPlan, prescribed roles or Sombrero tools. First establish **what must result and what must remain intact**; the executor then chooses **how to implement it** within those boundaries. Pass the required stack, interfaces and adopted architectural decisions as constraints.

### Profile Selection and Preparation

- **BROWNFIELD** — changes an existing system, interface or artifact. Describe compatibility, preserved parts and exact allowed exceptions alongside the new behavior. Most roadmap features in an existing product belong here.
- **GREENFIELD** — the first implementation, with no existing behavior to preserve. Describe the first useful outcome, MVP, justified stack, boundaries and excluded capabilities. Here `BR-1` is verifiable MVP success. Do not invent a regression baseline.
- **MIXED** — a new component inside an existing system. Explicitly separate new parts from preserved existing consumer contracts. A new file alone does not make a feature greenfield.

Before drafting, read the original request, phase/task records and decisions; inspect actual data producers/consumers, code, tests and real schemas. Save dated Input RECON: baseline identity, sources/observations, original test baseline, contradictions and unverified items. Usually this is a separate `docs/recon/…md`; a clearly separated specification section is acceptable for a small bounded change. Do not mix measurements with promises about future behavior. An unavailable source leaves a gap, not permission to invent a fact.

### Required SPEC Contents

Use a stable path such as `specs/T-001-list-limit.md`; store status inside rather than renaming the file. At the beginning, identify ID, profile, status, version, phase/task, Input RECON and an actual authorization record or `pending`.

| Section | Required contents |
|---|---|
| PURPOSE / SCOPE / KEYWORDS | Audience and reason, subject boundaries and key concepts |
| Done when / Stop and ask when | Brief observable finish and concrete stop conditions |
| Context / Input RECON | Original request/decisions, verified current behavior, sources, revision and observation limits |
| What we add / build | Inputs, outputs, defaults, ranges, ordering, validation, errors, storage and lifecycle |
| Business Requirements | Unique `BR-N`; each is a standalone rule linked to its source. In brownfield, `BR-1` preserves existing contracts and regression baseline with exact allowed exceptions |
| Boundaries | Concrete Always do / Ask first / Never do, accounting for existing authorization |
| Stack / Dependencies | For greenfield: language, framework, storage, transport and dependencies with rationale and verified version constraints. For brownfield: existing stack and exact proposed changes, or "unchanged" |
| Expected Architecture | Existing relationships and the change's position; separate proposals from binding decisions. For greenfield: approved target graph or fixed constraints, leaving detailed design to the executor |
| Scope / MVP | `MAY EDIT`: paths and purpose of each change, including tests/docs. `DO NOT TOUCH`: protected paths/interfaces and reasons. For new products, also Included / Excluded / Deferred with return conditions |
| Acceptance Criteria | Unique `AC-N`: related BR, scenario/input, verification method, exact expected result and evidence. Cover behavior, errors, compatibility, scope boundaries and delivery |
| Delivery / Live Probe | Actual command/entry point, environment, permitted result location, prerequisites, steps, observable success/failure and output location |
| Risks / Deficiencies / Deviations | Specific risks; source-backed gaps/contradictions, affected BR/AC, permitted interpretation and rationale; unresolved questions and where implementation deviations will be recorded |

For a changing CLI/script, verify the documented command with a separate actual run. For a file processor, include a real artifact of the relevant family, not only synthetic data. For external delivery, read the result at the actual authorized recipient. If an LLM call changes, define protection against instructions in input data and a discriminating adversarial test; if a maintained code map applies, retain its freshness checks. Explain inapplicability with facts. A deferred check names command, prerequisite, reason and affected AC; until executed, that AC is not met.

### Document-Protocol Formatting

First write the complete document plan, then expand its bodies. Use ordinary Markdown headings for readability and paired markers for boundaries. At minimum, one `GOAL` artifact can contain the full feature contract; use `USE_CASE` for separate scenarios. This is document formatting and does not start an agent workflow.

```text
$START_DOCUMENT
PURPOSE: …
SCOPE: …
KEYWORDS: …
$START_DOCUMENT_PLAN
$DOCUMENT_PLAN
GOAL [Feature name] => GOAL_FEATURE
$END_DOCUMENT_PLAN
$START_SECTION_FEATURE
$START_ARTIFACT_GOAL_FEATURE
TYPE: GOAL
KEYWORDS: …
$START_CONTRACT
PURPOSE: …
DESCRIPTION: …
RATIONALE: …
ACCEPTANCE_CRITERIA: AC-1, AC-2, …
$END_CONTRACT
$START_BODY
[Full contents of all sections in the table above]
$END_BODY
$START_LINKS
IMPLEMENTS: (none)
IMPACTS: (none)
REQUIRES: (none)
$END_LINKS
$END_ARTIFACT_GOAL_FEATURE
$END_SECTION_FEATURE
$END_DOCUMENT
```

Plan/body IDs must match. `IMPLEMENTS` points to the goal/rule implemented; `IMPACTS` to an affected artifact; `REQUIRES` to a prerequisite. For an external relationship, name the document and actual ID; use `(none)` for an absent relationship. Each artifact contains TYPE, KEYWORDS, a contract, a substantive body and links. A `USE_CASE` DESCRIPTION uses "actor → action → goal." Do not introduce a new XML graph or registry solely for these relationships. If the project has approved its own format, preserve it with the same substantive contract.

### Handoff-Readiness Check

1. Every BR has a source; ACs cover all its parts, and every AC maps to a requirement or explicit constraint. Numbers, ranges, lists, defaults and links agree throughout the input. A `BR → AC → verification` table exposes gaps.
2. Required package names, versions, APIs and other external identifiers are checked against real interfaces/primary sources. Commands are identified as existing or as required future artifacts. An old test count is a dated observation, not a permanent quota.
3. Scope includes all necessary tests, documentation and related consumers. Do not call an observed architectural graph "frozen by the owner" without an actual decision. Document plan, bodies, IDs, paired markers and links agree.
4. No unresolved intent/scope question remains that would force the executor to choose for the owner. Such a question holds dependent implementation. Identify evidentiary gaps separately; do not disguise them as accepted assumptions.
5. Record actual approval of the exact version/scope or `pending`. An example, `status: approved` or an agent signature does not create approval. After approval, changing BR/AC/boundaries requires the corresponding decision, not silent editing. Pass all retained interpretations to the executor in full; list implementation deviations or `none` in the result.

A completed teaching example is [SPEC-EXAMPLE.md](SPEC-EXAMPLE.md). It contains its own teaching Input RECON and does not depend on other project files. Its names, behavior and "measurements" are fictional; copy the form, not facts or authorization. Keep both files together; this main document contains the full normative minimum and works without the example.

## 5. How Work Proceeds

**Ordinary task.** Link it to a phase and record its outcome, boundaries and existing authorization. Perform routine steps autonomously. Documentation and small local fixes need proportionate checks, not a separate software-development cycle.

**New feature or substantial fix.** Reconnaissance comes first, then specification. Recon identifies the question, revision, inspected code/data/decisions, results and unverified items. Read the real database schema before querying; do not call fixtures production data. The specification records original requirements, MAY EDIT / DO NOT TOUCH, acceptance criteria, regression constraints and the real result-verification entry point. Implementation requires explicit authorization for that scope; an already approved exact batch may cover it.

Organize implementation with the chosen harness's tools. The executor may be one person/agent, a human team or Architect / Code / QA / Debug / Review roles. These instructions do not require a separate DevPlan as input; an executor may prepare one under its own rules. Preserving the specification contract, necessary checks, honest distinction between self-check and independent review, and final BR/AC reconciliation are mandatory. If project rules require independence, its absence remains a blocker. Respect established retry limits; changing sessions does not reset failed attempts.

**Significant open choice.** Before choosing, retain real options, criteria, consequences and reasons for preference. For an important product/architectural decision, obtain independent proposals and separate assessment when the harness permits; missing required independence leaves the choice open. Record the decision-maker's authority, selected/rejected options and reconsideration trigger. Do not reopen routine, forced or settled decisions. A brief critical reread should challenge assumptions, counterexamples, cost and remaining risks.

**Two distinct owner decisions.** Authorization to implement a scope differs from acceptance of a concrete result before merge/publish/deploy. Record the owner's exact words, date, source, object and scope in the task/specification/DEC. Ask only for the missing decision, after preparing a reviewable artifact. Silence, timeout and someone else's "SUCCESS" are not approval. Commit, merge, push, installation and deployment have their own authority boundaries.

**Result verification.** Bind it to a specific revision or saved change, including new files. Save the command, observed result and limits. For a fix, show a check that catches the original defect when applicable. Update affected checks after implementation changes. Mocks do not prove delivery: verify an API with a real response, a file by reading the result, and deployment with a live check of the target environment. If no check ran, state `NOT RUN`/`UNVERIFIED` and why. Identify every withheld feature flag, its state per environment and the decision needed to enable it.

**Boundaries and failures.** Stop dependent work on scope overrun, rule/ownership conflict, unexplained verification failure or a missing significant decision. Record the blocker and continuation condition; continue independent authorized work. Fix an error's root cause within task scope; outside that scope, explain the boundary and leave the decision to the owner. Before repeating an operation with an unknown outcome, check whether it already succeeded.

## 6. When to Update Records

- At the start of authorized work, align TASKS, ROADMAP's current focus and HANDOFF's next step when their meaning has changed.
- After a significant result, decision, blocker or direction change, update its affected home. Group routine small steps; no rewrite is needed after every command.
- Record each fact once at its owner: goals in VISION, structure in ARCHITECTURE, phases in ROADMAP, work in TASKS, binding future choices in DEC, detailed observations in notes. Link from other locations.
- Before finishing, handing over or known upcoming context compaction, preserve current state. Do not rewrite unchanged records or update their dates for appearances.
- Each file has one writer. Other agents return results to that writer. Before delegation, record git status and exact allowed paths; afterwards inspect the full change list. Preserve others' edits; do not automatically reset/stash/clean them up.

## 7. Final Check

A fresh agent must be able to answer from the files: **why the project exists → where we are → which task → what is authorized → what is proved → what blocks progress → what comes next**.

Check real paths/links, agreement of TASKS/ROADMAP/HANDOFF statuses, architecture against observed code, and preservation of decisions, failures and deferred work. Record unverified items. Commit only authorized named files; if a commit is unauthorized or others' state prevents it, leave your files saved and say so honestly.

Briefly tell the owner what needs their decision, what changed, how it was checked and what remains unverified. Continuation must remain possible without that reply or the entire chat history.
