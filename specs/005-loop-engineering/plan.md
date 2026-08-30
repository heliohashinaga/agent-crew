# Implementation Plan: Loop Engineering (Autonomous Control-Loop Layer)

**Feature Branch**: `005-loop-engineering`
**Last Updated**: 2026-08-15
**Spec**: [`spec.md`](./spec.md) | **Research**: [`research.md`](./research.md)

## Summary

Add a standalone, Library-First **`loop_engine`** capability to the ai-factory:
a reusable autonomous control-loop harness that repeatedly runs an **actor**
(`Actor` seam), verifies the result through an **external gate** (`Gate` seam —
never the actor grading itself), **repairs** with concise failure context, and
iterates until the gate passes or **termination conditions** (`max_iterations`,
budget, progress/stall ratchet) are met — persisting a **durable ledger/spine**
so loops survive pause/crash and **resume** from the last completed checkpoint.
Escalation at termination yields a concise human summary.

The `loop_engine` is an orchestrator-like role implemented as a **plain
library** (not a mono-capacity `researcher`; not routed through
`capability_levels`). Per clarifications: **Q1=A** a generic `Actor` interface
+ a concrete factory folder-driven pipeline binding; **Q2=C** a two-stage gate
(deterministic checks first, then an independent reviewer, integration-gated);
**Q3=A** no interactive approvals in v1 (escalation at termination + manual
start/resume).

**Library-First boundary (FR-010)**: `loop_engine` is deliberately **not**
wired inside the `dev_workflow` nodes in v1; workflows/CLIs *compose* it. The
factory folder-driven pipeline binding is shipped as a **library seam /
reference binding** that any caller may invoke, matching the `researcher`
pattern — it is not threaded through every planner/coder node in this pass.

**Technical approach** (from research — see `research.md`): Python ≥ 3.14 +
`uv`, `src`-style packaging; **Pydantic** for `LoopConfig`, `GateVerdict`,
`CheckResult`, `LoopResult`, and the ledger/spine records (validated state,
JSON serializable); the deterministic loop core is **network-free**; the ledger
is a **file-backed append journal** (JSON lines) supporting atomic writes and
`tmp_path`-testable resume. Gates split into a deterministic `CompositeGate`
(first stage, network-free) and an independent-reviewer gate (second stage,
`-m integration`). Every iteration emits **per-loop telemetry** (`role ==
"loop_engine"`, tokens/cost/latency/retries/errors/escalations/result), reusing
`shared/cli_util.py` + the telemetry seam (redaction mandatory).

## Technical Context

**Language/Version**: Python ≥ 3.14, managed with `uv` (constitution). No NEEDS
CLARIFICATION — settled.

**Primary Dependencies**:
- `pydantic` — validated models (`LoopConfig`, `GateVerdict`, `CheckResult`,
  `LoopResult`, ledger records); JSON round-trip for CLI + ledger + tests.
- `uv` / `pytest` — build + test, per constitution Principle III (Test-First,
  NON-NEGOTIABLE) and IV (Integration Testing).
- Injected seams only for network/LLM work: the deterministic core imports
  nothing network-bound; the **independent-reviewer gate** and any LLM-driven
  actor depend on injected collaborators (a `ReviewerGate` over a provider) and
  are **integration-gated** (`-m integration`).
- Stdlib `json` / `pathlib` / `enum` — ledger journal + CLI + termination math.
  No new third-party runtime dependency (LangGraph is NOT used for the loop in
  v1 — the loop is a plain control loop over a seam abstraction, not a graph).

**Storage**:
- **Ledger/spine**: file-backed JSON-lines journal under a caller-supplied
  `ledger_dir` (or `tmp_path` in tests), one record per iteration + config + a
  final status record; atomic append (write tmp + rename) so a reader never
  sees a partial record. Encodes the durable resume contract (FR-005). Full
  artifacts are **referenced, never duplicated** into the ledger (edge case).

**Testing**: `pytest` (unit + contract, network-free via `FakeActor` +
`FakeGate`); integration (`-m integration`) for the independent-reviewer gate.
Assertions cover iteration counts (US1), no-self-grading (US2), termination at
`max_iterations` / budget / ratchet (US3), pause/resume on `tmp_path` (US4),
CLI JSON/human + exit codes + telemetry (US5).

**Target Platform**: Developer host; runs locally; deterministic core has no
network.

**Project Type**: Library-first CLI capability — a standalone role library
under `src/ai_factory/loop_engine/` plus an `ai-factory-loop` console script,
composed by callers (workflows/CLIs). No service in v1.

**Performance Goals**: Loop safety over throughput: guaranteed termination
(`≤ max_iterations`), bounded budget, concise repair/escalation summaries. No
SLOs; per-iteration latency/cost/retries recorded as telemetry (FR-008), not
bounded by a target.

**Constraints**:
- Gate is exclusive source of truth for `passed`; actor can never self-grade
  (FR-002, US2).
- Termination is guaranteed from config validation (FR-009): `max_iterations`
  required and `> 0`; missing/zero termination limits fail fast.
