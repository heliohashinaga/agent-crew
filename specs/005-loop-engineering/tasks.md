# Tasks: Loop Engineering (Autonomous Control-Loop Layer)

**Branch**: `005-loop-engineering` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

**Implementation strategy**: MVP first (User Story 1 — the autonomous loop core),
then incremental delivery. The constitution mandates TDD (Red-Green-Refactor) as
NON-NEGOTIABLE, so every implementation task starts from a failing test. 
Library-First + CLI Interface: `loop_engine` is a standalone, independently
testable library exposed through a CLI; workflows compose it, never the reverse.
The deterministic core is **network-free** (FakeActor/FakeGate); review/LLM work
is behind injectable seams and gated `-m integration`.

- [ ] **Constitution**: TDD is non-negotiable — every implementation task starts
      from a failing (Red) test. No code merges without passing tests. Ruff must
      pass (`uv run ruff check .`). `pytest` (unit + contract) must pass with no
      network required; the independent-reviewer gate and real factory-actor
      paths are gated `-m integration`.
- [ ] Implementation order: Phase 1 (scaffold + models) → Phase 2 (seams +
      ledger, US1-4 foundation) → Phase 3 (loop engine core, US1) → Phase 4
      (gate + no-self-grading, US2) → Phase 5 (termination + escalation, US3) →
      Phase 6 (resume, US4) → Phase 7 (CLI + telemetry, US5) → Phase 8 (polish +
      full green suite). Tasks are listed in the priority order that satisfies
      P1 stories first; [P] tasks may run in parallel only when their files don't
      overlap.

## Phase 1 — Scaffold & Data Models

### US1-US5 Foundation

^- [x] **T001 — Specify & approve** — Author this feature's spec
      (`specs/005-loop-engineering/spec.md`), research (`research.md`), plan
      (`plan.md`), design artifacts (`data-model.md`, `contracts/`) and this task
      list. Approved by user before implementation begins.
- [x] **T002 — Scaffold `loop_engine` package [Red→Green]** — Create package
      skeleton `src/ai_factory/loop_engine/__init__.py` and the module stubs
      (`models.py`, `actor.py`, `gate.py`, `budget.py`, `ledger.py`, `engine.py`,
      `cli.py`, `escalation.py`). Add `tests/unit/loop_engine/` and
      `tests/contract/loop_engine/`. **Red**: a smoke test importing
      `ai_factory.loop_engine.models` and `.engine` fails to collect.
- [x] **T003 — Define `CheckResult` + `GateVerdict` models [Red→Green]** —
      `src/ai_factory/loop_engine/models.py`. `CheckResult`: `name: str`,
      `stage: Literal["deterministic","reviewer"]`, `passed: bool`,
      `reasons: list[str] = []`, `consumed: BudgetDelta` (default zero).
      `GateVerdict`: `passed: bool`, `checks: list[CheckResult] = []`,
      `consumed: BudgetDelta`. **Red**: unit test round-trips both via
      `model_validate_json` and asserts a gate is `passed` only when **all**
      checks pass (FR/Q2=C aggregate).
- [x] **T004 — Define `BudgetDelta` + `LoopBudget` models [Red→Green]** —
      `src/ai_factory/loop_engine/models.py`. `BudgetDelta`: `tokens: int = 0`,
      `cost_usd: float = 0.0`, `latency_s: float = 0.0`. `LoopBudget`:
      `max_tokens: int|None`, `max_seconds: float|None`, `max_cost_usd:
      float|None` (optional; at least one consumable dimension). **Red**: unit
      test builds and round-trips both; zero-defaults for `BudgetDelta`.
- [x] **T005 — Define `ActorOutput` + `RepairContext` models [Red→Green]** —
      `src/ai_factory/loop_engine/models.py`. `ActorOutput`: `status: bool`,
      `artifact_refs: list[str] = []`, `description: str = ""`, `summary:
      str = ""`. `RepairContext`: carries the previous `GateVerdict` (bounded,
      concise — never a full dump) (FR-006). **Red**: unit test round-trips
      `ActorOutput` and asserts a `RepairContext` holds a bounded prior verdict.
