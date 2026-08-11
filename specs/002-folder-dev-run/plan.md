# Implementation Plan: Folder-Driven Dev Run

**Feature Branch**: `002-folder-dev-run`

**Date**: 2026-08-09

**Spec**: [spec.md](./spec.md)

## Summary

Replace the factory's two-step entry (spec-workflow produces a
`SpecVersion`/`spec_version_id`, then `dev-run` consumes it by reference)
with a **single, folder-driven entry**: `dev-run <folder>` resolves
`specs/<folder>/` and reads the speckit artifacts (`spec.md`, `plan.md`,
`tasks.md`) directly, producing a `TechnicalPlan` and driving the existing
implementation pipeline to a merge-ready PR.

This simplifies the product and removes the factory duplicate of speckit's
own specify/clarify. Requirement review/refinement is **owned by the speckit
`clarify` skill** (runnable multiple times); the factory assumes a ready
folder and **never re-derives or re-clarifies requirements** (FR-005).

## Technical Context

- **Entry point (CLI)**: `dev-run <folder> [options]` — the folder is
  resolved under `specs/<folder>/` (FR-001/002). The output is a
  factory-opened `PullRequest`; exit codes `0` delivered, `4` failed
  delivery, `5` stopped-human. `spec-run`/`spec-workflow` removed from the
  required entry (FR-006).
- **Adapters**: the core new machinery is a **speckit→factory adapter**
  (folder → `TechnicalPlan`). It is a pure, deterministic, network-free
  library (`src/ai_factory/shared/folder_adapter/`) following the
  library-first rule; it composes the existing planner/workflow nodes.
- **SpecSource (FR-011/012)**: the source folder is resolved by **origin**, not
  only the working directory. `local` (default `specs/<name>/` or
  `--spec-source path:...`) climbs; `git` (`--spec-source git:<url>#branch`)
  clones the source repo, reads its `specs/<name>/`, and delivers the
  `tasks.md` completion diff back **via PR** — per-phase incremental PRs
  (phase PR preferred, dedicated `*-tasks-md` PR) — never a direct push to
  origin. `local` climbs its own path; `git` clones and delivers via PR. For
  `git`, the adapter **reuses the caller's existing git host client
  credentials** (no factory-managed secret store) and treats the source repo as
  **untrusted input**, validating/sanitizing its content before any write-back
  (FR-012, SC-011; clarified, Option D).
  - **Git backend note**: the deterministic `git_source` library validates/
    parses the source and binds a `GitSource`, but performing an actual
    network `git clone` requires a provisioned git backend through the
    sandbox. Absent one (e.g. offline or unit-test contexts), `dev-run` fails
    fast with a clear message — it never silently falls back to a local
    folder. Offline/deterministic runs use the `local`/`path:` origin.
- **Key question resolved in research**: how the adapter maps speckit
  markdown artifacts into the factory's internal models:
  - `spec.md` functional requirements → subtask `acceptance_criteria` (FR-003)
  - `plan.md` technical decisions → `TechnicalAssessment` (FR-004; imported,
    not re-derived only from `spec.md` — fixing the validated false-negatives)
  - `tasks.md` units → `TechnicalSubtask` `files` + ordering (FR-003)
  - paths normalized; absolute/out-of-repo paths dropped (FR-008)
- **Decision**: rather than reinvent, the adapter reuses the existing
  `TechnicalPlanner` model types (`TechnicalPlan`, `TechnicalSubtask`,
  `TechnicalAssessment`) and feeds them content parsed from the speckit
  artifacts. This avoids a parallel model set.
- **Identity/traceability**: the folder feature-id (e.g. `002-folder-dev-run`)
  becomes the stable dev-run identity; `spec_version_id`/`spec_run_id` are no
  longer required upstream inputs (FR-006). A derived stable string is kept
  for downstream reporting where needed.
- **Completed-task skip & warnings (FR-014a/b/c/d)**: by default tasks already
  marked `- [x]` in `tasks.md` are skipped (idempotent, FR-014a); an explicit
  selector narrows scope (FR-014b); an omitted earlier uncompleted task
  surfaces a **non-blocking** prerequisite warning (FR-014c); and any
  skipped/pruned completed task surfaces a **non-blocking** `skip_warnings`
  notice (named task + reason) in `dev-run` output — never under `--force`
  (FR-014d/SC-007c).
- **Task-type routing (FR-013)**: each `TechnicalSubtask` carries a
  `source_task_type` (`test` | `implement` | `validate`) derived from its
  describing speckit task. The orchestrator selects the capability path from
  it: `test` → test-engineering/test-running (not code-worker); `implement` →
  code-worker + review + tests; `validate` → a validation step. This prevents
  a test task from being routed through the generic code-worker (TDD
  Red/Green integrity).
- **No re-derivation invariant (FR-005)**: the factory must not parse
  requirements semantically to "improve" them; it only maps/carries the
  already-committed decisions from the artifacts. A folder must be **complete**
  (`spec.md`, `plan.md`, `tasks.md`) before `dev-run` runs; missing lower-level
  artifacts are originated by the external speckit `plan`/`tasks` skills, never
  auto-generated by the factory (clarification Option C).
- **Idempotency, task selector, and no-op gate (FR-014a/b/c, SC-007a/b)**:
  `dev-run` is **idempotent by default** — tasks already marked `- [x]` in
  `tasks.md` are skipped (marks preserved, content untouched) and only
  uncompleted tasks run; a fully-completed folder exits `0` as a **no-op with
  no PR**. An optional **task selector** narrows the run to exactly the
  selected tasks (single `T###`, list `T3,T5`, range `T3-T7`, or open
  checkpoint range `T3-`); write-back flips only the selected `- [x]` marks;
  each code-producing scope opens its **own small PR** (per-phase grouping,
  SC-009). `--force` re-executes the selected tasks even when already marked;
  `--resume` equals "open range from the first uncompleted task". A selector
  referencing an unknown task id errors non-zero; omitting earlier uncompleted
  tasks emits a **prerequisite warning** (non-blocking, FR-014c). Selector
  parsing + the default-skip filter and no-op short-circuit are added to the
  `folder_adapter`/`orchestrator` library and covered by unit + integration
  tests (Red–Green–Refactor).
