# Contract: spec-run CLI (REMOVED)

**Status**: REMOVED as a required entry point (FR-006).

This record documents the removal of the independent `spec-run` command and
the factory `spec-workflow` from the required entry path.

## What was removed

- `spec-run` from `[project.scripts]`.
- The factory `spec-workflow` as a required, separate step that produced a
  `SpecVersion`/`spec_version_id` for `dev-run` to consume by reference.

## Why (rationale)

- The speckit toolchain owns **specify** (spec generation) and **clarify**
  (revision/clarification, runnable multiple times). The factory's parallel
  spec command duplicated this and added an avoidable `spec_version_id`
  round-trip.
- Requirement review/refinement moved outside the factory (FR-005); the
  factory now assumes a ready speckit folder.

## What replaces it

`dev-run <folder>` enters from a `specs/<folder>/` speckit folder directly
(FR-001, FR-002). See `./dev-run-cli.md`.

## Migration notes

- Existing integration tests that depended on `spec-run`/`spec-workflow`
  (`test_spec_workflow.py`, `test_handoff.py`, spec-run CLI tests) are
  migrated to drive the folder-driven `dev-run` (FR-009).
- If any downstream traceability still expects a `spec_version_id`, it is
  derived from the folder name (feature id); it is no longer a factory-issued
  version string.
