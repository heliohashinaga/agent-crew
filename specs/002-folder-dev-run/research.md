# Research: Folder-Driven Dev Run

**Feature**: 002-folder-dev-run | **Date**: 2026-08-09 | **Plan**: [plan.md](./plan.md)

Résolutes the technical unknowns from the plan's Technical Context through
explicit decisions with rationale and alternatives.

---

## Decision 1: Adapter strategy — parse speckit markdown into existing factory models

- **Decision**: Add a dedicated `folder_adapter` library that **parses** the
  speckit artifacts (`spec.md`, `plan.md`, `tasks.md`) and constructs the
  **existing** factory models (`TechnicalPlan`, `TechnicalSubtask`,
  `TechnicalAssessment`) — no new parallel model set.
- **Rationale**: The validated PoC showed 100% (storybook) / 92% (ai-factory)
  of `tasks.md` units carry explicit, in-repo file paths that map 1:1 onto
  `TechnicalSubtask.files`. Reusing the existing `TechnicalPlanner` model types
  avoids model drift and keeps the downstream pipeline (orchestrator →
  code_worker → review → security → deliver) unchanged.
- **Alternatives considered**:
  - *Emit a new `FolderPlan` model*: rejected — duplicates the model, forces
    a downstream mapping layer, and risks divergence.
  - *Require factory-issued `SpecVersion`* (status quo): rejected — that is
    the entry being removed.

## Decision 2: Assessment must import `plan.md` decisions (not re-derive from `spec.md`)

- **Decision**: `TechnicalAssessment` is populated from the folder's `plan.md`
  (complexity/risk/architecture/security/test-scope/docs) when those sections
  exist, falling back to defaults + an inference note otherwise.
- **Rationale**: Validation demonstrated the current `assess()`, which scans
  only a `SpecVersion` corpus (==`spec.md`), yields **false-negatives** on
  mature specs: for the storybook feature it returned
  `security_surface=[]`, `architecture_impact=False`, `adr=none` despite
  `plan.md` explicitly covering a privacy/safety flow and a multi-component
  illustration architecture. Importing the committed `plan.md` decisions fixes
  this and honors "the plan already is the architecture decision."
- **Alternatives considered**:
  - *Extend `assess()` keyword corpus to include raw `plan.md` text*: viable and
    simple; adopted partially — the adapter feeds relevant `plan.md` sections
    into the assessment source rather than scanning the whole spec again.
  - *Skip assessment and default everything*: rejected — loses risk/security
    signal needed by orchestrator and security reviewer.

## Decision 3: Requirements are carried, never re-derived

- **Decision**: The adapter maps `spec.md` functional requirements 1:1 into
  subtask `acceptance_criteria`; it performs **no semantic re-derivation** and
  no clarification loop (FR-005). Validation runs performed later act on these
  carried criteria.
- **Rationale**: Clarify/review is the speckit `clarify` skill's job and is
  assumed already run. Re-derivation in the factory would re-introduce the
  removed workflow and risk contradicting the external review.
- **Alternatives considered**:
  - *Let the factory's `requirements_reviewer` run again*: rejected — that is
    the `spec-workflow` being removed.

## Decision 4: File path normalization

- **Decision**: The adapter normalizes each `tasks.md` path against the repo
  root. Absolute host paths (e.g. `/home/helio/...`) and out-of-repo
  references are **dropped** from `TechnicalSubtask.files`, with a warning. A
  shared path across tasks marks those tasks as **non-parallel**.
- **Rationale**: The PoC surfaced absolute-env-path noise (e.g.
  the repo `pyproject.toml` alongside the relative form)
  and duplicate paths (`package.json`, `src/app/page.tsx`) that signal shared
  dependencies. Normalization keeps `files` canonical; dupe detection patterns
  parallelism.
- **Alternatives considered**:
  - *Keep paths as-is*: rejected — would pass host-specific absolute paths into
    the sandbox/worker and violate repo-scoped exec.
  - *Resolve relatives to absolute*: rejected — deviates from the repo-relative
    convention used by the worker.

## Decision 5: Identity/traceability without `spec_version_id`