- **Testing**: `pytest`; `pytest -m integration` runs the folder-driven
  `dev-run` end-to-end against fixture folders. Existing tests that depend on
  `spec-run`/`handoff` are migrated (FR-009).

### Eliminated/incompatible decisions (supercedes 001)

- `spec_version_id` as the sole join key between spec and dev workflows.
- The `spec-workflow` (`spec_agent`, `requirements_reviewer`, human-approval
  `interrupt`) as a required upstream stage — clarif is external now.

## Constitution Check

The repository's constitution (embedded in `AGENTS.md`) is reviewed against
this design:

1. **Library-First** ✅ — The folder adapter is a standalone library
   (`folder_adapter`), testable in isolation; existing dev-role libraries
   remain unchanged. The `TechnicalPlanner` models are reused, not duplicated.
2. **CLI Interface** ✅ — `dev-run` keeps JSON + human output and meaningful
   exit codes. `spec-run` removal is additive at the command surface.
3. **Test-First** ✅ — New adapter is developed with failing tests first
   (parse mappings, path normalization, artifact-missing errors, assessment
   import). No merge without passing tests.
4. **Integration Testing** ✅ — `tests/integration/` drivers a folder-driven
   `dev-run` end-to-end; a fixture spec folder provides the artifacts.
5. **Simplicity & Observability** ✅ — The change removes a workflow, adding
   one library. Per-role telemetry continues to be emitted.

**Gates**: no principle violation — the change is consistent with
library-first and only removes an entry point, never the underlying role
libraries.

## Project Structure

### Documentation (this feature)

```
specs/002-folder-dev-run/
├── spec.md                       # feature spec (FR-001..015)
├── data-model.md                 # folder-as-contract + adapter models
├── plan.md                       # this plan
├── research.md                   # adapter parsing/assessment research
├── quickstart.md                 # folder-driven dev-run validation guide
├── checklists/requirements.md    # spec quality checklist
└── contracts/
    ├── dev-run-cli.md            # changed dev-run contract (folder entry)
    ├── spec-run-cli.md           # spec-run removal record
    └── README.md                 # contracts index
```

### Source Code (repository root)

```
src/ai_factory/
├── cli/
│   ├── dev_run.py                # changed: <folder> arg + folder resolution
│   └── spec_run.py               # REMOVED from [project.scripts]
├── shared/
│   └── folder_adapter/           # NEW: folder → TechnicalPlan (library)
│       ├── __init__.py
│       ├── resolve.py            # resolve specs/<folder>/, validate artifacts
│       ├── spec_source.py        # FR-011: resolve source by origin (local | git)
│       ├── git_source.py         # FR-012: clone source repo; deliver tasks.md diff via per-phase PR (preferred)
│       ├── parse_spec.py         # spec.md → acceptance criteria/edge cases
│       ├── parse_plan.py         # plan.md → TechnicalAssessment
│       ├── parse_tasks.py        # tasks.md → TechnicalSubtask list + order (+ source_task_id, FR-010)
│       ├── selector.py           # FR-014b: parse T###/list/T3-T7/T3- task selector (single/list/range/open-range)
│       ├── task_filter.py        # FR-014a/b/c: default-skip of -[x] tasks, --force override, no-op short-circuit, prerequisite warnings
│       ├── build_plan.py         # assemble TechnicalPlan
│       └── mark_completed.py     # FR-010: mark a source task - [ ] → - [x] in tasks.md
├── dev_workflow/                 # unchanged internals (planner/orchestrator/…)
└── spec_workflow/                # hard removed (no deprecation shim; clarification Option A)
```

**Write-back (FR-010, SC-007)**: `parse_tasks.py` captures each subtask's
originating speckit task id as `source_task_id`. On successful completion of
a `TechnicalSubtask`, `mark_completed.py` flips that task's checkbox in the
source `specs/<folder>/tasks.md` (`- [ ] T###` → `- [x] T###`). Only the
checkbox of the derived task is writable; requirement text is never re-derived
or rewritten (preserves FR-005). Single-writer-per-folder; marking happens at
task granularity so a partial/terminated run leaves finished tasks marked and
pending ones unmarked (SC-007). When the source is **another repo** (`git`
`SpecSource`, FR-011/012), the checkbox flip happens on the temporary clone and
is delivered back to the source repo **via PR** — a **phase PR** (code + that
phase's `tasks.md` marks, opened at each phase boundary) if the dev-run opens
an implementation PR there, else a dedicated `*-tasks-md` PR — never a direct
push to origin.

## Complexity Tracking

- Expected **technical complexity**: standard-to-complex. The adapter is a new
  parse/map layer; the fiddliest part is tolerating varied speckit markdown
  (headings, task formats, absolute paths) and maintaining the no-re-derivation
  invariant.
- **Risk areas**: (1) layout/structure differences between speckit-producers
  could break parsing → normalize keys and keep a fixture corpus; (2) removing
  `spec-run` breaks existing integration tests until migrated (FR-009);
  (3) partial `plan.md` without explicit decision sections → assessment must
  degrade gracefully.
- **Scope** is bounded to the folder-driven entry and adapter; the underlying
  dev-role pipeline is untouched. Removals are command-surface and import
  only.
