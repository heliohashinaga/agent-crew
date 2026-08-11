# Feature Specification: Folder-Driven Dev Run

**Feature Branch**: `002-folder-dev-run`

**Created**: 2026-08-09

**Status**: Draft

**Input**: User description: "Quero remover o spec-run e o spec-workflow, e que o dev-run receba o nome de uma spec da pasta `specs` (ex.: `002-folder-dev-run`) como a skill de implementação do speckit. O speckit já tem a skill clarify que faz a revisão e pode ser executada várias vezes — então o dev-run assume que a pasta já está pronta. O dev-run lê os artefatos speckit (spec.md, plan.md, tasks.md) e implementa a partir deles, entrando em qualquer nível (spec/plan/task gerando os artefatos abaixo, até a implementação)."

**Scope clarification**: This feature **removes** the independent `spec-run` command and the `spec-workflow` from being a required, separate entry point, and makes the `dev-run` command **enter directly from a speckit spec folder** by folder name — mirroring how the speckit `implement` skill operates. Clarification/review of the spec is **owned by the external speckit `clarify` skill**, which is assumed to have already been run to approval before `dev-run` is invoked. The factory itself therefore **does not re-derive or re-clarify requirements**; it consumes artifacts that are already considered ready.

## Clarifications

### Session 2026-08-09

- Q: When the `--spec-source git` mode opens a PR against the source repository, how should the factory authenticate and treat the source repo's trust boundary? → A: Reuse the caller's existing git host client credentials (no factory-managed secret store); treat the source repo as untrusted input and validate/sanitize its content before any write-back (Option D).

### Session 2026-08-11

- Q: When the target spec folder is incomplete (missing `plan.md` or `tasks.md`), what should `dev-run` do? → A: Always require a complete folder; missing artifacts error per FR-007, and lower artifacts (`plan.md`/`tasks.md`) are bootstrapped via the external speckit `plan`/`tasks` skills — the factory never auto-generates or re-derives them (Option C).
- Q: When a spec folder whose `tasks.md` already has tasks marked completed (`- [x]`) is passed, what is the default execution behavior? → A: The default is to **skip already-completed tasks** (marks preserved, content untouched) and run only the uncompleted ones; if **all** tasks are already completed, the run exits 0 as a no-op with **no PR** ("nothing to do"). A fresh run is idempotent and non-destructive.
- Q: How does a `dev-run` target a subset of tasks (or start mid-feature)? → A: A **task selector** filters which tasks execute, applied to the normal run (not a new mode): single `T###`, list `T3,T5`, range `T3-T7`, or open-checkpoint range `T3-` (that task and later). Exact selected tasks run; write-back flips only their `- [x]` marks; a targeted scope that produces code opens its **own small PR** (consistent with per-phase/PR, SC-009); the planner emits a **prerequisite warning** (not a block) if any earlier task before the selected range is still uncompleted.
- Q: How does a user force re-execution of already-completed or out-of-scope tasks? → A: `--force` re-runs selected tasks even if already marked `- [x]` (re-verify); plain `--resume` continues from the first uncompleted task (alias for "open range from first pending").
- Q: When removing the old `spec-run` command, should it be fully removed or kept as a deprecation shim? → A: Hard remove — delete `spec-run` from `[project.scripts]` and retire the factory `spec-workflow` modules entirely; any invocation of the removed command fails (Option A).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run the Dev Workflow from a Spec Folder Name (Priority: P1)

A user invokes `dev-run` with the **name of a spec folder** (e.g., `dev-run 002-folder-dev-run`), and the factory locates that folder under `specs/<name>/`, reads its speckit artifacts (`spec.md`, `plan.md`, `tasks.md`), and drives the implementation pipeline to produce a merge-ready pull request — exactly as a developer using the speckit `implement` skill would.

**Why this priority**: This is the core of the change. Today `dev-run` requires a factory `spec_version_id` provided by `spec-run`; this makes the folder the single, natural entry point and removes the dependency on the separate spec command.

