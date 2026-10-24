# DEC-005 — Scope-bound adaptive resilience

Date: 2026-10-23. Status: approved by owner approval of [T-009 v1.0.0](../../specs/T-009-adaptive-circuit-breaker.md), R1–R3 and its bounded isolated live packet. Primary integration remains separate.

## Problem and choice

The fixed router cooldown lost Retry-After and could not coordinate concurrent recovery or distinguish client cancellation from an upstream fault. Keep financial safety and eligibility authoritative; add a registry-owned, memory-only resilience controller shared by consumer routers and existing private qualification.

Service/network/timeout failures back off per captured credential-scope/raw route. Nonfinancial429 pauses the credential scope conservatively; this is application policy, not a claim about upstream quota identity. Backoff starts at the configured strict integer1..300-second base (default60), doubles to900s, with one atomic HALF_OPEN owner after expiry. Supported upstream hints may extend the pause to86400s; larger/oversized hints defer until deliberate reset/new scope rather than silently shortening them. Protocol/other nonfinancial4xx quarantine uses the base interval without exponential increment.

Inference401 locks the private resolved credential identity independently of service/quota generations. Catalog/profile epoch changes or restoration of the same key cannot clear that lock; a genuinely different credential has separate state, and deliberate process restart resets process-local state. This does not restore a revoked account assertion or clear a financial hold. Discovery GET401/403 and standalone inference403 do not establish inference credential rejection.

Admission uses all-or-none synchronous recovery tickets immediately before owned I/O. Generation fencing prevents late successes/failures from changing newer route/quota state; actual401 uses current credential/auth-binding fencing. Private permits preserve their existing budgets, both-mode lease requirements and financial suppression; quota recovery adds no new sends/scheduler. Protected T-006 validation remains isolated.

Health outcomes and delivery outcomes are separate: final upstream cost inspection/cleanup precedes health publication; valid complete answers survive a cost incident or bounded final transport failure, while future protection updates separately. Started SSE is never replayed. Internal bounded aggregate/event labels add no public API or telemetry fields. Known eligible but health-blocked requests return503 with zero actual attempts, rather than unknown-model404.

## Alternatives and consequences

Retaining fixed expiry would leave concurrent recovery and stale-result races unresolved. Automatic auth/balance probes would weaken already approved safety/redeclaration boundaries and are excluded. A new diagnostics endpoint, durable shared store, jitter or distributed coordination would broaden this slice and are deferred.

All state is process-local, bounded to4096 routes and256 combined quota/auth entries; protected live gates are never evicted to restore access. Capacity exhaustion fails closed. Multiple processes do not coordinate and restart is not durable incident retention. Existing strict OpenRouter zero-price routing overrides and conditional account assurance remain unchanged. [Results](../../notes/T-009-results.md) retain that historical candidate distinction and the later owner-authorized, verified T-009 primary integration. The separate T-010 source candidate below has not been loaded into that primary.


## T-010 approved task extension (2026-10-23)

Owner approval of [T-010 v1.0.0/N1–N4](../../specs/T-010-task-specific-inference.md) extends the source backend with separate task catalogs/protocols and exact OpenRouter task routes. Declarative logical provider identity is retained; task parsing/zero-price controls are owned protocol policy, never arbitrary YAML expressions or client routing overrides. Chat's default listing, alternative-model fallback and response masking do not authorize embedding/rerank/decisions/speech substitution. Task service health is distinct; credential quota/auth and the financial account umbrella protect related chat/task routes together within the retained registry. Independent registries remain isolated. Rerank/speech and incomplete task pricing remain unknown, with no inherited chat omitted-fee exception or account qualification. This approval authorizes implementation, not acceptance of missing external proof or primary activation. [Result evidence and limits](../../notes/T-010-results.md).