- **Decision**: The **folder feature id** (e.g. `002-folder-dev-run`) is the
  stable dev-run identity. A derived stable string is available for downstream
  reporting; no factory-issued `spec_version_id`/`spec_run_id` is required as
  an upstream input.
- **Rationale**: With `spec-run`/`spec-workflow` **hard removed** (no deprecation
  shim or redirect; clarified Option A), there is no producer for a factory
  version string. The folder is a stable, reviewable contract, which matches
  how speckit tracks features.
- **Alternatives considered**:
  - *Synthesize a fake default `spec_version_id`*: rejected — meaningless
    without a producer and misleading for telemetry/tracing.
  - *Keep `spec-run` as a deprecated redirect shim*: rejected — contradicts the
    hard-removal simplification (FR-006, Option A); any invocation of the
    removed command must fail cleanly.

## Decision 6: Missing/partial artifacts are an error, not a re-derive

- **Decision**: Resolution fails fast with a clear non-zero exit if any of
  `spec.md`, `plan.md`, `tasks.md` is missing or unparsable (FR-007). The
  factory NEVER generates or re-derives a missing lower-level artifact:
  a folder must be **complete** (`spec.md`, `plan.md`, `tasks.md`) before
  `dev-run` runs, and missing `plan.md`/`tasks.md` are originated by the
  **external speckit `plan`/`tasks` skills** (clarified Option C), not by the
  factory.
- **Rationale**: Partial context would silently degrade the plan and produce a
  misleading PR; a hard error keeps the invariant that the folder is the
  source of truth and that the factory is not a spec/plan/tasks author.
- **Alternatives considered**:
  - *Proceed with what exists*: rejected — risk of building against missing
    specs/plans/tasks.
  - *Auto-fill a minimal template*: rejected — this is re-derivation and
    duplicates the external speckit `plan`/`tasks` skills.

---

## Decision 7: Completion write-back (FR-010) is a write-back step, not the orchestrator

- **Decision**: A dedicated `mark_completed.py` library (in `folder_adapter`)
  flips a derived task's checkbox in the source `tasks.md` (`- [ ] T###` →
  `- [x] T###`), triggered **by subtask completion**. The orchestrator records
the fact that a subtask finished; it does not itself persist the checkbox
(keeps decision vs. execution separation). Only the checkbox of the derived
task is writable; requirement text is never re-derived or rewritten
(preserves FR-005). Single-writer-per-folder; task granularity.
- **Rationale**: Writing-to-source is a side effect that should be isolated in
  a library so it can be tested and reused, consistent with Library-First.
- **Alternatives considered**:
  - *Orchestrator updates tasks.md directly*: rejected — conflates decision
    and persistence, harder to test.

## Decision 8: Completion condition is task-intent-specific, not uniform (FR-010, SC-008)

- **Decision**: A task is marked completed only when its **stated intent** is
  satisfied, not a single pass/fail default. Following the speckit
  Red/Green pattern (per `/repos/storybook-ai`), a task that says
  "Write failing … tests" is **complete when the test exists and fails for the
  expected reason** (Red verified); a task that expects a **passing** test is
  complete when it passes; an **implement** task is complete when code + review
  + associated tests pass.
- **Rationale**: A Red test task is done by producing a failing test, and
  flipping to `[x]` on a green would be wrong (the task was never asked to make
  it green). Distinguishing fail-expected vs pass-expected matches TDD and the
  storybook task corpus.
- **Alternatives considered**:
  - *Uniform "completed = passes"*: rejected — mis-marks Red test tasks.
  - *Skip marking test tasks*: rejected — loses traceability (FR-010/SC-007).
- **Note**: full routing by task type (`test` vs `implement` vs `validate`) is
  a **follow-on pass** (see Task Routing); this decision scopes FR-010 to the
  completion *criterion* only.

---

## Decision 9: `SpecSource` resolves the spec by origin — including another repo (FR-011/012)