**Independent Test**: Can be tested by invoking `dev-run <folder>` against a known `specs/<name>/` folder containing fully-formed `spec.md`, `plan.md`, and `tasks.md`, and confirming a merge-ready PR is produced from those artifacts — without any factory spec-workflow run.

**Acceptance Scenarios**:

1. **Given** a folder `specs/<name>/` with `spec.md`, `plan.md`, and `tasks.md`, **When** the user runs `dev-run <name>`, **Then** the folder is resolved and the implementation pipeline runs against the artifacts to produce a pull request.
2. **Given** a folder name that does not exist under `specs/`, **When** the user runs `dev-run <name>`, **Then** a clear error is returned (exit code), and no pipeline runs.

---

### User Story 2 - Consume an Existing Spec/Plan/Task (Priority: P1)

The `dev-run` can start from a speckit spec folder that already contains all three artifacts (`spec.md`, `plan.md`, `tasks.md`) and, without re-deriving them, generate the next level: the `TechnicalPlan` (assessment + subtasks) and then the implementation.

**Why this priority**: This is the "enter at any level and descend" requirement — the user wants to work from a request/spec/plan/task and have the system produce everything below. Consuming the ready folder is the enabling capability.

**Independent Test**: Can be tested by pointing `dev-run` at a folder with all three markdown artifacts and confirming the `TechnicalPlan` subtasks are derived from the `tasks.md` file paths and the acceptance criteria are carried from the `spec.md` functional requirements — with no re-derivation of requirements.

**Acceptance Scenarios**:

