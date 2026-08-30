# Data Model: Loop Engineering (`loop_engine`)

**Feature**: `005-loop-engineering`
**Status**: Draft

> `loop_engine` is an **orchestrator-like role implemented as a plain library**
> (not a mono-capacity `researcher`, not routed through `capability_levels`). It
> runs an autonomous control loop: **actor → external gate → repair → repeat**,
> until the gate passes or termination conditions are met, persisting a durable
> ledger/spine that survives pause/crash (resume). The deterministic core is
> network-free; review/LLM work sits behind injectable seams and is
> integration-gated.

## Entities

### `CheckResult`
A single deterministic or reviewer check inside a gate.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | `str` | ✅ | e.g. `"suite_pass"`, `"contract_pass"`, `"reviewer"`. |
| `stage` | `str` | ✅ | `"deterministic"` or `"reviewer"` (Q2=C two-stage). |
| `passed` | `bool` | ✅ | Whether this check passed. |
| `reasons` | `list[str]` | default `[]` | Bounded, concise reasons (never a full dump). |
| `consumed` | `BudgetDelta` | default zero | Budget consumed by this check. |

### `GateVerdict`
The aggregate result of one verification pass over a run's artifact.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `passed` | `bool` | ✅ | `true` **only if all** configured checks pass (aggregate; FR/Q2=C). |
| `checks` | `list[CheckResult]` | default `[]` | Per-check breakdown feeding both outcome and repair. |
| `consumed` | `BudgetDelta` | default zero | Budget used across checks. |

- A gate that errors/unavailable raises a typed error (never a silent pass;
  US2 SC-3).

### `ActorOutput`
The result of one actor invocation.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `status` | `bool` | ✅ | Did the actor report success? **Not** the loop's verdict (no self-grading). |
| `artifact_refs` | `list[str]` | default `[]` | Pointers to produced artifacts (paths/URLs) — never duplicated into ledger. |
| `description` | `str` | default `""` | Short human description of what the actor produced. |
| `summary` | `str` | default `""` | Concise context fed back on repair (bounded). |

### `LoopConfig`
Immutable configuration validated before the loop starts (FR-009).

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `actor` | `Actor` | ✅ | Injectable actor seam. |
| `gate` | `Gate` | ✅ | Injectable gate seam (external, independent). |
| `max_iterations` | `int` | ✅ | Required; must be `> 0` (else config error). |
| `budget` | `LoopBudget \| None` | optional | Time/tokens/cost limits (FR-003). |
| `ratchet` | `RatchetConfig \| None` | optional | Stall/progress detector (FR-003). |
| `ledger_dir` | `Path` | ✅ | Durable spine target (file-backed JSON-lines). |
| `run_id` | `str` | ✅ | Deterministic run scoping; resume requires same `run_id`. |
| `exit_codes` | (implicit) | — | CLI mapping: 0 passed / non-zero exhausted / usage / resolution (FR-007). |

### `LoopBudget`
Termination budget (optional). At least one consumable dimension.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `max_tokens` | `int \| None` | optional | Token ceiling. |
| `max_seconds` | `float \| None` | optional | Wall-clock ceiling. |
| `max_cost_usd` | `float \| None` | optional | Cost ceiling. |

Consumed budget is recorded as a `BudgetDelta` (tokens/cost/latency) per
iteration; when a dimension exceeds its ceiling before the gate passes, the loop
**hard-stops** with outcome `exhausted` (US3, SC-2). Per **Q7=A** this is an
intentional, scoped divergence from the parent factory's soft-budget (warn +
continue) convention — within `loop_engine` budget is a **hard termination**;
the parent's soft-budget applies to its own cost tracking, not loop termination.
Budget exhausted mid-iteration: the current iteration may finish (atomic
checkpoint) but the next does not start.

### `RatchetConfig`
Stall/progress detector (optional).

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `max_stall` | `int` | ✅ | Number of consecutive no-progress iterations allowed. |
| `progress_key` | `str` | default `"artifact_refs"` | What counts as progress (e.g. artifact refs changed). |

A ratchet with `max_stall` consecutive no-progress iterations terminates early
with `stalled`/`exhausted` (US3, SC-3).

### Ledger records (`LedgerEntry`)
Append-only durable spine records (see `contracts/ledger-format.md`).

| Record | Fields |
|--------|--------|
| `ConfigRecord` | `run_id`, `config` snapshot. |
| `IterationRecord` | `run_id`, `iteration` (n), `actor_out`, `gate` (GateVerdict), `budget_delta`, `repair_context`. |
| `FinalRecord` | `run_id`, `status`, `iterations`, budget consumed, escalation summary, `ended_at`. |

