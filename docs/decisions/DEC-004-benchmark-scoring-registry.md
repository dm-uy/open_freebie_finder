# DEC-004: Benchmark Scoring Registry — Static Curated Store with Script-Assisted Updates

* **Status:** `accepted` (owner-approved in session on 2026-10-22)
* **Phase:** Governs P3 (Benchmark Engine, Quality Tiering) design; to be detailed in a P3 specification.
* **Related:** `VISION.md` §4 (Scoring & Context Guard), `ROADMAP.md` P3, `ARCHITECTURE.md` §2.6 (`core/benchmarks/`), DEC-002 (declarative YAML pattern), DEC-003 (canonical model names).

## Context and Problem

VISION and ROADMAP P3 require a benchmark score registry (Chatbot Arena Elo, MMLU, HumanEval) to:

1. Classify free models into quality tiers (S / A / B).
2. Power virtual routing aliases (`auto:quality`, `auto:fast`, `auto:code`) that select the best-suited model per task.
3. Display per-model benchmark scores in the React dashboard for human comparison ("which model is better for which task").

The data source landscape has specific constraints:

* **Chatbot Arena (LMArena)** is the most current and broadly covering source of comparative quality (Elo-style ratings), published as public CSV/datasets on Hugging Face; it has **no stable machine API contract**.
* **HELM (Stanford)** provides academically rigorous results (MMLU and others) via public JSON/CSV releases; also no update-notification contract.
* **OpenRouter / provider APIs** expose pricing and context lengths but **no benchmark scores** — they cannot serve as a source.
* **Open LLM Leaderboard (Hugging Face)** is discontinued/frozen and must not be relied upon.
* **Artificial Analysis** offers a quality index via a commercial API; unsuitable as the primary dependency of a free open-source tool.

Benchmark data changes on a scale of **weeks to months** (unlike the free-model catalog, which changes within hours and is handled by the dynamic discovery worker). Fresh models typically appear in our registry **before** they appear in any leaderboard.

## Considered Options

### Option 1: Dynamic Runtime Benchmark Discovery Worker (rejected)
* A background service polling LMArena/HELM periodically, caching results in SQLite, like the OpenRouter discovery worker.
* *Pros:* Always fresh without human action.
* *Cons:* Relies on scraping unstable public exports with no API contract — fragile, breaks silently, may violate source terms; zero-setup philosophy suffers; updates are needed far less often than the effort of maintaining a resilient scraper warrants.

### Option 2: External Online Scoring Service (rejected)
* Query a commercial scoring API (e.g., Artificial Analysis) at runtime.
* *Cons:* Introduces a paid external dependency, network calls, and an outage surface into a local tool; contradicts the zero-cost, zero-setup core value.

### Option 3: Static Curated Store in Repository + Script-Assisted Updates (chosen)
* A versioned benchmark file shipped in the repo, refreshed by a manually-run update script, changes reviewed through normal git flow.
* *Pros:*
  * Deterministic, offline-capable, zero runtime dependencies; identical to the proven declarative pattern of `providers.yaml` (DEC-002).
  * Every benchmark change is visible as a reviewable git diff — no silent ranking shifts.
  * Simple to expose to the dashboard and the router from an in-memory table at startup (matches ARCHITECTURE §2.6).
* *Cons:* Data can go stale between manual runs; mitigated by the update script and the `unranked` fallback below.

## Decision

1. **Storage:** `backend/app/core/benchmarks/benchmarks.yaml` — the single source of truth for benchmark scores, versioned in git. Schema per canonical model: `elo` (Chatbot Arena), `mmlu`, `humaneval`, optional `notes`, and a computed quality `tier` (S / A / B with documented thresholds). Loaded and validated via Pydantic models at startup into an in-memory registry, joined with discovered models by canonical name.
2. **Updates:** `scripts/update_benchmarks.py` — a manually executed refresh tool that pulls the latest public exports (LMArena CSV as the primary source; HELM as a secondary academic source), normalizes model names, regenerates `benchmarks.yaml`, and leaves the result for git review/commit. Recommended cadence: monthly or on demand; no cron, no runtime automation.
3. **Name mapping:** canonical-name normalization for joins (strip `:free`, quantization and `-it`/`-instruct` suffixes, lowercase) plus a small manual-overrides section in the YAML for leaderboard name discrepancies.
4. **Fresh-model fallback (important invariant):** a discovered model with no benchmark entry receives status `unranked` and default tier `B`. Virtual quality pools (`auto:quality`, `auto:code`) exclude `unranked` models; `auto:free` still includes them (availability over quality). This prevents silently routing "best quality" requests to unknown models while never blocking zero-cost availability.
5. **Consumers:** the P3 tiering engine (routing) and the P4 dashboard (a benchmark column in the model catalog, fed via the admin models endpoint) read exclusively from this registry; they never fetch scores at runtime.

## Consequences

* The routing quality of `auto:quality`/`auto:code` is exactly as fresh as the last manual benchmark update — an accepted trade-off documented here.
* Benchmark refresh is a conscious, reviewable act (script run + PR), not a background risk.
* The decision keeps P3 free of new runtime dependencies and consistent with the declarative philosophy of DEC-002.
* When P3 starts, its specification must define: tier thresholds, the exact YAML schema, join/mapping rules, and ACs covering the `unranked` fallback behavior.