1. **Given** a ready spec folder, **When** `dev-run` reads it, **Then** `spec.md` functional requirements become the subtask acceptance criteria and the `tasks.md` file paths become the subtask `files`.
2. **Given** a spec folder, **When** `dev-run` builds the plan, **Then** the technical assessment (complexity, risk, architecture impact, security surface) is imported from the folder's `plan.md` rather than re-derived only from `spec.md`.
3. **Given** a spec folder, **When** `dev-run` runs, **Then** no new requirements clarification is performed by the factory (the `clarify` skill's role is external).

---

### User Story 3 - Remove spec-run and the spec-workflow Entry Point (Priority: P1)

The independent `spec-run` command and the factory `spec-workflow` are removed as a required, separate entry point. Nothing in the user-facing flow depends on producing a factory `SpecVersion`/`spec_version_id` beforehand.

**Why this priority**: This is the deliberate simplification the user requested — with speckit owning clarify/specify, the parallel factory spec command is redundant and its removal is core to the unified entry.

**Independent Test**: Can be tested by invoking the factory without any `spec-run` step and completing a full folder-driven `dev-run` to PR; the previous `spec-run` command no longer being part of the documented/required flow.

**Acceptance Scenarios**:

1. **Given** the unified flow, **When** a user creates a spec folder (via speckit) and runs `dev-run <name>`, **Then** no factory `spec-run`/`spec_version_id` is required.
2. **Given** the removed command, **When** `spec-run` is invoked, **Then** the command is **hard removed** (no longer exposed in `[project.scripts]`, no deprecated redirect shim) and any invocation fails cleanly; no factory workflow depends on it.

### Edge Cases

- What happens when the spec folder exists but is missing one of the required artifacts (`spec.md`, `plan.md`, or `tasks.md`)? The system should detect the missing/partial artifacts and return a clear error rather than proceeding with incomplete context.
- What happens when the folder name resolves but the `plan.md` has no technical decisions (architecture/security sections)? The assessment should degrade gracefully and note that the assessment is inferred from available artifacts.
- What happens when the `tasks.md` references file paths outside the repository or absolute host paths? The adapter should normalize/drop paths that are absolute or out-of-repo and flag a warning.
- What happens when a `spec_version_id`/`SpecVersion` traceability is needed downstream (e.g., for reporting)? The folder name (and its feature id) becomes the stable reference; behavior for any still-required identity should be defined.
- What happens to the existing integration tests that currently depend on `spec-run`/`spec-workflow`/`handoff`? They must be migrated to drive the folder-driven entry.
- What happens when the `git` `SpecSource` has no usable credential or delivers untrusted/malicious source-repo content? The factory reuses the caller's existing git host client (no factory-managed secret store); content read from the source repo is validated/sanitized before any write-back, and a missing/invalid credential surfaces a clear non-zero error rather than a silent fallback (FR-012).
- What happens when the same speckit `tasks.md` is mutated (completion marks) while its folder is the contract? The dev-workflow MUST treat only the checkbox state of the task it derived (`- [ ]` → `- [x]`) as writable; it MUST NOT re-derive or rewrite requirement content (preserving FR-005). Concurrent writes are avoided by single-writer-per-folder and by marking at task granularity, not the whole file.
- What happens when a task's completion condition is ambiguous (e.g. it does not clearly state fail or pass)? The dev-workflow SHOULD NOT mark it completed purely on a single uniform rule; it must record an unresolved/incomplete status and require the task's intended outcome to be resolvable (fail-expected vs pass-expected) before flipping the checkbox (FR-010; sharpened further by task-type routing in a follow-on pass).
- What happens when the spec source is a different repository? The dev-workflow MUST resolve the `SpecSource` (same-repo default, or `--spec-source git:...`) and read the artifacts from the source repo; it MUST NOT write the completion mark to its own working directory's `tasks.md`. It updates the source repo's `tasks.md`, delivering the completion diff **via PR** per phase (phase PR with code, or a dedicated `*-tasks-md` PR) — **never a direct push to the source repo's origin branch** — and never rewriting requirement content (FR-011, FR-012, SC-009).
- What happens when a `dev-run` is invoked on a folder whose `tasks.md` is **fully completed** (`- [x]` on every task)? Default is idempotent: exit 0, no re-execution, no PR (FR-014a).
- What happens when a task selector (`T###`/list/range/`T3-`) references a task id that does **not** exist in `tasks.md`? The selector should error clearly (non-zero), not silently match nothing.
- What happens when a targeted scope (`T3-T7`) omits earlier uncompleted tasks? A **prerequisite warning** (non-blocking) lists those tasks; only the selected tasks run (FR-014c).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a spec folder name as the primary `dev-run` argument and resolve it against the `specs/` directory.
- **FR-002**: System MUST read the folder's `spec.md`, `plan.md`, and `tasks.md` (speckit artifacts) and use them as the source of truth for a `dev-run`.
- **FR-003**: System MUST derive the `TechnicalPlan` subtasks' `files` from the `tasks.md` file paths, and the subtasks' `acceptance_criteria` from the `spec.md` functional requirements.
- **FR-004**: System MUST import the technical assessment (complexity, risk, architecture impact, security surface, documentation required) from the folder's `plan.md` when present, rather than re-deriving it only from `spec.md` content.
- **FR-005**: System MUST NOT re-derive or re-clarify requirements inside the factory; clarification/review is the responsibility of the external speckit `clarify` skill, assumed already run. The factory likewise MUST NOT generate missing lower-level artifacts: a folder must be **complete** (`spec.md`, `plan.md`, `tasks.md` all present) before `dev-run` runs, and missing artifacts are the responsibility of the external speckit `plan`/`tasks` skills (Option C; resolves the "enter at any level" intent of the feature description — entry is at the folder level, and artifact generation below it is external).
- **FR-006**: System MUST remove the independent `spec-run` command and the factory `spec-workflow` from the required entry path, and no factory flow depends on producing a `SpecVersion`/`spec_version_id` beforehand.
- **FR-007**: System MUST return a clear, non-zero exit code when the requested folder cannot be resolved, or when any of the **required** artifacts (`spec.md`, `plan.md`, `tasks.md`) is missing or unparsable. Optional files (`data-model.md`, `contracts/`, `checklists/`, `research.md`) never gate the run.
- **FR-008**: System MUST normalize file paths referenced in `tasks.md`, dropping absolute/host paths and out-of-repo references with a warning.
- **FR-009**: System MUST migrate existing integration tests that depend on `spec-run`/`spec-workflow`/`handoff` to the folder-driven entry point.
- **FR-010**: System MUST mark a speckit task as **completed** in the **source repo's** `tasks.md` (`- [ ] T###` → `- [x] T###`) when the `TechnicalSubtask` derived from it finishes, writing back to `specs/<folder>/tasks.md`. "Finishes" is interpreted per the task's stated intent — it is **not** a single uniform criterion:
  - a task that describes generating/verifying a **failing test** (TDD Red, e.g. "Write failing … tests") completes when the test **exists and fails for the expected reason** (Red verified) — **not** when it passes;
  - a task that describes a **passing** test/validation (TDD Green) completes when it passes;
  - an **implement** task completes when code + review + associated tests pass.
  The checkbox flips only when that task-specific completion condition is met.
- **FR-011**: System MUST resolve the spec source (`SpecSource`) by origin, not only by a path relative to the dev-run process's working directory: it MAY point at a spec in the **same repository** (default, `specs/<name>/` on disk) or in a **different repository** (multi-repo) via an explicit spec source. When the spec lives in another repo, the system MUST locate and read `spec.md`/`plan.md`/`tasks.md` from that repo's `specs/<name>/`, and the completion write-back (FR-010) MUST update the `tasks.md` **in that source repo** — not the directory where the dev-workflow runs.
- **FR-012**: When the spec source is another repository (multi-repo), system MUST support a `git` `SpecSource` (`--spec-source git:...`) for delivery of the completion write-back, and MUST deliver the `tasks.md` completion diff to the source repo **via a pull request** — never by pushing directly to the source repo's origin branch. Delivery SHALL be **per phase/increment**, so a multi-phase feature yields a **sequence of small reviewable PRs** rather than one huge PR:
  - **phase PR** (preferred when the dev-run opens implementation PRs on the source repo): at each phase (user-story/phase) boundary, a new branch carries **code + the `tasks.md` completion marks for that phase**, merged as one PR; over a long feature this produces many small PRs;
  - **dedicated PR** (when there is no code PR on the source repo, or separation is required): a new branch (`ai-factory/<feature>-tasks-md`) is created and a PR carrying **only** the `tasks.md` completion diff for the phase is opened.
  Where a phase is disproportionately large, it may be split so each PR stays a reviewable increment, but the default grouping is by phase boundary, **not** by a fixed count of tasks. Both modes reuse the existing git host client; the source repo is never mutated outside a merged PR. For the `git` mode, the system SHALL reuse the caller's existing git host client credentials (the factory does not manage its own tokens/secrets), and SHALL validate/sanitize any content read from the source repo before it is used or written back — the source repo is treated as untrusted input for write-back (FR-012, SC-011).
- **FR-013**: System MUST route each `TechnicalSubtask` by its `source_task_type`, derived from the describing speckit task, rather than forcing every subtask through the generic code pipeline. `test` tasks (that write or assert a test, e.g. "Write failing …") route to the test-engineering/test-running capability, **not** the code-worker; `implement` tasks route through the normal code-worker + review + tests pipeline; `validate` tasks (quickstart/checklist) route to a validation step. Record the resolved type on the subtask (per FR-010 completion criteria) and on telemetry.
- **FR-014**: System MUST support resuming an interrupted folder-driven `dev-run` such that already-completed subtasks are **skipped** (not re-executed) while pending subtasks continue, preserving the completion marks already written back (FR-010). This formalizes the factory baseline's `--resume` behavior for the folder-driven entry point.
- **FR-014a**: By **default**, a fresh `dev-run <folder>` is **idempotent**: tasks already marked completed (`- [x] T###`) in the source `tasks.md` are **skipped** (marks preserved, content untouched) and only uncompleted tasks run. If **all** tasks are already completed, the run exits 0 as a **no-op with no PR** ("nothing to do"). `--force` re-executes selected tasks even when already marked `- [x]` (re-verify); requirement re-derivation (FR-005) remains forbidden.
- **FR-014b**: System MUST accept an optional **task selector** argument on `dev-run <folder>` that filters exactly which tasks execute (applied as a filter on the normal run, not a separate mode): single task `T###`, a list `T3,T5`, a range `T3-T7`, or an open checkpoint range `T3-` (that task and all later). Exactly the selected tasks run; write-back flips only their `- [x]` marks. A targeted scope that produces code opens its **own small PR** (consistent with per-phase grouping, SC-009/FR-012). `--resume` is equivalent to selecting the open range from the first uncompleted task.
- **FR-014c**: When a task selector omits earlier tasks (e.g. `T3-T7` while `T2` is still pending), the planner MUST emit a **prerequisite warning** (non-blocking) listing the uncompleted tasks ordered before the selected range, so skipped work is surfaced without aborting the targeted scope.
- **FR-014d**: When a task is **skipped** because it is already marked completed (`- [x] T###`) in the source `tasks.md` (default idempotent skip, FR-014a) or is pruned because an explicit `--selector` selected it but it is already complete, the runner MUST emit a **non-blocking skip warning** that names each pruned task and the reason ("already complete" / "not selected"), so a skipped completion is never silent. This warning is informational only: it must not abort the run, must not trigger a PR by itself, and must not alter the preserved `- [x]` marks. `--force` re-running a completed task must NOT emit a skip warning (the task is intentionally re-executed).
- **FR-015**: System MUST emit per-role telemetry from the folder-driven `dev-run` path (role, model, capability level, tokens, cost, latency, retries, errors, escalations, result), asserting that no secret-looking values are logged and honoring the soft budget (`overspend`) signal. This formalizes the factory baseline's observability behavior for the folder-driven entry point.

### Key Entities *(include if feature involves data)*

- **Spec Folder**: A directory under `specs/<name>/` containing speckit-generated artifacts (`spec.md`, `plan.md`, `tasks.md`, and optionally `data-model.md`, `contracts/`, `checklists/`).
- **`spec.md`**: The feature specification (user stories, edge cases, functional requirements, success criteria, assumptions).
- **`plan.md`**: The implementation plan carrying the architectural/technical decisions (technical context, project structure, constitution check, design details).
- **`tasks.md`**: The dependency-ordered task list, with each task carrying explicit file paths and phase grouping; also serves as the **progress ledger** (each `- [ ] T###` checkbox) and scoping source for the task selector.
- **Task selector**: the optional `dev-run` scope argument (`T###`, `T3,T5`, `T3-T7`, or `T3-`) that filters exactly which tasks execute (FR-014b).
- **`TechnicalPlan`** (factory model): the internal plan produced by the adapter — `goal`, `assessment`, `subtasks` (each with `title`, `description`, `files`, `acceptance_criteria`), and optional `adr`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can complete a full `dev-run <folder>` to a merge-ready pull request using only `spec.md`, `plan.md`, and `tasks.md` — with no factory spec command.
- **SC-002**: 100% of spec folder entries resolve the folder or return a clear non-zero error; there is no silent fallback to a missing folder.
- **SC-003**: For every `dev-run`, the `TechnicalPlan` subtask `files` match the `tasks.md` file paths that are in-repo (100% of in-repo paths carried; absolute/host paths excluded with a warning).
- **SC-004**: The acceptance criteria carried into subtasks derive from `spec.md` functional requirements without factory-side re-clarification (100% of FRs represented).
- **SC-005**: The technical assessment reflects the `plan.md` decisions (architecture/security) rather than false-negative keyword misses, for the reference folders validated.
- **SC-006**: The existing integration suite passes after migration (no tests remain that are blocked on the removed `spec-run`).
- **SC-007**: When a `dev-run` completes each subtask, the originating speckit task in the source `tasks.md` transitions to completed (`- [x]`); a partial/terminated run leaves finished tasks marked and unfinished ones pending.
- **SC-007a**: A fresh `dev-run <folder>` on an **all-completed** folder exits 0 and opens **no PR** (no re-execution); a `--force` run re-executes the selected tasks (FR-014a).
- **SC-007b**: A `dev-run <folder> T3-T7` (or list/`T3-`) executes **exactly** the selected tasks, flips only their `- [x]` marks, and produces a small PR for that scope; an all-complete targeted scope is a no-op (FR-014b).
- **SC-007c**: Whenever a task is skipped as already-complete (default skip) or pruned by a selector, the run output names the pruned task(s) with the reason, non-blockingly; a `--force` re-run of a completed task produces **no** skip warning (FR-014d).
- **SC-008**: A task that declares an expected test failure (`Write failing …`) is marked completed only when the test is present and fails for the expected reason; a task that declares a `passing` expectation is marked completed only when it passes — the checkbox reflects the task's stated intent, not a single pass/fail default.
- **SC-009**: When the spec source is another repository (multi-repo), the completion write-back lands in the **source repo's** `tasks.md` via a pull request per **phase boundary** (a new branch carrying code + that phase's `tasks.md` marks, or a dedicated `*-tasks-md` PR when no code PR exists); a long feature yields a **sequence of small PRs**, not one huge one, and the origin branch of the source repo is never pushed to directly (FR-011/FR-012).
- **SC-010**: For every `dev-run`, a `test`-typed task is handled by the test capability and a test task whose description expects a failure is marked completed only on Red verification — the wrong-capability path (test task through code-worker) is never taken (FR-013).
- **SC-011**: For every `dev-run` with a `git` `SpecSource`, credentials are reused from the caller's existing git host client (no factory-managed tokens), and all source-repo content is validated/sanitized before write-back — no source-repo content is ever written back unvalidated (FR-012).

