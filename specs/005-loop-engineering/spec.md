# Feature Specification: Loop Engineering (Autonomous Control-Loop Layer)

**Feature Branch**: `005-loop-engineering`

**Created**: 2026-08-15

**Status**: Draft

**Input**: User description: "quero desenvolver um loop engineering" — develop a loop-engineering capability for the AI Dev Factory: an autonomous control loop that repeatedly runs work (actor), verifies it through an external gate (oracle), feeds failures back (repair path), and iterates until success or termination — persisting durable state (spine/ledger) so loops survive re-runs.

**Scope clarification**: This feature adds a **`loop_engine` role/library** to the ai-factory: a standalone, Library-First control-loop capability (analogous to `researcher` and the other role libraries) that any caller can use to run **iterative work loops** — execute an actor → verify through an **external gate** (never self-graded) → **repair** with failure context → repeat until the gate passes or **termination conditions** (max iterations, budget, escalation) are met — while persisting a **durable ledger/spine state** so a run can be paused/resumed. The `loop_engine` is deliberately **not** wired inside the `dev_workflow` nodes; workflows/CLIs *compose* it (Library-First). The deterministic core is network-free (constitution III/IV); network/LLM-bound gates are integration-gated.

## Clarifications

### Session 2026-08-15

- Q1 (actor scope): **A — Generic actor interface + 1 concrete binding.** The loop is a reusable harness over an injectable **actor** seam; the factory's folder-driven pipeline (approved spec folder → orchestrated execution → merge-ready PR) ships as the first concrete actor binding in v1. The interface is open, so future actors (media/video generation loops, arbitrary tasks, etc.) can be bound without changing the loop core.
- Q2 (gate): **C — Both deterministic + independent reviewer.** The gate requires all configured checks to pass: deterministic verification first (e.g., test/contract suite on the produced artifact), then an **independent reviewer** gate (a separate role/model reviewing the artifact — never the actor grading itself). The reviewer path is network/LLM-bound and integration-gated (`-m integration`).
- Q3 (human-in-the-loop): **A — No interactive approvals in v1.** Humans participate via **escalation at termination** (concise summary) and by manually starting/resuming loops through the CLI/library. Interactive approval checkpoints are future work.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run an autonomous loop until verified success or termination (Priority: P1)