- [x] **T006 — Define `RatchetConfig` model [Red→Green]** —
      `src/ai_factory/loop_engine/models.py`. Fields: `max_stall: int`,
      `progress_key: str = "artifact_refs"`. **Red**: unit test round-trips the
      config and asserts defaults.
- [x] **T007 — Define `EscalationSummary` + `LoopResult` models [Red→Green]** —
      `src/ai_factory/loop_engine/models.py`. `EscalationSummary`: `status`,
      `iterations`, `gate_verdicts: list[GateVerdict]` (bounded), `budget_consumed:
      BudgetDelta`, `partial_artifacts: list[str]`. `LoopResult`:
      `run_id: str`, `status: Literal["passed","exhausted","stalled","error"]`,
      `iterations: int`, `gates: list[GateVerdict] = []`, `budget: BudgetDelta`,
      `artifact_refs: list[str] = []`, `escalation: EscalationSummary|None`.
      **Red**: unit test round-trips a `LoopResult` and asserts a passed result
      has `escalation: None`, a non-passed result carries `escalation`
      (FR-004).
- [x] **T008 — Define `LoopConfig` model [Red→Green]** —
      `src/ai_factory/loop_engine/models.py`. Fields: `actor`, `gate`,
      `max_iterations: int`, `budget: LoopBudget|None`, `ratchet:
      RatchetConfig|None`, `ledger_dir: Path`, `run_id: str`. Config is validated
      before any run (FR-009): missing actor/gate or `max_iterations <= 0` are
      rejected (fail fast). Also validate the **work/task input**: an
      empty/missing work payload raises a typed input error rather than running
      unsafely (spec Edge Cases, C2). **Red**: unit tests cover config fail-fast
      AND empty work-input rejection.
- [x] **T009 [P] — Define constant execution profile [Red→Green]** —
      `src/ai_factory/loop_engine/profile.py`. A **constant, non-escalating**
      execution profile for `loop_engine` (logical model, limits) living in the
      library and **NOT** routed through `capability_levels`/`FIXED_ROLES` (no
      `bump_level`), mirroring `researcher.profile`. **Red**: unit test asserts
      `loop_engine` exposes the constant profile and is NOT in
      `capability_levels.FIXED_ROLES`.

## Phase 2 — Seams & Ledger (US1-4 foundation)

### Foundational (blocking prerequisites)

- [x] **T020 — Define `Actor` + `Gate` seam protocols [Red→Green]** —
      `src/ai_factory/loop_engine/actor.py` and `gate.py`. `Actor.invoke(context:
      RepairContext) -> ActorOutput`; `Gate.verify(artifact) -> GateVerdict`.
      `FakeActor` (scripted outputs per call, optionally reads `RepairContext`)
      and `FakeGate` (scripted verdict sequence: pass-on-1st, pass-on-k+1,
      never, or a raising variant) in `tests/.../fakes.py` or a `fakes` module.
      **Red**: unit tests drive `FakeActor`/`FakeGate` and assert the seam
      round-trip (deterministic, no network). See
      `contracts/actor-gate-seam.md`.
- [x] **T021 — Define `CompositeGate` [Red→Green]** — `src/ai_factory/
      loop_engine/gate.py` (or `composite_gate.py`). Deterministic checks run
      first (network-free) and are **pluggable** (Q4=B): ship defaults
      (`artifact_exists` + caller-supplied suite/contract checks are supplied
      via the seam, not hard-coded in the core). An independent reviewer runs
      **only after** deterministic checks pass; aggregate `passed` requires
      **all** checks (Q2=C, FR-011). Link the reviewer stage to an injectable
      reviewer seam so the network/LLM path is integration-gated. **Red**: unit
      test with a failing deterministic check proves the reviewer is **not**
      invoked; with all-deterministic-pass the verdict drives onward. See
      `contracts/actor-gate-seam.md`.
- [x] **T022 — Define file-backed ledger (spine) append [Red→Green]** —
      `src/ai_factory/loop_engine/ledger.py`. JSON-lines journal at
      `<ledger_dir>/<run_id>.ledger.jsonl`; atomic append (write tmp + rename);
      append `ConfigRecord`, `IterationRecord`, `FinalRecord` (see
      `contracts/ledger-format.md`). **Red**: unit test on `tmp_path` appends
      config + 2 iterations + final, reads them back in order, and confirms no
      partial line.