- Budget within `loop_engine` is a **hard stop → `exhausted`** (Q7=A, FR-003);
  this is an intentional, scoped divergence from the parent factory's
  soft-budget (warn + continue) convention.
- **Actor-exception** (not a gate failure) records a failed iteration and
  repairs via the repair path, but does **not** consume a `max_iterations` slot
  (Q6=A); retries are bounded by budget, escalating on exhaustion.
- **`stalled`** is a distinct final status from `exhausted` (Q5=A).
- Credentials/LLM only behind seams and integration-gated; secrets redacted
  from telemetry (FR-008).
- Resume requires the same `run_id`; a mismatched/absent/corrupt ledger yields a
  fresh run with a warning or a clear typed error — never silent corruption.
- Deterministic core remains network-free even when review-aware
  (FR-011) — exactly the `researcher` `repo` vs `web` scoping pattern. The
  deterministic check set is **pluggable** (Q4=B): default = artifact referenced
  exists + caller-supplied suite/contract checks; the core never hard-codes
  binding-specific checks.

**Scale/Scope**: v1 = single loop, one harness, manual trigger, one concrete
actor binding + one composite gate. Multi-loop composition, scheduled/event
triggers, worktrees/subagent parallel loops, and interactive approvals are
explicitly out of scope (spec Assumptions + research "target architecture").

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after design.*

| Principle | Status | Evidence / Plan |
|-----------|--------|-----------------|
| **I. Library-First** | ✅ PASS | FR-001/FR-010/FR-012: `loop_engine` is a standalone, independently testable library under `src/ai_factory/loop_engine/`; workflows compose it, never the reverse; not wired into `dev_workflow` nodes in v1. |
| **II. CLI Interface** | ✅ PASS | FR-007: `ai-factory-loop` exposes JSON + human-readable stdout, diagnostics on stderr, meaningful exit codes (0 passed / 2 exhausted / 3 resolution / 4 error / 1 usage). |
| **III. Test-First (NON-NEGOTIABLE)** | ✅ PASS | Red-Green-Refactor per task in `tasks.md` (TDD); deterministic tests via `FakeActor`/`FakeGate`; no implementation merges without passing tests. |
| **IV. Integration Testing** | ✅ PASS | Independent-reviewer gate exercised under `-m integration`; deterministic core + fake-seam tests network-free; full suite green. |
| **V. Simplicity & Observability** | ✅ PASS | Per-iteration telemetry (`role == "loop_engine"`, FR-008); ledger = audit + resume (FR-005); YAGNI applied (no multi-loop, no triggers, no interactive approvals in v1) — justified in `research.md`. |

**Gate result**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/005-loop-engineering/
├── plan.md              # This file
├── research.md          # Phase 0 output (decision history)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── loop-cli.md      #   ai-factory-loop CLI contract
│   ├── actor-gate-seam.md   # Actor/Gate seam contracts + FakeActor/FakeGate
│   └── ledger-format.md     # durable spine journal format + resume contract
└── tasks.md             # Phase 2 output (/speckit.tasks — not created here)
```

### Source Code (repository root)

```text
src/ai_factory/
├── loop_engine/                 # standalone control-loop library (Library-First)
│   ├── __init__.py
│   ├── models.py                # LoopConfig, GateVerdict, CheckResult, LoopResult, budget, ledger records
│   ├── actor.py                 # Actor abstract seam + protocol
│   ├── gate.py                  # Gate abstract seam + CheckResult/verdict types + CompositeGate
│   ├── budget.py                # token/time/cost budget tracker + ratchet helpers  (could fold into models)
│   ├── ledger.py                # file-backed JSON-lines spine: append atomic record, load, resume, run summary
│   ├── engine.py                # core run_loop(engine) control loop (deterministic, network-free)
│   ├── factory_actor.py         # Q1=A concrete binding: folder-driven dev pipeline seam (library-only, not wired)
│   ├── reviewer_gate.py         # Q2=C independent-reviewer second-stage gate (integration-gated)
│   ├── profile.py               # constant, non-escalating execution profile for the loop_engine role (like researcher; NOT in capability_levels)
│   ├── cli.py                   # ai-factory-loop entrypoint (reuses shared/cli_util.py)
│   └── escalation.py            # concise human escalation summary builder
│
└── shared/
    ├── cli_util.py              # reuse: add_output_format_arg / run / emit / write_stdout
    └── telemetry/               # reuse: TelemetryRecord emission with redaction

tests/
├── unit/loop_engine/            # FakeActor/FakeGate deterministic tests per US1-5
├── contract/loop_engine/        # CLI + seam + ledger contract tests
└── integration/loop_engine/     # reviewer-gate + real factory-actor binding (-m integration)
```

**Structure Decision**: mirrors the `researcher` feature — a self-contained
role library with its own CLI, seam abstractions, ledger, telemetry, and tests,
reusing `shared/cli_util.py` and the telemetry seam. The factory folder-driven
binding (`factory_actor.py`) is a **reference binding** asserting FR-012's
seam without being wired into `dev_workflow` nodes in v1 (FR-010).

## Complexity Tracking

> None — Constitution Check passes with no violations.