An operator (human or orchestrator) starts a loop over a piece of work (e.g., the factory's approved-spec-folder → execution pipeline) without step-by-step supervision. The `loop_engine` executes the actor, verifies the result through an **external gate**, and — if the gate fails — runs a **repair iteration** with the failure context fed back. The loop stops only when the gate passes or a termination condition (max iterations, budget, escalation) is reached. The operator receives a `LoopResult` describing the outcome, iteration count, and gates.

**Why this priority**: This is the core ask — an autonomous, verifiable, terminating loop is the whole point of loop engineering.

**Independent Test**: Can be tested with a `FakeActor` + `FakeGate` (deterministic, network-free): assert the loop runs N iterations when the gate keeps failing, that each failed iteration receives the **previous failure context** (repair), and that the loop reports the correct final outcome (`passed` / `exhausted`) with its iteration count.

**Acceptance Scenarios**:

1. **Given** a loop whose gate passes on the first attempt, **When** the loop runs, **Then** it completes in 1 iteration with outcome `passed` and the actor's artifact as the result.
2. **Given** a loop whose gate fails the first k iterations and passes on iteration k+1, **When** the loop runs, **Then** it produces exactly k+1 iterations, each failed iteration is followed by a repair iteration carrying the previous gate-failure context, and the final outcome is `passed`.
3. **Given** a loop whose gate never passes, **When** the loop runs with max-iterations N, **Then** it stops after at most N iterations with outcome `exhausted` (never runs unboundedly).

---

### User Story 2 - External verification gate — no self-grading (Priority: P1)

The loop's success decision is made by an **external, independent gate**, not by the actor that produced the work. The gate returns a structured verdict (pass/fail + reasons) that drives both the outcome and the repair path. The actor can never mark its own work as "done."

**Why this priority**: "The model must not grade its own work" is a core loop-engineering invariant and the main safeguard against false success.

**Independent Test**: Can be tested deterministically with a `FakeActor` that always claims success and a `FakeGate` that fails: assert the loop does **not** treat the actor's claim as success and reports `failed`/`exhausted` with the gate's reasons.

**Acceptance Scenarios**:

1. **Given** a `FakeActor` that claims success while the `FakeGate` fails, **When** the loop runs, **Then** the loop reports `exhausted` (not `passed`), and the held-back reason is the gate's, not the actor's.
2. **Given** a gate that fails with structured reasons, **When** the repair path runs, **Then** the next iteration's actor receives those reasons (bounded, concise — never a full dump).
3. **Given** a gate that is unavailable/errors, **When** the loop runs, **Then** the error is surfaced (typed exception in library / non-zero CLI exit), never silently treated as a pass.

---

### User Story 3 - Termination conditions, budgets, and human escalation (Priority: P1)

The loop guarantees termination: configurable **max-iterations**, **budget** (time/tokens/cost), and an optional **progress/stall ratchet**. When termination conditions are reached without the gate passing, the loop **escalates to a human** with a concise summary (outcome, iterations, failures, budget consumed). A loop never runs forever and never silently consumes unbounded budget.

**Why this priority**: Safety — unbounded autonomous loops are the failure mode loop engineering exists to prevent.

**Independent Test**: Can be tested deterministically: a loop with max-iterations=N and a never-passing gate runs ≤ N iterations; a loop with a token/time budget and a slow `FakeActor` stops when the budget is exceeded; a stall ratchet terminates a loop whose iterations make no progress.

**Acceptance Scenarios**:

1. **Given** max-iterations=N and a never-passing gate, **When** the loop runs, **Then** it performs at most N iterations and reports `exhausted`.
2. **Given** a budget limit, **When** the budget is consumed before the gate passes, **Then** the loop stops and reports `exhausted` (escalation).
3. **Given** a ratchet enabled and consecutive iterations with no progress, **When** the loop runs, **Then** it terminates early with outcome `exhausted` (or a distinct `stalled` status) rather than continuing pointlessly.
4. **Given** an exhausted/stalled loop, **When** the loop ends, **Then** a concise human escalation summary is produced: iterations, gate verdicts, budget consumed, and pointers to partial artifacts.

---

### User Story 4 - Durable state and resume (Priority: P2)

The loop persists its state to a **durable ledger/spine** across iterations and across process runs. An interrupted loop can be **resumed** from the last checkpoint instead of restarting from scratch; the ledger records iterations, verdicts, budget consumed, and repair context.

**Why this priority**: Long loops must survive crashes/restarts; durable state is the "spine" of loop engineering.

**Independent Test**: Can be tested deterministically (e.g., persist to a `tmp_path` ledger): start a loop with a failing gate, simulate an interruption after k iterations, resume, and assert the loop continues from iteration k+1 (not from 1) and completes with the correct total.

**Acceptance Scenarios**:

1. **Given** a paused/interrupted loop with a persisted ledger, **When** the loop resumes, **Then** it continues from the last completed checkpoint (no re-running of completed iterations).
2. **Given** a fresh caller, **When** they query the ledger, **Then** they can read a concise run summary (iterations, verdicts, budget, status) — human-readable and machine-readable.
3. **Given** a corrupt/absent ledger on resume, **When** the loop starts, **Then** it starts a new run (with a warning) or surfaces a clear error — never silently corrupt data.

---

### User Story 5 - Library-First CLI and telemetry (Priority: P2)

The `loop_engine` is exposed as a library (core function) **and** as a CLI (`ai-factory-loop`) with JSON and human-readable output and meaningful exit codes, following the repo-wide library-CLI convention. Every iteration emits per-role telemetry (`role == "loop_engine"`, tokens, cost, latency, retries, errors, escalations, result).

**Why this priority**: Constitution: every library exposes a CLI with JSON + human output and meaningful exit codes; observability is a non-negotiable.

**Independent Test**: Can be tested by invoking the CLI with `FakeActor`/`FakeGate` behind an injectable seam (deterministic) and asserting stdout JSON parses into a `LoopResult` with correct status and that exit codes match the outcome (0 passed / non-zero exhausted / usage / resolution).

**Acceptance Scenarios**:

1. **Given** a loop that passes, **When** the CLI runs with `--format json`, **Then** stdout carries a valid JSON `LoopResult` with `status: passed` and the diagnostic output goes to stderr; exit code 0.
2. **Given** a loop that exhausts, **When** the CLI runs, **Then** it exits non-zero with a status indicating `exhausted` (distinct from hard errors).
3. **Given** missing/invalid arguments, **When** the CLI runs, **Then** it exits non-zero with a clear usage error.
4. **Given** a loop run, **When** telemetry is emitted, **Then** each iteration record has `role == "loop_engine"`, includes tokens/cost/latency/retries/errors/escalations/result, and contains no secret-looking values.

### Edge Cases

- What happens when the work/task input is empty? The library raises/returns a typed error; the CLI exits non-zero with a usage error.
- What happens when the actor fails with an exception (not just a gate failure)? The iteration is recorded as failed with the error, and the repair/retry path (if budget allows) or escalation is applied — never a crash of the whole loop unless configured to fail fast.
- What happens when the gate is unavailable (network/LLM down)? Surfaced clearly (typed error / non-zero exit), never treated as a pass or silently skipped.
- What happens when max-iterations or budget is 0/absent? Configuration validation errors (fail fast); a loop must never run with undefined termination conditions.
- What happens on repeated identical failures (stall)? The ratchet terminates with `stalled`/`exhausted` to avoid burning budget on no-progress iterations.
- What happens when budget is exhausted mid-iteration? The current iteration may finish (atomic checkpoint) but the next iteration does not start; outcome is `exhausted`.
- What happens with concurrent/resumed runs over the same ledger? Deterministic run-id scoping; resume requires the same run-id, otherwise a fresh run (documented behavior, no silent overwrite of a different run).
- What happens when a gate reports mixed verdicts (e.g., 2 of 3 checks pass)? The gate verdict is aggregate (pass only when **all** configured checks pass), with per-check breakdown in the reasons.
- What happens to large outputs/artifacts? Artifacts are referenced, not duplicated into the ledger; summaries stay concise (fits context window).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a standalone, Library-First `loop_engine` library exposing a core loop function (e.g., `run_loop(config)` / `LoopEngine`) that executes iterations of an **actor** followed by an **external gate**, feeding gate-failure context into the repair path, until the gate passes or termination conditions are met. The library MUST be deterministic and testable without network via injectable `FakeActor`/`FakeGate`.
- **FR-002**: The loop MUST determine success exclusively from the **external gate** verdict — the actor MUST NOT be able to mark its own work as passed (no self-grading).
- **FR-003**: The loop MUST support configurable **termination conditions**: `max_iterations` (required), an optional **budget** (time/tokens/cost), and an optional **progress/stall ratchet**. Termination MUST be guaranteed: with a never-passing gate, the loop performs at most `max_iterations` iterations.
- **FR-004**: When termination is reached without the gate passing, the loop MUST **escalate** with a concise human summary: final status, iterations, per-iteration gate verdicts (bounded), budget consumed, and pointers to partial artifacts.
- **FR-005**: The loop MUST persist a **durable ledger/spine state** across iterations and process runs, and MUST support **resume** from the last completed checkpoint (never re-running completed iterations); corrupted/absent state on resume MUST yield a documented behavior (fresh run with warning or clear error).
- **FR-006**: The loop MUST support a **repair path**: each failed iteration passes the previous gate-failure verdict (bounded, concise) to the next actor invocation.
- **FR-007**: The loop MUST expose a **CLI** (`ai-factory-loop`) with JSON and human-readable output on stdout, diagnostics on stderr, and meaningful exit codes: 0 = `passed`; distinct non-zero codes for `exhausted`/escalation, usage errors, and resolution/configuration errors.
- **FR-008**: The loop MUST emit **per-iteration telemetry** (`role == "loop_engine"`, tokens, cost, latency, retries, errors, escalations, result status) with no secret-looking values logged.
- **FR-009**: Configuration MUST be validated before the loop starts: missing actor/gate, zero/absent termination limits, or invalid run-id resume are rejected (fail fast) rather than running unsafely.
- **FR-010**: The library MUST be composable: the `dev_workflow`/other callers can invoke it (this spec documents the seam; wiring into every workflow node is NOT in scope for v1).
- **FR-011**: Per Q2=C, the gate MUST support two stages: (a) **deterministic checks** — network-free, MUST pass first; (b) an **independent reviewer** gate (a separate role/model) that runs only after (a) passes. Stage (b) MUST be integration-gated (`-m integration`); the deterministic core MUST remain network-free; when the network/LLM is unavailable, stage (b) surfaces cleanly (typed error or documented skip) — never a silent pass.
- **FR-012**: Per Q1=A, the system MUST define a **generic actor interface** and ship at least one concrete binding in v1: the factory's folder-driven pipeline (approved spec folder → orchestrated execution). The interface MUST be open so future actors (media/video generation, arbitrary tasks) can be bound without changing the loop core; those future bindings are out of scope for v1.

### Key Entities *(include if feature involves data)*

- **`loop_engine` role**: a standalone control-loop capability; emits telemetry with `role == "loop_engine"`. It carries a configurable execution profile (not a mono-capacity researcher; the loop is an orchestrator-like role but implemented as a plain library).
- **`LoopConfig`**: immutable configuration: `actor`, `gate`, `max_iterations`, optional `budget` (time/tokens/cost), optional `ratchet`, `ledger` (persistence target), `run_id`.
- **`LoopState` / ledger (spine)**: durable, append-only record of a run: `run_id`, iteration entries (actor output refs, gate verdicts, budget deltas, repair context), final status. Enables resume and audit.
- **`GateVerdict`**: structured result of one verification: `passed: bool`, `checks: list[CheckResult]` (per-check pass/fail + bounded reasons), `consumed` (budget).
- **`LoopResult`**: final outcome: `status` ∈ {`passed`, `exhausted`, `stalled`, `error`}, `iterations`, `gates` (verdict history, bounded), budget summary, artifact pointers, escalation summary.
- **`Actor` / `Gate` abstractions**: injectable seams (FakeActor/FakeGate in tests; concrete bindings per Q1/Q2 in prod).
- **`ai-factory-loop` CLI**: the library CLI wrapper.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of deterministic unit/contract tests pass **without network**, using FakeActor/FakeGate — including: correct iteration counts, repair-context propagation, no-self-grading, termination at `max_iterations`, and budget-driven exhaustion.
- **SC-002**: Termination is guaranteed: with a never-passing gate and `max_iterations = N`, the loop runs ≤ N iterations in every test (no infinite loops).
- **SC-003**: A loop never reports `passed` unless the external gate passed; a self-claiming actor cannot produce `passed` (asserted by a dedicated no-self-grading test).
- **SC-004**: Resume correctness: an interrupted loop resumes from the last checkpoint and the total completed iteration count is preserved (asserted by a pause/resume test on `tmp_path`).
- **SC-005**: Escalation always yields a concise human-readable summary (status, iterations, verdicts bounded, budget, artifact pointers) whenever the loop ends without `passed`.
- **SC-006**: The CLI emits valid JSON/human output, diagnostics on stderr, and correct exit codes for `passed` / `exhausted` / usage / resolution errors.
- **SC-007**: `uv run ruff check .` passes and the full `pytest` suite remains green (unit + contract, network blocked); integration tests (`-m integration`) pass when network/LLM is available and skip cleanly otherwise.

## Assumptions

- **Actor scope (Q1 = A)**: v1 ships a **generic actor interface** plus one **concrete binding** over the factory's folder-driven pipeline (approved spec folder → orchestrated execution) as the first real actor. The interface is open — media/video generation and arbitrary task actors can bind in the future without changing the loop core; those future bindings are out of scope for v1.
- **Gate (Q2 = C)**: v1 gate = **deterministic verification first** (e.g., suite pass / contract checks on the produced artifact), then an **independent reviewer** gate (separate role/model) that runs only after deterministic checks pass; the reviewer path is network/LLM-bound and integration-gated (`-m integration`).
- **Human-in-the-loop (Q3 = A)**: no interactive approval between iterations in v1; humans are involved via **escalation at termination** and via CLI invocation/resume. Interactive approval checkpoints are future work.
- **Manual trigger in v1**: loops are started manually (CLI/library call); scheduled/event triggers are future work.
- **Library-First**: `loop_engine` is a standalone library under the role-library layout with its own CLI, telemetry, and tests; workflows compose it, never the reverse.
- **Bounded state**: the ledger stores references and concise verdicts, never full artifacts or unbounded logs; summaries fit the invoking role's context window.
- **Deterministic core, optional LLM**: the core loop logic requires neither network nor an LLM; any LLM involvement is behind the gate/actor seams and integration-gated.