- [x] **T023 — Ledger load + resume cursor [Red→Green]** —
      `src/ai_factory/loop_engine/ledger.py`. Load a ledger for `run_id`; find the
      **last completed `IterationRecord`** (highest `iteration`) as the resume
      cursor. **Red**: unit test on `tmp_path` writes k completed iterations and
      asserts the next iteration is `k+1` (FR-005, SC-004).
- [x] **T024 — Corrupt/absent ledger resume behavior [Red→Green]** —
      `src/ai_factory/loop_engine/ledger.py`. On resume, an absent ledger starts
      a **fresh run** (with a warning) or raises a clear typed error; corrupt
      JSON reports clearly — never silently corrupt data (FR-005). **Red**:
      unit tests write a malformed line / no file and assert the documented
      behavior.
- [x] **T025 — `run_id` scoping [Red→Green]** — `src/ai_factory/loop_engine/
      ledger.py`. Deterministic run scoping: resume requires the same `run_id`;
      a resume with a different `run_id` starts a fresh run (documented; no
      silent overwrite of another run). **Red**: unit test resumes with a
      mismatched `run_id` and asserts a fresh run result is produced.

## Phase 3 — Loop Engine Core (US1)

### User Story 1 - Run an autonomous loop until verified success or termination

> Story goal: `run_loop(LoopConfig) -> LoopResult` executes actor → gate →
> repair → repeat until passed or termination. **Independent test**: FakeActor +
> FakeGate, deterministic/network-free — correct iteration counts, repair-context
> propagation, `passed`/`exhausted` with iteration count (SC-001/SC-002).

- [x] **T030 — `engine.run_loop` core: pass-on-first [Red→Green]** —
      `src/ai_factory/loop_engine/engine.py`. Build the minimal control loop:
      iterate `actor.invoke` → `gate.verify`. **Red**: `FakeGate` passes on 1st
      call → `LoopResult(status="passed", iterations=1)` with the actor's
      artifact refs (US1 AS-1).
- [x] **T031 — Repair path: feed failure context [Red→Green]** —
      `src/ai_factory/loop_engine/engine.py`. Each failed iteration feeds the
      previous `GateVerdict` (bounded) into the next actor invocation via
      `RepairContext` (FR-006). **Red**: `FakeGate` fails k calls then passes →
      exactly `k+1` iterations; each failure is followed by a repair call whose
      `RepairContext` carries the previous verdict (US1 AS-2).
- [x] **T032 — Termination at `max_iterations` [Red→Green]** —
      `src/ai_factory/loop_engine/engine.py`. Never-passing gate + `max_iterations=N`
      → stop after `≤ N` iterations with `status="exhausted"` — never unbounded
      (FR-003, US1 AS-3, SC-002). **Red**: `FakeGate` never passes, assert
      iteration count `<= max_iterations`.

## Phase 4 — External Gate / No Self-Grading (US2)

### User Story 2 - External verification gate — no self-grading

> Story goal: the external `Gate` is the **exclusive** source of truth for
> `passed`; the actor can never mark its own work done. **Independent test**:
> FakeActor always claims success while FakeGate fails → `exhausted`, reason is
> the gate's (SC-003).

- [x] **T040 — No-self-grading invariant [Red→Green]** —
      `src/ai_factory/loop_engine/engine.py`. Author a dedicated test asserting
      the loop never uses the actor's `status` claim for the outcome. **Red**:
      `FakeActor` always claims success while `FakeGate` fails → outcome is
      `exhausted` (not `passed`), and the held-back reason is the **gate's**
      (US2 AS-1, SC-003).
- [x] **T041 — Bounded reasons to next iteration [Red→Green]** —
      `src/ai_factory/loop_engine/engine.py`. A gate failing with structured
      reasons forwards those (bounded, concise) into the next iteration's actor —
      never a full dump (US2 AS-2, FR-006). **Red**: `FakeGate` returns
      structured reasons; assert the next `RepairContext` carries exactly those
      bounds.
- [x] **T042 — Gate-unavailable surfaces, never silent pass [Red→Green]** —
      `src/ai_factory/loop_engine/engine.py`. A gate that errors/unavailable must
      surface a **typed error** (`LoopGateError`) — never a silent pass or skip
      (US2 AS-3). **Red**: a raising `FakeGate` variant raises the typed error
      from `run_loop`.