## Assumptions

- **Speckit owns specify/clarify**: The speckit skill (specifically `clarify`, runnable multiple times) is responsible for reviewing and refining a spec to approval. The factory consumes the result and assumes it is ready.
- **Folder is the contract**: The `specs/<name>/` folder — not a factory `SpecVersion`/`spec_version_id` — is the stable identity and entry contract for a `dev-run`.
- **Artifacts are complete**: A folder must contain `spec.md`, `plan.md`, and `tasks.md` before `dev-run` runs; otherwise resolution errors (FR-007). See FR-005 for the complete-folder / external-bootstrap rule (Option C).
- **Idempotent, non-destructive runs**: `dev-run` is idempotent by default (skip `- [x]` tasks), treats `tasks.md` as both plan and progress ledger, and supports task-selector scoping (single/list/range/`T3-`); already-completed work is never re-executed unless `--force` is given (FR-014a/b/c).
- **Assessment may be partial**: If `plan.md` lacks explicit technical decision sections, the assessment degrades gracefully from available artifacts and notes the inference (edge case), rather than failing the run.
- **Test migration**: The integration tests for `spec-workflow`/`handoff` are rewritten to exercise the folder-driven entry; this is in scope and scheduled.
- **Removal is via the command surface**: `spec-run` is hard removed from `[project.scripts]` and the `spec-workflow` modules are retired (no deprecation shim or redirect); residual identity mapping to a folder feature id is preserved. Asserted in US3 Acceptance Scenario 2 (FR-006, Option A).
- **Git-source authentication & trust**: For a `git` `SpecSource`, the factory reuses the caller's existing git host client credentials (it does not manage its own tokens/secrets); the source repo is treated as untrusted input and its content is validated/sanitized before any write-back (FR-012, SC-011).
- **Dependency**: Success assumes the ability to parse speckit markdown artifacts (`spec.md`, `plan.md`, `tasks.md`) into factory models reliably (parser/adapter), and that the existing `TechnicalPlanner`, `code_worker`, `test`/review/security pipeline continue to operate on the derived `TechnicalPlan`.