### `LoopResult`
The final outcome returned by `run_loop(...)` and by the CLI.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `run_id` | `str` | ✅ | The run this result belongs to. |
| `status` | `str` | ✅ | `passed` \| `exhausted` \| `stalled` \| `error`. |
| `iterations` | `int` | ✅ | Total completed iterations. |
| `gates` | `list[GateVerdict]` | default `[]` | Verdict history (bounded — last N). |
| `budget` | `BudgetSummary` | default | Tokens/cost/latency consumed. |
| `artifact_refs` | `list[str]` | default `[]` | Pointers to final/partial artifacts. |
| `escalation` | `EscalationSummary \| None` | optional | Present when not `passed` (FR-004). |

### `EscalationSummary`
Concise human escalation (FR-004, Q3=A).

| Field | Type | Notes |
|-------|------|-------|
| `status` | `str` | Final status. |
| `iterations` | `int` | Count. |
| `gate_verdicts` | `list[GateVerdict]` | Bounded history. |
| `budget_consumed` | `BudgetSummary` | Tokens/cost/latency. |
| `partial_artifacts` | `list[str]` | Pointers to partial artifacts. |

## Seam Abstractions

- **`Actor`** (abstract): `invoke(context: RepairContext) -> ActorOutput`. The
  actor **cannot** mark the loop as passed — only the external `Gate` decides
  (FR-002, US2).
- **`Gate`** (abstract): `verify(artifact) -> GateVerdict`. External,
  independent. `CompositeGate` runs deterministic checks first, then (if passed)
  the independent reviewer (Q2=C). Reviewer is integration-gated.
- Concrete binding (Q1=A): `FactoryActor` over the factory folder-driven dev
  pipeline — shipped as a **library seam**, not wired into workflow nodes in v1
  (FR-010, FR-012).
- Test fakes: `FakeActor`, `FakeGate` — deterministic, network-free.

## Relationships

- `LoopEngine.run_loop(LoopConfig) -> LoopResult`.
- `LoopConfig` owns 1 `Actor`, 1 `Gate`, optional `LoopBudget`, optional
  `RatchetConfig`, and a `ledger_dir`.
- A run appends ledger records: 1 `ConfigRecord` → N `IterationRecord` → 1
  `FinalRecord`. `LoopResult` is derived from the ledger at the end / on resume.
- `GateVerdict` owns 0..* `CheckResult`; each `CheckResult` owns a
  `BudgetDelta`.

## Validation Rules (from FRs)

- **FR-001/FR-009**: `run_loop` requires a valid `LoopConfig`; missing
  actor/gate, `max_iterations <= 0`/absent, or invalid resume `run_id` → fail
  fast (typed config error), never an unsafe run.
- **FR-002**: outcome `passed` derives **exclusively** from the external gate;
  a self-claiming actor cannot produce `passed` (dedicated no-self-grading
  test).
- **FR-003**: termination guaranteed — never-passing gate runs `≤
  max_iterations`; budget/ratchet may stop earlier.
- **FR-005**: ledger durable + resume from last completed checkpoint; corrupt/
  absent ledger on resume → fresh run with warning or clear error, never
  silent corruption.
- **FR-006**: repair path feeds the previous `GateVerdict` (bounded, concise)
  into the next actor invocation. If the **actor raises an exception**, the
  iteration is recorded as **failed** and repaired via this path, but (per
  **Q6=A**) does **not** consume a `max_iterations` slot; such retries are
  bounded by the **budget**, escalating (FR-004) when budget is exhausted.
- **FR-008**: per-iteration telemetry `role == "loop_engine"` with tokens/cost/
  latency/retries/errors/escalations/result; secrets redacted.
- **FR-011**: deterministic checks pass first; independent reviewer runs only
  after; reviewer path integration-gated; unavailable/network-down reviewer
  surfaces clearly (typed skip/error), never a silent pass.

## State Transitions

```
[validated config]
      │
      ▼
┌─► run active ─(gate passes)──► passed ── end: LoopResult(status=passed)
│        │ (gate fails)
│        ▼
│   repair (feed verdict) ──► next iteration
│        │                    max_iterations/budget/ratchet exceeded
│        ▼
│   exhausted / stalled ──► escalation summary ── end: LoopResult
└──────────────────────────────────────────▶ interrupted: resume from ledger
```

The ledger is the **spine**: a resume read continues from the last completed
`IterationRecord` (no re-run of completed iterations), scoped by `run_id`.