## Phase 5 — Termination, Budgets & Escalation (US3)

### User Story 3 - Termination conditions, budgets, and human escalation

> Story goal: guarantees termination (max_iterations, budget, stall ratchet) and
> escalates to a human with a concise summary on non-pass. **Independent test**:
> deterministic — never-passing gate ≤ N; budget-exceeded → exhausted; stall
> ratchet terminates no-progress iterations (SC-002).

- [x] **T050 — Budget tracker [Red→Green]** — `src/ai_factory/loop_engine/
      budget.py`. Track tokens/cost/latency (`BudgetDelta`) consumed across
      iterations; stop when a `LoopBudget` dimension is exceeded before the gate
      passes → `exhausted` (FR-003, US3 AS-2). Budget exhausted **mid-iteration**:
      current iteration may finish (atomic checkpoint) but the next does not
      start. **Red**: a slow/budget-consuming `FakeActor` + never-passing gate →
      `exhausted` once budget is exceeded.
- [x] **T051 — Stall ratchet [Red→Green]** — `src/ai_factory/loop_engine/
      budget.py` + `engine.py`. Optional `RatchetConfig.max_stall` consecutive
      no-progress iterations → terminate early with `stalled`/`exhausted`
      (US3 AS-3). **Progress** = the set of `artifact_refs` on `ActorOutput`
      changes between consecutive iterations (via `progress_key`)
      (FR-003). **Red**: `FakeActor` yields no progress across `max_stall`
      iterations → early `stalled` termination; asserting a changed
      `artifact_refs` set counts as progress.
- [x] **T053 — Actor-exception handling [Red→Green]** —
      `src/ai_factory/loop_engine/engine.py`. When the **actor** raises an
      exception (not just a gate failure), record the iteration as failed with
      the error and apply the repair/retry path (if budget allows) or escalate;
      never crash the whole loop unless configured to fail fast (spec Edge
      Cases, C1). **Red**: a raising `FakeActor` → the run records the failed
      iteration, applies repair/retry, and resolves to a non-pass `LoopResult`
      (or typed error if fail-fast), never a silent unexpected crash.
- [x] **T052 — Human escalation summary [Red→Green]** — `src/ai_factory/
      loop_engine/escalation.py`. Non-pass ending always produces a concise
      `EscalationSummary` (status, iterations, bounded verdicts, budget consumed,
      partial artifact pointers) (FR-004, US3 AS-4). **Red**: an exhausted loop's
      `LoopResult` carries a populated, bounded `escalation`.

## Phase 6 — Durable State & Resume (US4)

### User Story 4 - Durable state and resume

> Story goal: loop persists to a durable ledger and resumes from the last
> completed checkpoint. **Independent test**: `tmp_path` ledger — interrupt after
> k iterations, resume to k+1, total preserved (SC-004).

- [x] **T060 — Engine writes ledger records per iteration [Red→Green]** —
      `src/ai_factory/loop_engine/engine.py`. `run_loop` appends `ConfigRecord`,
      one `IterationRecord` per completed iteration, and a `FinalRecord` to the
      ledger (FR-005, `contracts/ledger-format.md`). **Red**: unit test on
      `tmp_path` asserts a config + N iteration + final records after a run.
- [x] **T061 — Resume from last checkpoint [Red→Green]** —
      `src/ai_factory/loop_engine/engine.py`. A resumed run reads the ledger,
      continues from the last completed `IterationRecord` (iteration `k+1`), and
      never re-runs completed iterations (FR-005, US4 AS-1, SC-004). **Red**:
      run with a failing gate, simulate interruption after k iterations (raise /
      stop), resume, assert continuation from `k+1` and correct total.
- [x] **T062 — Ledger run summary read [Red→Green]** — `src/ai_factory/
      loop_engine/ledger.py`. A fresh caller can read a concise run summary
      (iterations, verdicts, budget, status) — human- and machine-readable
      (US4 AS-2). **Red**: unit test reads a completed ledger and renders a
      summary without re-running.

## Phase 7 — Library-First CLI & Telemetry (US5)

### User Story 5 - Library-First CLI and telemetry

