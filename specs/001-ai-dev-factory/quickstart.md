# Quickstart: AI Software Development Factory

**Feature**: 001-ai-dev-factory | **Date**: 2026-08-09 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Runnable validation scenarios that prove the feature works end-to-end.
This is a **validation/run guide**, not implementation; implementation
details belong in `tasks.md` (Phase 2) and the implementation phase.

## Prerequisites

- Python ≥ 3.14 managed with `uv` (constitution).
- A container runtime available (FR-021) — the factory fails early with a
  clear reason if none is present (spec Edge Cases).
- LLM-provider credentials in the environment or a dedicated secret store
  (FR-018). The factory MUST NOT read credentials from committed config.
- Git-host credentials (for PR delivery) in the same secret store (FR-022).
- LangSmith configured for tracing (R2) — credentials via the same path.

## Setup

```bash
uv sync                       # install the factory and its libraries
uv run pytest -q              # unit + contract + integration tests (constitution Principles III/IV)
```

## Scenario 1 — Specification Workflow end-to-end (FR-002..006, SC-001)

**Goal**: a request becomes an approved, versioned spec with no code.

```bash
echo "Add a password-reset flow to the auth library" | \
  uv run spec-run --request --stdin --format json
```

**Expected outcome**:
- Exit code `0`; stdout is a `SpecVersion` JSON with a stable
  `spec_version_id` and `spec_run_id`.
- The spec contains intent, rationale, testable acceptance criteria, a
  definition of done, and ≥1 edge case (FR-003).
- No implementation code is produced (FR-001).
- A human approval gate was enforced before `approval_status=approved`
  (FR-005).
- A scope-critical ambiguity would surface as bounded clarifications
  (FR-006); to verify, run the same with an ambiguous request and expect
  exit code `3`.

**Verify observability**: the spec run is a distinct top-level trace
(FR-024, SC-016); record its `spec_run_id` for Scenario 2.

## Scenario 2 — Dev Workflow end-to-end (FR-007..012, SC-002)

**Goal**: an approved spec becomes a factory-opened PR.

```bash
uv run dev-run --spec-version-id <id from Scenario 1> --format json
```

**Expected outcome**:
- Exit code `0`; stdout is a `PullRequest` JSON with `auto_merged=false`,
  `checks_status=pass`, a `pr_url`, and the same `spec_version_id`.
- The PR was opened by the factory on the remote git host via the host API
  (FR-022, SC-014); the factory did NOT auto-merge (FR-012).
- The dev run consumed the spec by reference (no re-derivation) and its
  trace carries `spec_version_id` + `spec_run_id` (FR-025, SC-017).
- No human gate interrupted the run between planning and execution
  (FR-023, SC-015).

## Scenario 3 — Issue handling & re-planning (FR-013/014/015, SC-003)

**Goal**: an injected issue is absorbed without human intervention.

Run Scenario 2 against a repo with a deterministic failing test. Inject
the failure mid-run.

**Expected outcome**:
- The deterministic failure routes to `code_worker` for a fix (FR-014).
- If a retry/escalation limit is exceeded, the graph re-routes to
  `technical_planner` to re-plan (FR-015).
- The run stops for a human **only** if re-planning itself fails (FR-015);
  expect exit code `5` in that case, otherwise `0`.

## Scenario 4 — Resumability (FR-020, SC-012)

**Goal**: an interrupted run resumes from the last checkpoint.

Interrupt a Scenario 2 run (e.g., cancel mid-phase), then:

```bash
uv run dev-run --spec-version-id <id> --resume <run_id>
```

**Expected outcome**:
- The resumed run continues from the last completed checkpoint and
  re-runs no completed role/phase (SC-012).
- Final output is the same `PullRequest` shape as Scenario 2.

## Scenario 5 — Security & secrets (FR-018/021, SC-010/013)

**Goal**: secrets never leak; AI code runs sandboxed.

- Place a secret-looking value in the target repo; run Scenario 2 and
  assert no emitted log/telemetry contains it (SC-010).
- Assert AI-generated code/tests executed inside the sandbox and could not
  touch host resources outside the mounted repo (SC-013).

## Scenario 6 — Budget overrun (FR-019, SC-011)

**Goal**: a run completes despite exceeding its cost budget.

Run Scenario 2 with an artificially low budget.

**Expected outcome**:
- The run completes (exit `0`), a warning is emitted, and the telemetry
  records `overspend=true` (SC-011). The run is not aborted on budget
  grounds.

## Scenario 7 — Conditional ADR (FR-008, SC-008)

**Goal**: an ADR is produced only for architecturally significant changes.

- Run Scenario 2 with a request requiring a non-conventional trade-off →
  expect an `ADR` linked to the `TechnicalPlan`.
- Run Scenario 2 with a trivial fix (e.g., null-check) → expect no ADR.

## Notes

- Refer to [data-model.md](./data-model.md) for entity shapes and
  [contracts/](./contracts/) for CLI contracts; this guide does not
  duplicate them.
- Telemetry is emitted per-role via the
  [library CLI convention](./contracts/library-cli-convention.md) (FR-016).