- **Decision**: The source folder is resolved by `SpecSource`, not only by a
  path relative to the dev-run process's working directory. Two modes:
  - `local` — default `specs/<name>/` in the working repo, or `--spec-source path:...`;
  - `git` — `--spec-source git:<repo-url>[#branch]`, which **clones** the source
    repo, reads its `specs/<name>/`, and delivers the `tasks.md` completion diff
    back **via PR**, per phase/increment: a **phase PR** (a new branch carries
    code + that phase's `tasks.md` completion marks, opened at each phase
    boundary so a long feature yields a sequence of small PRs) or
    **dedicated PR** (a new branch
    `ai-factory/<feature>-tasks-md` carrying only the `tasks.md` diff). Never a
    direct push to the source repo's origin branch.
- **Rationale**: The supported topology includes "dev-workflow runs locally but
  the spec lives in another repository". Resolving by origin lets the adapter
  locate artifacts in the correct repo and keeps the completion write-back
  (FR-010) scoped to the **source repo's** `tasks.md`, never the working
  directory. Delivering via PR respects the source repo's review flow (no
  direct push to origin).
- **Alternatives considered**:
  - *Only resolve within the working repo's `specs/`*: rejected — breaks
    multi-repo and mis-scopes the write-back.
  - *Direct push to the source repo when write access exists*: rejected —
    bypasses review and can mutate origin; always route through a PR.
- **Note**: `spec_source.py` (resolve) and `git_source.py` (clone + PR delivery)
  are new `folder_adapter` modules; see plan.md structure.

---

## Decision 11: git SpecSource credentials & trust boundary (FR-012, SC-011)

- **Decision**: For the `git` `SpecSource`, the factory **reuses the caller's
  existing git host client credentials** (it does not manage its own
  tokens/secrets). The source repo is treated as **untrusted input**: any
  content read from it is **validated/sanitized before write-back**, and a
  missing/invalid credential surfaces a clear non-zero error rather than a
  silent fallback (clarified, Option D).
- **Rationale**: A CLI orchestration tool should delegate authentication to the
  existing git host client rather than reinvent a secret store; this matches the
  declared "reuse the existing git host client" delivery path. Validating
  before write-back preserves the spec's write-back safety posture (FR-008-style
  path normalization), so an arbitrary source repo cannot inject malformed or
  malicious content into the `tasks.md` completion diff.
- **Alternatives considered**:
  - *Factory manages its own tokens*: rejected — contradicts "reuse the existing
    git host client", adds a secret-management surface, and is out of scope for
    a CLI orchestrator.
  - *Full trust with no validation*: rejected — an untrusted source repo could
    corrupt the write-back; validation before write-back is required.
  - *Require a `--trust-source <host>` allowlist*: rejected for base design
    (operational friction); can be layered on later as a hardening option.

---

## Decision 10: Route each subtask by `source_task_type` (FR-013)

- **Decision**: The adapter derives a `source_task_type` (`test` | `implement` |
  `validate`) for each `TechnicalSubtask` from its describing speckit task, and
  the orchestrator selects the capability path from it. `test` tasks (e.g.
  "Write failing …") route to test-engineering/test-running, **not** the
  code-worker; `implement` tasks go through code-worker + review + tests;
  `validate` tasks go to a validation step.
- **Rationale**: A task that is itself a test (TDD Red) should not be fed to a
  code-worker that generates implementation — that would overwrite/duplicate the
  test contract and waste budget. The speckit corpus (e.g. storybook `009 Write
  failing tests` → `010 Implement`) presents test tasks as first-class units,
  which route by type. This also aligns with the completion criteria (Decision 8:
  a `test` task completes on Red verification, an `implement` task on
  code+review+tests pass).
- **Alternatives considered**:
  - *One uniform pipeline for all subtasks*: rejected — mis-handles `test` tasks
    through code-worker.
  - *Always route test tasks to test-engineer only when tests are "requested"*:
    rejected — indeterminate; routing by described type is deterministic.

---

## Open items / risks

- **Format variance between speckit producers** is the main risk; the adapter
  should normalize keys/headings and be validated against a corpus of real
  folders (both `001-ai-dev-factory` and the storybook example).
- **Test migration cost**: existing `test_spec_workflow.py`, `test_handoff.py`
  and spec-run CLI tests must be rewritten onto the folder-driven entry
  (FR-009) — schedule as its own task group.
