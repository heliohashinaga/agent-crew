# Data Model: Folder-Driven Dev Run

**Feature**: 002-folder-dev-run | **Date**: 2026-08-09 | **Spec**: [spec.md](./spec.md)

Defines the **shape** of the data the `dev-run` consumes when entering from
a speckit spec folder. This document changes the entry boundary of the
factory: it moves from a factory-produced `SpecVersion` (via `spec-run`) to a
**speckit spec folder on disk**. It does not define implementation bodies.

> **Design shift (supersedes `001-ai-dev-factory` boundary)**: Previously the
> two workflows were joined only by `spec_version_id`, produced by the factory
> `spec-workflow`. With this feature, `spec-run`/`spec-workflow` are **hard
> removed** (no longer exposed in `[project.scripts]`, no deprecation shim or
> redirect; clarified Option A), and the **folder** (`specs/<name>/`) is the
> stable contract. Traceability identity is derived from the folder feature id
> rather than a factory-issued version string.

---

## The folder as the entry contract

The unit of input is a **spec folder** at `specs/<name>/` containing speckit
artifacts:

| File | Role in `dev-run` | Required |
|------|-------------------|----------|
| `spec.md` | Source of functional requirements → subtask `acceptance_criteria`; edge cases; success criteria | Yes (FR-002) |
| `plan.md` | Source of technical decisions → technical `assessment` (complexity/risk/architecture/security/docs) | Yes (FR-002) |
| `tasks.md` | Source of implementation units → subtask `files` and ordering | Yes (FR-002) |
| `data-model.md`, `contracts/`, `checklists/` | Supporting context; optional, read if present, never required | No |

---

## `SpecSource` — where the spec folder is resolved from (FR-011)

The folder is located by **origin**, not only by a path relative to the
dev-run process's working directory. `SpecSource` has two modes:

| Mode | How it is given | Read from | Write-back target (FR-010/012) |
|------|-----------------|-----------|---------------------------------|
| `local` | default: `specs/<name>/` in the working repo, or `--spec-source path:/abs/path` | the on-disk folder | the same on-disk `tasks.md` (direct edit) |
| `git` | `--spec-source git:<repo-url>[#branch]` | a temporary clone of the source repo's `specs/<name>/` | the **source repo's** `tasks.md`, delivered **via PR** (FR-012) |

**Rules**:

- The dev-workflow reads `spec.md`/`plan.md`/`tasks.md` from the **resolved
  source repo** — its own working directory is never silently treated as the
  source when a `git` source is specified (FR-011).
- The `tasks.md` completion mark (FR-010/SC-007) is written to the **source
  repo's** `tasks.md`: for `local`, an in-place edit; for `git`, a temporary
  clone update delivered to the source repo **via PR**, never a direct push to
  its origin branch (FR-012, SC-009).
- Delivery for `git` is **per-phase PR (preferred)** (FR-012): a **per-phase PR** (a new
  branch carrying code + that phase's `tasks.md` completion marks, opened as a
  small PR at each phase boundary — yielding a sequence of small PRs over a long
  feature) is the default/recommended delivery; a **dedicated `*-tasks-md` PR** (a
  new branch `ai-factory/<feature>-tasks-md` carrying only the `tasks.md` diff) is
  the fallback for phases that are tasks-mark-only (no code PR exists). The source
  repo is never mutated outside a merged PR.
- **Credentials & trust (git mode)**: authentication **reuses the caller's
  existing git host client credentials** — the factory does not manage its own
  tokens/secrets. The `git` source repo is treated as **untrusted input**; any
  content read from it is **validated/sanitized before write-back**, so an
  arbitrary source repo cannot inject malformed/unvalidated content into the
  `tasks.md` completion diff or PR (FR-012, SC-011; clarified, Option D).

---

## Internal models produced by the adapter

### `TechnicalPlan` (unchanged factory model, new inputs)

| Field | Type | Source |
|-------|------|--------|
| `goal` | `str` | Derived slug of `spec.md` intent / title |
| `assessment` | `TechnicalAssessment` | Imported from `plan.md` decisions (FR-004) |
| `subtasks` | `list[TechnicalSubtask]` | One per `tasks.md` unit (FR-003) |
| `adr` | `Optional[ADR]` | Created only when `plan.md` indicates real architecture impact |

### `TechnicalSubtask` (flat; unchanged + write-back field)

| Field | Type | Source |
|-------|------|--------|
| `title` | `str` | From the `tasks.md` task id + clean description |
| `description` | `str` | The task description with file-path references removed |
| `files` | `list[str]` | In-repo file paths from `tasks.md` (normalized, absolute/host paths dropped — FR-008) |
| `acceptance_criteria` | `list[str]` | From the `spec.md` functional requirements (FR-003) |
| `source_task_id` | `Optional[str]` | The speckit task id (`T###`) in the source `tasks.md` this subtask originates from (FR-010); enables completion write-back |
| `source_task_type` | `Literal["test","implement","validate"]` | Derived from the describing speckit task (FR-013): `test` (writes/asserts a test), `implement` (code), `validate` (quickstart/checklist). Drives capability routing. |