> Story goal: `loop_engine` exposes a CLI (`ai-factory-loop`) with JSON +
> human-readable output, meaningful exit codes, and per-iteration telemetry
> (`role == "loop_engine"`, no secrets). **Independent test**: CLI with fakes
> behind an injectable seam → stdout JSON parses to `LoopResult`, exit codes
> match outcome (SC-006).

- [x] **T070 — CLI parser [Red→Green]** — `src/ai_factory/loop_engine/cli.py`,
      reusing `shared/cli_util.py` (`add_output_format_arg`, `run`, `emit`,
      `write_stdout`). Args: `--actor`, `--gate`, `--run-id`, `--ledger-dir`,
      `--max-iterations` (required), optional `--budget-tokens/-seconds/-cost`,
      `--ratchet-max-stall`, `--output-format`, `--resume`, `--telemetry`.
      Register `ai-factory-loop = ai_factory.loop_engine.cli:main` in
      `pyproject.toml [project.scripts]`. **Red**: contract test asserts a usage
      error (non-zero) when required args are missing. See
      `contracts/loop-cli.md`.
- [x] **T071 — CLI passed → JSON + exit 0 [Red→Green]** — `cli.py`. Calling with a
      passing fake actor/gate behind the injectable seam prints valid JSON
      `LoopResult` (`status: passed`) to stdout, diagnostics to stderr, exit `0`
      (FR-007, US5 AS-1). **Red**: contract test drives `run(main, [...])` with
      `capsys`.
- [x] **T072 — CLI exhausted/escalation → distinct exit [Red→Green]** — `cli.py`.
      An exhausted/stalled loop exits non-zero `2` with `status` indicating
      `exhausted` (distinct from hard errors), `escalation` present (US5 AS-2,
      FR-004/FR-007). **Red**: contract test asserts exit `2` and JSON status.
- [x] **T073 — CLI human output + resolution/usage exits [Red→Green]** — `cli.py`.
      `--output-format human` prints a readable brief (status, iterations,
      verdicts, budget, refs); invalid config (missing actor/gate,
      `--max-iterations <= 0`) → exit `3`; missing/empty args → exit `1`; and an
      unavailable gate/actor surfacing `status == "error"` → exit `4` distinct
      from usage/resolution (US5 AS-3, FR-007, F2). **Red**: contract tests
      assert human output + the non-zero codes `1` (usage), `3` (resolution),
      and `4` (`error`).
- [x] **T074 — Per-iteration telemetry, `role == "loop_engine"` [Red→Green]** —
      `src/ai_factory/loop_engine/engine.py` (and/or `cli.py`). Emit a
      `TelemetryRecord` per iteration via the shared telemetry seam with
      tokens/cost/latency/retries/errors/escalations/result; no secret-looking
      values logged (FR-008, US5 AS-4, Principle V). **Red**: unit test asserts an
      emitted record carries `role == "loop_engine"` and no secret-looking
      values.

## Phase 8 — Concrete Binding, Polish & Full Green

### Cross-cutting / integration

- [x] **T080 — Concrete factory actor binding [Red→Green]** —
      `src/ai_factory/loop_engine/factory_actor.py`. Implement `FactoryActor`
      over the factory folder-driven dev pipeline (approved spec folder →
      execution) as a **library seam** — NOT wired into `dev_workflow` nodes
      (FR-010, FR-012, Q1=A). **Red/Green**: unit test proves it binds to the
      `Actor` protocol; the real end-to-end path is `-m integration`.
- [x] **T081 — Independent reviewer gate (integration) [Red→Green]** —
      `src/ai_factory/loop_engine/reviewer_gate.py`. Independent-reviewer
      second-stage gate wired to an injectable provider; network/LLM path under
      `-m integration`; deterministic core stays network-free (FR-011, Q2=C);
      when unavailable it surfaces a typed error or documented skip — never a
      silent pass. **Red**: integration test asserts best-effort reviewer pass/skip
      on real provider, or skips cleanly offline.
- [x] **T082 — Docs**: Add `loop_engine` to `AGENTS.md` role list and a short
      section/example in `README.md` (and `quickstart.md` of this feature).
      Document the intended composition seam (workflows compose it; not wired into
      nodes in v1) (FR-010).
