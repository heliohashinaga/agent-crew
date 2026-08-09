# Contract: dev-run CLI (Development Workflow)

The Development Workflow entrypoint. Consumes an approved specification by
reference and delivers a factory-opened pull request (FR-007, FR-012,
FR-022, FR-023, FR-025).

## Interface

```text
dev-run --spec-version-id <id> [--resume <run_id>] [--format json|human]
```

- **Input**: a `spec_version_id` referencing an approved, human-approved
  `SpecVersion` (FR-025). The dev run loads the spec **by reference** — it
  MUST NOT re-derive requirements (FR-001, FR-025, SC-017).
- **Output (stdout)**: a `PullRequest` record (host, branch,
  `spec_version_id`, checks status, `pr_url`, `auto_merged=false`).
- **Diagnostics**: to stderr.
- **Exit codes**: `0` delivered; `4` failed delivery (host unreachable /
  bad credentials — local branch kept); `5` stopped-human (re-planning
  failed, FR-015); non-zero otherwise.

## Traceability (FR-024, FR-025, SC-016, SC-017)

The dev run carries `spec_version_id` and the originating `spec_run_id` in
its run metadata. The dev run is a distinct top-level trace; the two
workflows are linked by these ids, not merged.

## Workflow (LangGraph `StateGraph`)

1. `technical_planner` — maps the spec to existing components; produces a
   `TechnicalPlan` and `Assessment` (complexity, risk, architecture impact,
   test scope, security surface, documentation). Produces an `ADR` only if
   `architecture_impact` is true (FR-008). No human gate after this
   (FR-023).
2. `orchestrator` — pure decision layer (FR-009); from the assessment,
   produces an `ExecutionPlan` per role (model, capability level, budget,
   timeout, parallelization, retry policy) using `capability_levels/` (R9).
3. `code_worker` — implementation + unit tests, with local validation
   (FR-011). Produces documentation when the assessment requires it.
4. `code_reviewer` — validates and approves; validates ADR adherence if an
   ADR exists (FR-008).
5. `test_engineer` + `test_runner` — produce and run the test suite.
   AI-generated tests run in the sandbox (FR-021).
6. `security_reviewer` — assesses and approves. A CRITICAL finding halts,
   triggers an immediate fix, and requires a full re-audit before merge
   (FR-014).
7. `deliver` — opens the PR on the remote git host via the host API client
   (FR-022). MUST NOT auto-merge (FR-012).

## Issue handling (FR-013/014/015)

Bounded retry loops, escalation, and re-planning are LangGraph conditional
edges within this graph. On retry/escalation limit exceeded, the graph
re-routes to `technical_planner` to re-plan; it stops for a human only when
re-planning itself fails (FR-015). Transient/infra failures use
exponential backoff; deterministic failures route to `code_worker`
(FR-014).

## Resumability (FR-020, SC-012)

The run checkpoints at role/phase boundaries. `--resume <run_id>` continues
from the last completed checkpoint, re-running no completed work.

## Guarantees

- MUST NOT auto-merge the PR (FR-012, FR-022).
- MUST NOT re-derive requirements; consumes the approved spec by reference
  (FR-025, SC-017).
- AI-generated code/tests run in an isolated sandbox (FR-021, SC-013).
- Records each `DevRoleInvocation` (telemetry) per the
  [library CLI convention](./library-cli-convention.md).
- Cost budget is soft: continue + warn + record overspend (FR-019, SC-011).