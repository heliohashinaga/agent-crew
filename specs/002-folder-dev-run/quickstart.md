# Quickstart: Folder-Driven Dev Run

**Feature** | 002-folder-dev-run | **Date** | 2026-08-09 | **Spec** | [spec.md](./spec.md) | **Plan** | [plan.md](./plan.md)

This is a **validation guide**. It proves the feature works end-to-end; it does
not contain implementation code or test bodies (see [tasks.md](./tasks.md) and
the implementation phase for those).

## Prerequisites

- Python ≥ 3.14 project managed with `uv` (repository root `ai-factory`).
- A speckit spec folder under `specs/<name>/` containing `spec.md`,
  `plan.md`, and `tasks.md`. A fixture folder is provided by the test suite
  (see Setup) so validation does not require a real speckit run.

## Setup

```bash
cd /home/helio/repos/ai-factory
uv sync
uv run ruff check .
uv run pytest -q
```

`uv run pytest` runs unit + contract tests (network-blocked). The
folder-driven scenarios below use fixture artifact folders under `tests/fixtures/specs/`.

## Scenarios

### Scenario 1 — Folder is Rejected/Resolved (FR-001, FR-002, SC-002)

**Goal**: `dev-run <folder>` resolves a spec folder and returns a clear
non-zero error for a missing one.

```bash
# missing folder → non-zero, clear error, no pipeline
uv run dev-run nope-not-a-folder --sandbox fake --git-host fake
echo "exit: $?"
```

**Expected outcome**: Non-zero exit (4 per contract) with a clear "folder not
found / artifacts missing" message; no PR produced; deterministic, network-free.

### Scenario 2 — Folder Drives a Full Run to a PR (FR-001..003, FR-005, SC-001/003)

**Goal**: a ready fixture folder is consumed end-to-end to a factory-opened PR.

```bash
uv run dev-run 002-folder-dev-run --sandbox fake --git-host fake --format human
```

**Expected outcome**: `outcome: delivered`, `pr.number`, `pr.url` on fake host,
`auto_merged=false`, exit `0`. Subtask `files` match the fixture `tasks.md`
in-repo paths (100%); `acceptance_criteria` carried from fixture `spec.md` FRs
(SC-004).

### Scenario 3 — Assessment Imported from plan.md (FR-004, SC-005)

**Goal**: the technical assessment reflects the folder `plan.md` decisions, not
re-derived only from `spec.md`.

```bash
uv run pytest -m integration -k "folder_adapter_assessment" -q
```

**Expected outcome**: on the fixture folder whose `plan.md` declares
architecture/security decisions, `architecture_impact=True` and
`security_surface` populated (no false-negative). Where `plan.md` lacks a
section, the field degrades to a default with an inference note.

### Scenario 4 — No Spec-Run Required (FR-006, SC-006)

**Goal**: a full `dev-run` needs no factory `spec-run`.

```bash
# spec-run is no longer in project scripts / required
! (uv run spec-run --help)  # exits non-zero (removed)
uv run dev-run 002-folder-dev-run --sandbox fake --git-host fake >/dev/null && echo OK
```

**Expected outcome**: `spec-run` is absent from `[project.scripts]`; the
folder-driven `dev-run` completes with no `spec_version_id` input.

### Scenario 5 — Missing/Partial Artifacts Fail Fast (FR-007)

**Goal**: a folder missing `plan.md` (or any required artifact) errors rather
than proceeding on partial context.

```bash
uv run dev-run <fixture-folder-without-plan> --sandbox fake --git-host fake
echo "exit: $?"
```

**Expected outcome**: Non-zero exit with a clear missing-artifact message; no
pipeline run.

### Scenario 6 — Path Normalization (FR-008, SC-003)

**Goal**: absolute host paths and out-of-repo references in `tasks.md` are
dropped with a warning; in-repo paths carried.

```bash
uv run pytest -m integration -k "folder_adapter_paths" -q
```

**Expected outcome**: no subtask `files` contains an absolute host path;
out-of-repo references excluded; shared-file tasks flagged non-parallel; a
warning is emitted.

### Scenario 7 — Migrated Integration Suite (FR-009, SC-006)

**Goal**: the existing integration tests that depended on `spec-run`/handoff
now pass via the folder-driven entry.

```bash
uv run pytest -m integration -q
```

**Expected outcome**: Full integration suite green; no test is blocked on the
removed `spec-run`/`spec-workflow`.

### Scenario 8 — Task-Type Routing (FR-013, SC-010)

**Goal**: a `test`-typed subtask is handled by the test capability, **not** the
code-worker; a test task expecting a failure completes on Red.

```bash
uv run pytest -m integration -k "folder_adapter_routing" -q
```

**Expected outcome**: A fixture task described as "Write failing …" routes to
`test_engineer`/`test_runner` (no code-worker invocation); a `test` task whose
description expects a failure is marked completed on Red verification; `implement`
tasks route to code-worker + review + tests; `validate` tasks go to a validation
step (FR-013, SC-010).

### Scenario 9 — git SpecSource credentials & validation (FR-012, SC-011)

**Goal**: authenticate via the caller's existing git host client (no factory-managed
secret store) and validate/sanitize source-repo content before any write-back.

```bash
uv run pytest -m integration -k "git_source_auth_trust" -q
```

**Expected outcome**: A `git:...` source delivers its `tasks.md` completion diff **via
PR** using the caller's existing host-client credentials; content read from the source
repo is validated/sanitized before write-back (no unvalidated write-back, SC-011); a
missing/invalid credential returns a clear non-zero exit rather than a silent fallback.

### Scenario 10 — Idempotent re-run, no-op, and task selector (FR-014a/b/c, SC-007a/b)

**Goal**: a fully-completed folder is a no-op; a fresh run skips `- [x]`
tasks; `--force` re-runs them; a task selector scopes `T###`/range/`T3-`.

```bash
# default: all tasks already - [x]  → exit 0, no PR, no execution
uv run dev-run <fixture-all-complete> --sandbox fake --git-host fake
# selector: run only T3..T7, flip only their marks, own small PR
uv run dev-run <folder> T3-T7 --sandbox fake --git-host fake
# --force: re-execute the selected already--[x] tasks
uv run dev-run <folder> --force --sandbox fake --git-host fake
# unknown selector id → non-zero clear error
uv run dev-run <folder> T99 --sandbox fake --git-host fake
uv run pytest -m integration -k "task_selector_noop" -q
```

**Expected outcome**: all-complete folder exits `0` (no-op, no PR); a fresh run
skips already-`[x]` tasks and writes back only the selected `- [x]` marks;
`--force` re-runs completed tasks; an unknown task id errors non-zero; a targeted
scope omitting earlier uncompleted tasks emits a **prerequisite warning**
(non-blocking). See [contracts/dev-run-cli.md](./contracts/dev-run-cli.md).

## Notes

- All scenarios run with `--sandbox fake --git-host fake`, so validation is
  deterministic and offline (no model, no container, no live host).
- The contract for exit codes and the PR record is in
  [contracts/dev-run-cli.md](./contracts/dev-run-cli.md). The folder-as-contract
  model is in [data-model.md](./data-model.md).
- To validate against a *real* environment, replace `--sandbox fake` with
  `--sandbox docker` and `--git-host fake` with `--git-host github`
  (needs credentials + container), per the dev-run contract.
