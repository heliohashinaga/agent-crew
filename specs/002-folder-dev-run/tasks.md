# Tasks: Folder-Driven Dev Run

**Branch**: `002-folder-dev-run` | **Date**: 2026-08-09 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

**Implementation strategy**: the factory already exists (`001-ai-dev-factory`
delivered), so this feature is an **additive library + a CLI contract change +
a removal**. The `folder_adapter` library is the foundational, blocking piece
(Phase 2) that every user story depends on. MVP first (US1 — folder entry +
error paths), then assessment fidelity (US2), then removal + test migration
(US3). The constitution mandates TDD (Red–Green–Refactor) as NON-NEGOTIABLE,
so every library gets a failing test before its implementation. Library-First
+ CLI Interface: the adapter is a standalone, independently testable library;
`dev-run` composes it. In addition to the core adapter, Phase 2 now includes
**task selector parsing, default-skip/no-op filtering, and prerequisite
warning detection** (FR-014a/b/c, SC-007a/b, tasks T053–T059) and US1 wiring
for the idempotent re-run / `--force` / per-scope-PR paths (T060–T061), mirroring
what was clarified into the spec/plan/contract.

## User Stories (from spec.md)

- **US1 (P1)** — Run the Dev Workflow from a Spec Folder Name
- **US2 (P1)** — Consume an Existing Spec/Plan/Task (assessment imported from plan.md)
- **US3 (P1)** — Remove spec-run and the spec-workflow Entry Point (migrate tests)

## Dependencies (user story completion order)

```text
[Phase 1: Setup: fixture corpus + env]
   └─→ [Phase 2: Foundational: folder_adapter library (resolve + parse + normalize + build)]
          └─→ US1 (dev-run <folder> entry + error paths)          ← MVP
                └─→ US2 (assessment import from plan.md; fidelity)
                      └─→ US3 (remove spec-run/spec-workflow + migrate integration tests)
                            └─→ [Polish: quickstart validation, CI, audit]
```

- Phase 2 (the `folder_adapter` library) is the blocking prerequisite for all
  user stories — every `dev-run` enters through it.
- US1 is the MVP: folder resolution, artifact validation (fast-fail, FR-007),
  and a working `dev-run <folder>` → PR path.
- US2 depends on US1 (needs the adapter wired in) and adds plan.md→assessment
  fidelity (FR-004, fixing the validated false-negatives).
- US3 depends on US1/US2 being stable (so removal does not break the running
  flow) and migrates the spec-workflow/handoff integration tests (FR-009).

---

## Phase 1: Setup

- [x] T001 Create a fixture speckit folder corpus under `tests/fixtures/specs/` (one full-featured, one readable example with absolute-path noise, one missing `plan.md`, one missing `tasks.md`) in `/home/helio/repos/ai-factory/tests/fixtures/specs/`
- [x] T002 Verify the repository environment (`uv sync`, `uv run pytest -q` green baseline, `uv run ruff check .` clean) in `/home/helio/repos/ai-factory/`
- [x] T003 Confirm `spec-run` still present/working as a baseline before removal (exit 0/2/3 with `--auto-approve`) in `/home/helio/repos/ai-factory/`

## Phase 2: Foundational (blocking prerequisites for all user stories)

The `folder_adapter` library at `src/ai_factory/shared/folder_adapter/` (per
plan.md source structure + research.md decisions). Library-first, TDD.