> **Routing by type (FR-013)**: `source_task_type` chooses the capability path —
> `test` tasks go to the test-engineering/test-running capability (**not** the
> code-worker); `implement` tasks go through the normal code-worker + review +
> tests pipeline; `validate` tasks go to a validation step. This mirrors the
> speckit Red/Green task corpus and prevents a test task being routed through a
> generic code-worker.
>
> task id (`source_task_id`) so that the dev-workflow can mark that task as
> **completed** in the source `specs/<folder>/tasks.md` (`- [ ] T###` → `- [x] T###`)
> once the subtask finishes. Only the checkbox state of the derived task is
> writable; requirement content is never re-derived or rewritten (preserves
> FR-005).

### Completion write-back (FR-010, SC-007)

- The dev-workflow marks a task completed **when the ``TechnicalSubtask``
  deriving from it finishes successfully**, updating the source `tasks.md` in
  place (`local` mode; git/remote handling is a follow-on concern, see
  research.md).
- A partial/terminated run leaves finished tasks marked `- [x]` and unfinished
  ones `- [ ]`, matching SC-007.
- Write-back is single-writer-per-folder and operates at task granularity, not
  by rewriting the whole file.

### Completion-state read & skip (FR-014a/b, SC-007a/b)

- The adapter/orchestrator **reads** each task's checkbox state from the source
  `tasks.md` as its `completed` flag. By default a `- [x]` task is **skipped**
  (marks preserved, content untouched) and only uncompleted tasks run; a
  fully-completed folder short-circuits to exit `0` with no PR (idempotent,
  non-destructive; see CLI selector/`--force` in `contracts/dev-run-cli.md`).
- An optional **task selector** (single `T###` / list / range `T3-T7` / open
  range `T3-`) filters which tasks execute; write-back flips only the selected
  tasks' marks.

### `TechnicalAssessment` (upstream source change)

| Field | Imported from `plan.md` |
|-------|--------------------------|
| `complexity` | Complexity/design sections |
| `risk` | Risk/edge-case + security sections |
| `architecture_impact` | Architecture decisions (structure, components) |
| `security_surface` | Security/privacy design sections |
| `test_scope` | Testing/quality-gate sections |
| `documentation_required` | Documentation sections |
| `plan_summary` | Concise plan.md summary |

> **Key change**: Previously `assess()` derived these from a `SpecVersion`
> corpus (`spec.md`-only), producing false-negatives for mature specs (e.g.
> architecture/security present in `plan.md` but missed). Now the assessment
> **imports the `plan.md` decisions** rather than re-scanning only `spec.md`
> (FR-004). Where `plan.md` lacks a section, the field degrades to a default
> and a note is added (edge case).

---

## Identity & traceability

### Folder feature id as the stable reference

- The **folder name** (`<name>`, e.g. `002-folder-dev-run`) is the stable
  identity for a `dev-run`.
- `spec_version_id`/`spec_run_id` are **no longer required** upstream inputs.
  If downstream reporting still needs a stable string, it is derived as
  `<feature-id>` from the folder name (FR-006), not a factory-issued version.

### No re-derivation invariant

- The factory **MUST NOT** re-derive or re-clarify requirements (FR-005).
  Clarification/review is the speckit `clarify` skill's responsibility and is
  assumed already complete.
- The acceptance criteria are **carried** from `spec.md` FRs into subtasks as
  a 1:1 mapping, not re-inferred.

---

## Normalization of file paths (FR-008)

- Each `tasks.md` path is normalized against the repo root.
- Absolute host paths (e.g. `/home/helio/...`) and out-of-repo references are
  **dropped** from `files` and a warning is emitted; they never reach subtasks.
- Duplicate paths across tasks are preserved and signal **shared-file
  dependencies** (tasks sharing a file are not run in parallel).

---

## Edge case: partial artifacts

- If any of `spec.md`, `plan.md`, or `tasks.md` is missing, resolution **fails
  with a clear non-zero exit** (FR-007); the run does not proceed on partial
  context.
- `dev-run` NEVER generates or re-derives missing lower-level artifacts
  (FR-005, clarified Option C). Missing `plan.md`/`tasks.md` are originated by
  the **external speckit `plan`/`tasks` skills**, not by the factory; the
  folder must be complete before `dev-run` runs.
- If `plan.md` exists but lacks explicit technical decision sections, the
  assessment degrades gracefully (defaults + inference note) and the run
  continues (edge case), rather than aborting.
