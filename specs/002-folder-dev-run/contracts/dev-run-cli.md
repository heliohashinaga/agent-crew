# Contract: dev-run CLI (Development Workflow)

The Development Workflow entrypoint. Consumes a **speckit spec folder** by
name and delivers a factory-opened pull request (FR-001, FR-002, FR-003).

This contract **supersedes** the `001-ai-dev-factory` `dev-run-cli.md`: the
entry point changes from `--spec-version <id>` (factory-produced) to a
**folder name** resolved under `specs/`. `spec-run`/`spec-workflow` are no
longer required (FR-006).

## Interface

```text
dev-run <folder> [<selector>] [--force] [--sandbox fake|fake-fail|docker]
         [--git-host fake|github] [--resume <run_id>]
         [--format json|human] [--repo <path>]
         [--run-dir <path>] [--budget-cost <n>]
```

- **Input**: a `<folder>` name resolved against `specs/<folder>/` (FR-001),
  containing the speckit artifacts `spec.md`, `plan.md`, `tasks.md` (FR-002).
  The factory reads those artifacts; it **MUST NOT re-derive or re-clarify
  requirements** (FR-005) — clarification/review is owned by the speckit
  `clarify` skill, assumed already run to readiness.
- **Optional `<selector>` (task scoping, FR-014b)**: narrows the run to
  exactly the tasks matched against `tasks.md` `- [ ] T###` ids:
  - `T###` — run exactly task `T###`;
  - `T3,T5` — run exactly the listed tasks;
  - `T3-T7` — run the range `T003..T007`;
  - `T3-` — open checkpoint range: run `T003` and everything after
    (the default semantic of `--resume` is "open range from the first
    uncompleted task").
  A selector referencing a task id absent from `tasks.md` errors non-zero
  (does not silently match nothing). When a selector omits earlier
  uncompleted tasks (e.g. `T3-T7` while `T2` is pending), the planner emits
  a **prerequisite warning** (non-blocking) listing those tasks (FR-014c).

### Default skip & no-op (FR-014a, SC-007a)

- By default, tasks already marked completed (`- [x] T###`) in the source
  `tasks.md` are **skipped** (marks preserved, content untouched) and only
  uncompleted tasks run — a fresh run is **idempotent** and non-destructive.
- `--force` re-executes the selected tasks even when already marked `- [x]`
  (re-verify); it never re-derives requirements (FR-005).
- If **all** tasks are already completed (full-folder or `--resume`), the run
  exits `0` as a **no-op and opens no PR** ("nothing to do").
- Each targeted scope that produces code opens its **own small PR**
  (consistent with per-phase grouping, SC-009); write-back flips only the
  selected tasks' `- [x]` marks.
- **Output (stdout)**: a `PullRequest` record (host, branch, feature id,
  checks status, `pr_url`, `auto_merged=false`).
- **Diagnostics**: to stderr.
- **Exit codes**: `0` delivered; `4` failed delivery (folder or artifact
  missing — FR-007 — or host unreachable/bad credentials — local branch
  kept); `5` stopped-human (re-planning failed); non-zero otherwise.

## Traceability (FR-009)

The dev run's stable identity is the **folder feature id** derived from the
folder name (e.g. `002-folder-dev-run`). `spec_version_id`/`spec_run_id`
are no longer required upstream inputs. The dev run remains a distinct
top-level trace.

## Artifact → Plan derivation (FR-003, FR-004)

1. `spec.md` functional requirements → subtask `acceptance_criteria`.
2. `plan.md` technical decisions → `TechnicalAssessment`
   (complexity, risk, architecture impact, security surface, test scope,
   documentation). Imported, **not** re-derived only from `spec.md`.
3. `tasks.md` units → `TechnicalSubtask` (`title`, `description`, `files`,
   `acceptance_criteria`). Paths normalized; absolute/out-of-repo paths
   dropped with a warning (FR-008).

## Workflow (LangGraph `StateGraph`)

1. `folder_resolver` — resolves `specs/<folder>/`, validates that
   `spec.md`/`plan.md`/`tasks.md` exist (FR-007); fails fast if absent.
2. `adapter` — parses the artifacts into a `TechnicalPlan` (see
   "Artifact → Plan derivation"). Also parses the optional `<selector>`
   into the task filters (single/list/range/`T3-`) and validates that every
   referenced `T###` exists in `tasks.md`; an unknown id errors non-zero
   (FR-014b).
3. `orchestrator` — pure decision layer; applies the default skip of
   already-`[x]` tasks (or `--force` re-run), emits prerequisite warnings
   (FR-014c), and produces an `ExecutionPlan` per role (model, capability
   level, budget, timeout, parallelization, retry policy). If no task
   remains to run, short-circuits to exit `0` with no PR (FR-014a, SC-007a).
4. `code_worker` — implementation + unit tests, with local validation.
5. `code_reviewer` — validates and approves; validates ADR adherence if an
   ADR exists.
6. `test_engineer` + `test_runner` — produce and run the test suite.
7. `security_reviewer` — assesses and approves. A CRITICAL finding halts,
   triggers an immediate fix, and requires a full re-audit before merge.
8. `deliver` — opens the PR on the remote git host via the host API client.
   MUST NOT auto-merge.

## Requirements removal (FR-006)

- The independent `spec-run` command is removed from `[project.scripts]`.
- The `spec-workflow` modules are **hard removed** (no deprecation shim or
  redirect; clarification Option A); no factory flow depends on producing a
  `SpecVersion`/`spec_version_id` beforehand, and any invocation of the removed
  `spec-run` command fails cleanly.
- See `./spec-run-cli.md` for the removal record.

## Guarantees

- MUST NOT auto-merge the PR.
- MUST NOT re-derive/re-clarify requirements; consumes the ready speckit
  folder (FR-005).
- Returns a clear non-zero exit for a missing folder/artifact (FR-007).
- Normalizes paths: absolute/host and out-of-repo paths are excluded (FR-008).
- For a `--spec-source git:...` source: authenticates via the caller's existing
  git host client (no factory-managed secret store) and treats the source repo as
  untrusted input, validating/sanitizing its content before any write-back;
  a missing/invalid credential returns a clear non-zero exit (FR-012, SC-011).
- Records each `DevRoleInvocation` (telemetry) per the
  [library CLI convention](./library-cli-convention.md).
- Cost budget is soft: continue + warn + record overspend.