- [x] T004 [P] Write failing test for folder resolution (`resolve()`) — resolves `specs/<name>/`, validates `spec.md`/`plan.md`/`tasks.md` present, raises on missing artfact — in `tests/unit/shared/folder_adapter/test_resolve.py` (FR-001, FR-002, FR-007)
- [x] T005 [P] Implement folder resolution and artifact validation in `src/ai_factory/shared/folder_adapter/resolve.py` (FR-001, FR-002, FR-007)
- [x] T006 [P] Write failing test for `parse_spec.py` — derive subtask `acceptance_criteria` from `spec.md` Functional Requirements (1:1 carry, no re-derivation) — in `tests/unit/shared/folder_adapter/test_parse_spec.py` (FR-003, FR-005)
- [x] T007 [P] Implement `spec.md` parsing (functional requirements → acceptance criteria; edge cases) in `src/ai_factory/shared/folder_adapter/parse_spec.py` (FR-003, FR-005)
- [x] T008 [P] Write failing test for `parse_tasks.py` — map `tasks.md` units to `TechnicalSubtask` (`title`, `description`, `files`, `acceptance_criteria`, `source_task_type`), preserve order, detect shared-file non-parallel — in `tests/unit/shared/folder_adapter/test_parse_tasks.py` (FR-003, FR-013)
- [x] T009 [P] Implement `tasks.md` parsing into `TechnicalSubtask` list (order + shared-file detection + capture each task's `source_task_id` T### for FR-010 write-back + derive `source_task_type` test|implement|validate for FR-013 routing) in `src/ai_factory/shared/folder_adapter/parse_tasks.py` (FR-003, FR-010, FR-013)
- [x] T010 [P] Write failing test for path normalization — absolute host paths and out-of-repo references dropped, in-repo carried, warning emitted — in `tests/unit/shared/folder_adapter/test_parse_tasks.py` (FR-008, SC-003)
- [x] T011 [P] Implement path normalization (drop absolute/out-of-repo; flag shared-file non-parallel) in `src/ai_factory/shared/folder_adapter/parse_tasks.py` (FR-008, SC-003)
- [x] T012 [P] Write failing test for `parse_plan.py` — `TechnicalAssessment` imported from `plan.md` (complexity/risk/architecture/security/test-scope/docs); degrade to default + inference note when a section is absent — in `tests/unit/shared/folder_adapter/test_parse_plan.py` (FR-004, SC-005)
- [x] T013 [P] Implement `plan.md` → `TechnicalAssessment` import (project structure, design/security sections, complexity) in `src/ai_factory/shared/folder_adapter/parse_plan.py` (FR-004, SC-005)
- [x] T014 Write failing test for `build_plan.py` — assemble a complete `TechnicalPlan` (`goal`, `assessment`, `subtasks`, optional `adr`; identity from folder feature id) from parsed artifacts — in `tests/unit/shared/folder_adapter/test_build_plan.py` (FR-001..004, research Decision 5)
- [x] T015 Implement the `TechnicalPlan` assembler (folder → complete `TechnicalPlan`; no re-derivation invariant) in `src/ai_factory/shared/folder_adapter/build_plan.py` (FR-001..004, FR-005)
- [x] T016 [P] Write failing test for `mark_completed.py` — flips `- [ ] T### → - [x] T###` only for the task's intended outcome (fail-expected Red vs pass Green); does not rewrite content; partial-run leaves unfinished pending — in `tests/unit/shared/folder_adapter/test_mark_completed.py` (FR-010, SC-008)
- [x] T017 [P] Implement `mark_completed.py` write-back (checkbox flip per derived `source_task_id` and task-intent completion condition; single-writer; content untouched) in `src/ai_factory/shared/folder_adapter/mark_completed.py` (FR-010, SC-007, SC-008)
- [x] T018 [P] Write failing test for `spec_source.py` — resolves the source folder by origin: `local` (default `specs/<name>/` or `--spec-source path:...`) and `git` (`--spec-source git:<url>[#branch]`) returns the source repo target — in `tests/unit/shared/folder_adapter/test_spec_source.py` (FR-011)
- [x] T019 [P] Implement `spec_source.py` (parse `SpecSource` modes local|git; return where artifacts must be read) in `src/ai_factory/shared/folder_adapter/spec_source.py` (FR-011)
- [x] T020 [P] Write failing test for `git_source.py` — resolves credentials by reusing the caller's existing git host client (no factory-managed secret store); treats the source repo as untrusted input and validates/sanitizes its content before write-back (SC-011); clones the source repo, reads `specs/<folder>/`, delivers the `tasks.md` completion diff via per-phase PR (phase PR with code, or dedicated `*-tasks-md` PR); never pushes to origin; a missing/invalid credential surfaces a clear non-zero error — in `tests/unit/shared/folder_adapter/test_git_source.py` (FR-012, SC-009, SC-011)
- [x] T021 [P] Implement `git_source.py` (reuse the caller's existing git host client credentials — no factory-managed secret store; clone source repo; treat the source repo as untrusted input, validating/sanitizing its content before any write-back; apply `tasks.md` completion mark per phase; deliver the phase diff via PR — phase PR or dedicated; no direct push to origin; surface a clear non-zero error on missing/invalid credential) in `src/ai_factory/shared/folder_adapter/git_source.py` (FR-012, SC-009, SC-011)

### Task selector, default-skip & no-op (FR-014a/b/c, SC-007a/b) — added on top of the core adapter

- [x] T053 [P] Write failing test for `selector.py` — parses a task selector into a filter (single `T###`, list `T3,T5`, range `T3-T7`, open range `T3-`); an empty/no selector means "all uncompleted"; a missing list captures equal contiguous ids; a reference to an id absent from `tasks.md` raises a clear parse error (does not silently match nothing) — in `tests/unit/shared/folder_adapter/test_selector.py` (FR-014b)
- [x] T054 [P] Implement task-selector parsing and validation (single/list/range/`T3-` → concrete selected `T###` set; unknown id → non-zero error; empty selector → all tasks) as a pure library in `src/ai_factory/shared/folder_adapter/selector.py` (FR-014b)
- [x] T055 [P] Write failing test for completed-state skip — a task already marked `- [x] T###` in the source `tasks.md` is **skipped** by default (marks preserved, content untouched); only uncompleted tasks run; a fully-completed plan yields an empty run set — in `tests/unit/shared/folder_adapter/test_task_filter.py` (FR-014a, SC-007a)
- [x] T056 [P] Implement the task filter that combines the parsed selector with each task's completed state (default = exclude already-`[x]` tasks; `--force` = keep selected tasks regardless of mark); expose which tasks are selected and which omitted for the prerequisite warning in `src/ai_factory/shared/folder_adapter/task_filter.py` (FR-014a, FR-014b)
- [x] T057 [P] Write failing test for the prerequisite warning — when a selector omits an earlier uncompleted task (e.g. `T3-T7` while `T2` is pending), the returned list includes that earlier pending task id; it is non-blocking (does not abort the scope) — in `tests/unit/shared/folder_adapter/test_task_filter.py` (FR-014c)
- [x] T058 [P] Implement prerequisite-warning detection (collect uncompleted tasks ordered before the selected range and surface them as a non-blocking warning list) in `src/ai_factory/shared/folder_adapter/task_filter.py` (FR-014c)
- [x] T065 [P] Implement the **non-blocking skip warning** (FR-014d/SC-007c) — surface a `skip_warnings` notice (named task + "already complete" reason) whenever a completed task is skipped by default or pruned by a `--selector`, and never under `--force`; emit it to `dev-run` stderr and to the JSON output (noop + run summary) in `src/ai_factory/shared/folder_adapter/task_filter.py` and `src/ai_factory/cli/dev_run.py`, and test in `tests/unit/shared/folder_adapter/test_task_filter.py`
- [x] T059 [P] Write failing test for the no-op short-circuit — when the task filter yields no runnable tasks (all completed, or an all-`[x]` selected scope), the plan yields an empty `ExecutionPlan` with a `nothing_to_do` signal rather than a pipeline run — in `tests/unit/shared/folder_adapter/test_task_filter.py` (FR-014a, SC-007a)

## Phase 3: User Story 1 — Run the Dev Workflow from a Spec Folder Name (P1)

**Goal**: `dev-run <folder>` resolves a `specs/<folder>/` and drives the
pipeline to a factory-opened PR. **Independent test**: run `dev-run <folder>`
against a full fixture folder (fake sandbox/host) → `delivered`, exit 0, PR
opened, `auto_merged=false`. Depends on Phase 2 (`folder_adapter`).

- [x] T022 [US1] Write failing integration test for `dev-run <folder>` happy path (folder → PR delivered, exit 0, no `spec_version_id` input) in `tests/integration/test_dev_run_folder.py` (FR-001, FR-002, FR-003, SC-001)
- [x] T023 [US1] Modify the `dev-run` CLI to accept a positional `<folder>` argument and resolve it via `folder_adapter.resolve()` under `specs/` in `src/ai_factory/cli/dev_run.py` (FR-001, FR-002)
- [x] T024 [US1] Wire `folder_adapter.build_plan()` output into the existing dev-workflow graph entry (replacing the `spec_version_id`-based `SpecVersion` input) in `src/ai_factory/cli/dev_run.py` and `src/ai_factory/dev_workflow/graph.py`
- [x] T025 [US1] Write failing integration test for the fast-fail paths — missing folder, missing artifact, unparsable artifact → clear error, non-zero exit, no pipeline — asserting the complete-folder model: a missing required artifact is an error, never auto-generated (FR-005, FR-007, SC-002) — in `tests/integration/test_dev_run_folder.py` (FR-005, FR-007, SC-002)
- [x] T026 [US1] Implement fast-fail resolution + error surfaces (clear messages, contract exit code 4) that enforce the complete-folder model — a missing required artifact errors; the factory does not generate/re-derive missing artifacts (external speckit `plan`/`tasks` skills bootstrap) in `src/ai_factory/shared/folder_adapter/resolve.py` and `src/ai_factory/cli/dev_run.py` (FR-005, FR-007, SC-002)
- [x] T027 [US1] Write failing test that the PR is NOT auto-merged and carries the folder feature id in `tests/integration/test_dev_run_folder.py` (FR-006, SC-001)
- [x] T028 [US1] Update the contract to document `dev-run <folder>` entry, resolution, artifact validation, and exit codes in `specs/002-folder-dev-run/contracts/dev-run-cli.md` (FR-001, FR-002, FR-007)
- [x] T029 [US1] Write failing integration test that a completed subtask flips its originating speckit task to `- [x] T###` in the source `tasks.md` (FR-010) and a partial run leaves unfinished pending (SC-007), and fail-expected test tasks complete on Red (SC-008) in `tests/integration/test_dev_run_folder.py` (FR-010, SC-007, SC-008)
- [x] T030 [US1] Validate US1 against quickstart Scenarios 1, 2, 5 and mark the US1 checklist item complete
- [x] T060 [US1] Write failing integration test for the no-op + selector + `--force` paths end-to-end — a fully-completed fixture folder exits 0 with **no PR**; `dev-run <folder> T3-T7` runs exactly that range and flips only its `- [x]` marks into its own small PR; `--force` re-executes already-`[x]` selected tasks; an unknown selector id errors non-zero — in `tests/integration/test_dev_run_folder.py` (FR-014a, FR-014b, FR-014c, SC-007a, SC-007b)
- [x] T061 [US1] Wire the task filter + no-op short-circuit into `dev_run.py`/`orchestrator` — parse the optional `<selector>` arg, apply the default-skip (or `--force`) filter, emit prerequisite warnings, and short-circuit to exit 0 / no PR when nothing remains to run in `src/ai_factory/cli/dev_run.py` and `src/ai_factory/shared/folder_adapter/task_filter.py` (FR-014a, FR-014b, FR-014c, SC-007a)

## Phase 4: User Story 2 — Consume an Existing Spec/Plan/Task (P1)

**Goal**: subtask `files` and `acceptance_criteria` come from the folder
artifacts; the technical `assessment` is imported from `plan.md` (not
re-derived only from `spec.md`). **Independent test**: on a fixture whose
`plan.md` declares architecture/security, `architecture_impact=True` and
`security_surface` populated (no false-negative). Depends on US1.

- [x] T031 [US2] Write failing integration test that subtask `files` match the fixture `tasks.md` in-repo paths 100% and `acceptance_criteria` carry the `spec.md` FRs in `tests/integration/test_dev_run_folder.py` (FR-003, SC-003, SC-004)
- [x] T032 [US2] Write failing integration test that the assessment reflects `plan.md` (architecture/security imported; no re-derived false-negative) in `tests/integration/test_dev_run_folder.py` (FR-004, SC-005)
- [x] T033 [US2] Assert against the reference storybook-style fixture that `architecture_impact=true` and `security_surface` is populated when `plan.md` contains an architecture/privacy section in `tests/integration/test_dev_run_folder.py` (FR-004, research Decision 2)
- [x] T034 [US2] Write failing test for partial-`plan.md` graceful degradation (missing design section → default assessment + inference note, run continues) in `tests/unit/shared/folder_adapter/test_parse_plan.py` (edge case, SC-005)
- [x] T035 [US2] Implement graceful degradation for missing `plan.md` technical sections (default + inference note; no abort) in `src/ai_factory/shared/folder_adapter/parse_plan.py` (FR-004, edge case)
- [x] T036 [US2] Write failing integration test that a `test`-typed subtask routes to the test capability (NOT the code-worker), a `test` task expecting failure completes on Red, and `implement`/`validate` route to the expected paths (FR-013, SC-010) in `tests/integration/test_dev_run_folder.py` (FR-013, SC-010)
- [x] T037 [US2] Validate US2 against quickstart Scenarios 3 and mark the US2 checklist item complete

## Phase 5: User Story 3 — Remove spec-run and the spec-workflow Entry Point (P1)

**Goal**: no factory flow depends on `spec-run`/`spec-workflow`; folder-driven
`dev-run` is the entry. **Independent test**: `spec-run` is absent from
`[project.scripts]` and removed from docs; a full folder-driven `dev-run`
completes with no `spec_version_id`. Depends on US1/US2 stable.

- [x] T038 [US3] Write failing integration test that a full `dev-run <folder>` completes with no `spec-run`/`spec_version_id` dependency in `tests/integration/test_dev_run_folder.py` (FR-006, SC-006)
- [x] T039 [US3] Remove `spec-run` from `[project.scripts]` in `pyproject.toml`
- [x] T040 [US3] **Delete** `spec_run.py` (hard removal; no deprecation shim or redirect) and remove it from the entry surface: drop the `spec-run` console script from `[project.scripts]`, remove the `spec_run_main` re-export from `src/ai_factory/cli/__init__.py`, drop `ai_factory.cli.spec_run` from the CLI-convention audit, and delete `src/ai_factory/cli/spec_run.py`. (FR-006, clarification Option A) — targets the **command surface** only; shared `spec_store` types stay for residual folder-identity mapping.
- [x] T041 [US3] **Delete** the `spec-workflow` **entry-point modules** (hard removal; no deprecated/retired entry modules remain) — remove `src/ai_factory/spec_workflow/graph.py` (the spec-workflow production graph/entry) and its imports from the entry graph; keep no factory flow that produces a `SpecVersion`/`spec_version_id` beforehand. The independently-tested spec-side **libraries** (`requirements_reviewer`, `spec_agent`) are **retained** as active libraries per Library-First (they are not entry points). (FR-006, clarification Option A)
- [x] T042 [US3] Migrate `tests/integration/test_spec_workflow.py` to drive the folder-driven `dev-run` (or remove spec-workflow-only cases) in `tests/integration/test_spec_workflow.py` (FR-009)
- [x] T043 [US3] Migrate `tests/integration/test_handoff.py` to the folder feature-id traceability (no `spec_run_id` input) in `tests/integration/test_handoff.py` (FR-009, SC-006, SC-009)
- [x] T044 [US3] Update old `001-ai-dev-factory` references and the README/AGENTS to reflect the single folder-driven command in `AGENTS.md` and `/home/helio/repos/ai-factory/README.md` (FR-006)
- [x] T045 [US3] Validate US3 against quickstart Scenario 4 and mark the US3 checklist item complete
- [x] T064 [US3] Add a test asserting the folder-driven `dev-run` **rejects/ignores** a `--spec-version` flag (and errors clearly if passed as unsupported rather than silently accepting it), and that a full folder-driven run carries **no `spec_version_id`** in its `PullRequest`/run record (single join key removed) — in `tests/integration/test_dev_run_folder.py` and `tests/unit/cli/test_dev_run_cli.py` (FR-009)

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T046 [P] Add a `--resume` end-to-end test for the folder-driven `dev-run` (interrupt → resume skips completed checkpoints) in `tests/integration/test_dev_run_folder.py` (FR-014)
- [x] T047 [P] Add a full-quickstart integration test (Scenarios 1–7) executed via the folder-driven `dev-run` in `tests/integration/test_quickstart.py`
- [x] T048 [P] Emit per-role telemetry from the folder-driven `dev-run` path (assert no secret-looking values, `overspend` on soft budget) in `tests/integration/test_dev_run_folder.py` and `src/ai_factory/dev_workflow/*/cli.py` (FR-015)
- [x] T049 [P] Update the CI workflow to run the migrated suite (`ruff` + pytest unit/contract/integration; no network in unit) in `/home/helio/repos/ai-factory/.github/workflows/ci.yml` (FR-009)
- [x] T050 [P] Audit the adapter library against the library-CLI convention (JSON + human output, meaningful exit codes) in `src/ai_factory/shared/folder_adapter/*.py`
- [x] T051 [P] Re-run the full quickstart suite for `002-folder-dev-run` (Scenarios 1–7) and mark all checklist items complete
- [x] T052 [P] Security audit of the `git` SpecSource path — confirm no secret/managed tokens, credentials delegate to the caller's host client, and source-repo content is validated before write-back (no unvalidated write-back); add a red-team case for a malicious/untrusted source repo and a missing/invalid credential (clear non-zero error, no silent fallback) in `tests/unit/shared/folder_adapter/test_git_source.py` and `src/ai_factory/shared/folder_adapter/git_source.py` (FR-012, SC-011)
- [x] T062 [P] Add a quickstart Scenario 10 validation test (idempotent re-run / no-op / `--force` / task selector, assert exit 0 no-op on all-complete, exactly-scoped execution + per-scope PR, non-zero on unknown selector id) in `tests/integration/test_quickstart.py` (FR-014a, FR-014b, FR-014c, SC-007a, SC-007b)
- [x] T063 [P] Re-run the full quickstart suite for `002-folder-dev-run` (Scenarios 1–10) and mark all checklist items complete