- [x] **T083 — Full suite Green + Ruff** — `uv run ruff check .` clean; `uv run
      pytest -q` (unit+contract) all pass with **no network**; integration
      (`-m integration`) passes/skips cleanly.

## Acceptance Handoff

- [x] **T090 — Against the worked US1** — A loop run with a `FakeActor` + `FakeGate`
      (deterministic, network-free) reproduces US1 AS-1/2/3 end-to-end via
      `ai_factory.loop_engine.engine.run_loop`: pass-on-first → `passed`
      iterations=1; fail-k-then-pass → exactly k+1 with repair context;
      never-pass + `max_iterations=N` → `exhausted`, `<= N` iterations. Verified
      via unit/contract/integration tests and CLI probes.
- [x] **T091 — Boundary check** — Missing/invalid `--actor`/`--gate`/`--run-id`/
      `--max-iterations` → usage/resolution errors; empty work input → typed
      error; gate-unavailable → typed error (never silent pass); corrupt/absent
      ledger on resume → fresh run + warning or clear error; budget/ratchet
      exhaustion → `exhausted`/`stalled`; mixed verdicts (some checks fail) →
      `passed` only when **all** pass. Verified via unit/contract/integration
      tests and CLI probes (edge cases).
^- [x] **T092 — Deep review** — Read-only review of the diff verifying Library-First
      (no import of `ai_factory.loop_engine` outside the loop engine package
      except the intended seam), the deterministic core has no network
      (`engine.py` zero network calls), and the reviewer/factory-actor paths are
      integration-gated; approve merge.

---

## Dependencies & Parallelization

### Completion order

```
Phase 1 (T001–T009)  →  Phase 2 (T020–T025)  →  Phase 3 (T030–T032, US1)
   └── Phase 4 (T040–T042, US2)   requires engine core (T030–T031)
   └── Phase 5 (T050–T053, US3)   requires engine core (T030–T032)
   └── Phase 6 (T060–T062, US4)   requires engine core + ledger (T022–T025)
   └── Phase 7 (T070–T074, US5)   requires models + engine + ledger + budget
Phase 8 (T080–T083)  +  Acceptance (T090–T092)
```

- **US1 (T030–T032)** is the MVP and the only blocking prerequisite for
  US2–US6 usability; recommended first.
- **US2 (T040–T042)** and **US3 (T050–T053)** depend only on the engine core
  (T030–T032); they can be implemented in parallel with each other after US1.
- **US4 (T060–T062)** depends on the engine core **and** the ledger foundation
  (T022–T025); can run parallel to US2/US3 once those bases exist.
- **US5 (T070–T074)** depends on models (Phase 1) + engine core + ledger +
  budget; starts after US1 (and in parallel with US2–US4).

### Parallel examples

- After **Phase 1 + T030–T032 (US1)**, these may run in parallel:
  - T040–T042 (US2) — files `engine.py` (does not overlap US1's, only adds
    invariant/error tests + small engine branches).
  - T050–T053 (US3) — files `budget.py`, `escalation.py` + engine branches.
  - T060–T062 (US4) — `ledger.py` write hooks in `engine.py`.
  - T070–T074 (US5) — `cli.py`, `pyproject.toml`, telemetry emission.
  - If [P]-tagged (non-overlapping files), run concurrently under worktree
    isolation; otherwise serialize on `engine.py` edits to keep a single writer.

## Implementation notes (TDD, JSON + human, exit codes)

- **Library-First**: `loop_engine` is standalone; workflows never import it,
  except the intended composition seam (FR-010). No import of
  `ai_factory.loop_engine` outside the package (T092 must verify).
- **CLI**: JSON on stdout by default, diagnostics to stderr; `--output-format
  human` for readable output; exit codes `0` passed / `2` exhausted/escalation /
  `3` resolution-config / `4` error / `1` usage (FR-007, `contracts/loop-cli.md`).
- **Telemetry**: per-iteration `TelemetryRecord` with `role == "loop_engine"`;
  secrets redacted before emission (FR-008, Principle V).
- Each task lists its exact file path; tests live under
  `tests/unit/loop_engine/`, `tests/contract/loop_engine/`, and
  `tests/integration/loop_engine/` (`-m integration`).