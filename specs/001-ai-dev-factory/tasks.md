# Tasks: AI Software Development Factory

**Branch**: `001-ai-dev-factory` | **Date**: 2026-08-09 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

**Implementation strategy**: MVP first (US1 only — the Specification Workflow
end-to-end), then incremental delivery. The constitution mandates TDD
(Red-Green-Refactor) as NON-NEGOTIABLE, so every library gets a failing
test before its implementation. Library-First + CLI Interface: each
role/capability is a standalone, independently testable library exposed
through a CLI; the two workflows are thin CLIs that compose libraries.

## User Stories (from spec.md)

- **US1 (P1)** — Specify a Feature from a Natural-Language Request
- **US2 (P1)** — Build and Deliver a Pull Request from an Approved Spec
- **US3 (P1)** — Handle Issues Automatically with Retry, Escalation, Re-Planning
- **US4 (P2)** — Right-Size Execution via Capability Levels and Orchestrator Decisions
- **US5 (P2)** — Make the Factory Observable and Data-Driven
- **US6 (P3)** — Produce Architecture Decision Records Only When Needed

## Dependencies (user story completion order)

```text
[Phase 1: Setup] → [Phase 2: Foundational shared libs + state + contracts]
   └─→ US1 (spec workflow + hand-off)           ← MVP
         └─→ US5 (telemetry — needed by US2/US3 too; build after US1, wire into US2)
               └─→ US4 (capability levels + orchestrator) → US6 (conditional ADR)
                     └─→ US2 (dev workflow end-to-end + PR delivery)
                           └─→ US3 (issue handling loops in dev graph)
                                 └─→ [Polish]
```

- US1 is the MVP and the foundation of the hand-off contract (FR-025).
- US5 (telemetry) is built as a shared library after US1 and is wired into
  every role invocation; US2/US3 depend on it being available.
- US4 (capability levels + Orchestrator) and US6 (conditional ADR) precede
  US2 because the dev workflow graph needs the decision layer and the ADR
  path before end-to-end execution.
- US2 (dev workflow + PR delivery) depends on US1 (hand-off), US4
  (orchestrator), US5 (telemetry), and US6 (ADR path).
- US3 (issue handling) builds on US2's dev graph, adding the retry/
  escalation/re-plan conditional edges.

---

## Phase 1: Setup

- [x] T001 Create `pyproject.toml` with `uv`, Python ≥ 3.14, `src/` layout, and core deps (`langgraph`, `langsmith`, `pydantic`) in `/home/helio/repos/ai-factory/pyproject.toml`
- [x] T002 Create `src/ai_factory/__init__.py` and the package skeleton (`shared/`, `spec_workflow/`, `dev_workflow/`, `capability_levels/`, `cli/`) with empty `__init__.py` files
- [x] T003 Create `tests/` skeleton (`tests/unit/`, `tests/contract/`, `tests/integration/`) with a `conftest.py` that asserts no network in unit tests
- [x] T004 Create `.specify/memory/constitution.md` is already present — add a project-level `AGENTS.md` summarizing Library-First, CLI Interface, Test-First, and the two-workflow boundary in `/home/helio/repos/ai-factory/AGENTS.md`
- [x] T005 Configure `ruff` and `pytest` in `/home/helio/repos/ai-factory/pyproject.toml` (strict config; integration tests marked separately)

## Phase 2: Foundational (blocking prerequisites for all user stories)

- [x] T006 [P] Write failing test for `FactoryState` and core state models in `tests/unit/shared/state/test_factory_state.py`
- [x] T007 [P] Implement Pydantic `FactoryState`, `RunState`, `Checkpoint`, `ApprovalStatus` in `src/ai_factory/shared/state/factory_state.py`
- [x] T008 [P] Write failing test for the secret/redaction library in `tests/unit/shared/secrets/test_redaction.py`
- [x] T009 [P] Implement env/secret-store credential loaders and secret-value redaction in `src/ai_factory/shared/secrets/loader.py` (FR-018)
- [x] T010 [P] Write failing test for the spec-store (versioned persistence, stable `spec_version_id`) in `tests/unit/shared/spec_store/test_spec_store.py`
- [x] T011 [P] Implement local-filesystem spec store with versioning and `spec_version_id` in `src/ai_factory/shared/spec_store/store.py` (FR-025)
- [x] T012 Write failing test for the LLM provider abstraction in `tests/unit/shared/llm/test_provider.py` (uses a fake provider; no network)
- [x] T013 Implement the pluggable LLM provider abstraction with env/secret-store credentials in `src/ai_factory/shared/llm/provider.py` (R5, FR-018)
- [x] T014 Write failing test for the library CLI convention harness (JSON/human output, exit codes, redaction) in `tests/contract/test_library_cli_convention.py`
- [x] T015 Implement the shared CLI helpers (output formatting, exit codes, telemetry hook, redaction wrapper) in `src/ai_factory/shared/cli_util.py` (contracts/library-cli-convention.md)

## Phase 3: User Story 1 — Specify a Feature from a Natural-Language Request (P1)

**Goal**: text request → approved, versioned spec with no code. **Independent test**: submit one concrete request and receive an approved `SpecVersion` (intent, rationale, testable AC, DoD, edge case) containing no implementation code.

- [x] T016 [US1] Write failing contract test for the spec-agent library CLI in `tests/contract/spec_workflow/test_spec_agent_cli.py`
- [x] T017 [US1] Implement the spec-agent role library (drafts spec: intent, rationale, AC, DoD, edge cases; surfaces bounded clarifications) in `src/ai_factory/spec_workflow/spec_agent/agent.py` and `src/ai_factory/spec_workflow/spec_agent/cli.py` (FR-002, FR-003, FR-006)
- [x] T018 [US1] Write failing contract test for the requirements-reviewer library CLI in `tests/contract/spec_workflow/test_requirements_reviewer_cli.py`
- [x] T019 [US1] Implement the requirements-reviewer role library (validates clarity/completeness/consistency/testability/edge-case coverage; Approve/Reject with reasons) in `src/ai_factory/spec_workflow/requirements_reviewer/reviewer.py` and `src/ai_factory/spec_workflow/requirements_reviewer/cli.py` (FR-004)
- [x] T020 [US1] Write failing integration test for the spec workflow graph (draft → review → amend loop; bounded reject cycles) in `tests/integration/test_spec_workflow.py`
- [x] T021 [US1] Implement the Specification Workflow LangGraph `StateGraph` (spec_agent ↔ requirements_reviewer loop, human-approval gate) in `src/ai_factory/spec_workflow/graph.py` (FR-004, FR-005)
- [x] T022 [US1] Write failing integration test for the human-approval gate (no `approved` without human approval) in `tests/integration/test_spec_workflow.py`
- [x] T023 [US1] Implement the `spec-run` thin CLI (text-in → approved `spec_version_id` out; exit codes 0/2/3) in `src/ai_factory/cli/spec_run.py` (contracts/spec-run-cli.md, FR-005, FR-025)
- [x] T024 [US1] Write failing test for the spec-workflow → dev-workflow hand-off boundary (dev consumes by reference, no re-derivation; carries `spec_version_id`/`spec_run_id`) in `tests/integration/test_handoff.py`
- [x] T025 [US1] Implement the hand-off seam (emit approved `SpecVersion` with stable `spec_version_id` + `spec_run_id`; reference-only loader) in `src/ai_factory/shared/spec_store/handoff.py` (FR-024, FR-025, SC-016, SC-017)
- [x] T026 [US1] Validate US1 end-to-end against quickstart Scenario 1 and mark the US1 checklist item complete

## Phase 4: User Story 5 — Make the Factory Observable and Data-Driven (P2, built before US2/US3/US4)

**Goal**: every role invocation records a `TelemetryRecord`. **Independent test**: run one feature through and retrieve the full per-role telemetry. Built now because US2/US3/US4 all emit telemetry.

- [x] T027 [US5] Write failing test for the `TelemetryRecord` model and per-role telemetry emission in `tests/unit/shared/telemetry/test_record.py`
- [x] T028 [US5] Implement the `TelemetryRecord` Pydantic model (role, model, capability level, tokens, cost, latency, tool calls, retries, errors, escalations, result, overspend) in `src/ai_factory/shared/telemetry/record.py` (FR-016)
- [x] T029 [US5] Write failing test for secret redaction in telemetry (no secret-looking values emitted) in `tests/unit/shared/telemetry/test_emitter.py` (redaction-focused coverage)
- [x] T030 [US5] Implement the telemetry emission library (structured records, redaction before emission, machine- and human-readable forms) in `src/ai_factory/shared/telemetry/emitter.py` (FR-016, FR-018, SC-010)
- [x] T031 [US5] Write failing test for the telemetry query CLI (retrieve a run's telemetry in JSON and human forms) in `tests/contract/test_telemetry_cli.py`
- [x] T032 [US5] Implement the telemetry-query CLI (returns a run's full per-role telemetry within seconds) in `src/ai_factory/shared/telemetry/cli.py` (FR-016, SC-003)
- [x] T033 [US5] Wire telemetry emission into the spec-agent and requirements-reviewer library CLIs (emit per invocation) in `src/ai_factory/spec_workflow/spec_agent/cli.py` and `src/ai_factory/spec_workflow/requirements_reviewer/cli.py`
- [x] T034 [US5] Validate US5 against quickstart Scenario 5 (secret-redaction assertion) and mark the US5 checklist item complete

## Phase 5: User Story 4 — Right-Size Execution via Capability Levels and Orchestrator (P2)

**Goal**: per-role model/capability-level/budget from the assessment. **Independent test**: two tasks of different complexity get different levels. Built before US2 because the dev graph needs the Orchestrator.

- [x] T035 [US4] Write failing test for the capability-level definitions (simple/standard/complex; shallow/standard/deep) and their model/budget/timeout/tool-access mapping in `tests/unit/capability_levels/test_levels.py`
- [x] T036 [US4] Implement the centralized capability-level mapping library in `src/ai_factory/capability_levels/levels.py` (FR-010, R9)
- [x] T037 [US4] Write failing contract test for the orchestrator library CLI in `tests/contract/dev_workflow/test_orchestrator_cli.py`
- [x] T038 [US4] Implement the orchestrator role library (pure decision layer: assessment → ExecutionPlan per role; no specialized work) in `src/ai_factory/dev_workflow/orchestrator/orchestrator.py` and `src/ai_factory/dev_workflow/orchestrator/cli.py` (FR-009)
- [x] T039 [US4] Write failing test that a retry-after-failure raises the capability level by ≥1 step in `tests/unit/dev_workflow/orchestrator/test_retry_leveling.py`
- [x] T040 [US4] Implement retry level-bump logic (raise level + add validation depth/budget on re-plan) in `src/ai_factory/dev_workflow/orchestrator/orchestrator.py` (spec User Story 4 scenario 4)
- [x] T041 [US4] Validate US4 against quickstart (low- vs high-complexity assessment gets different levels) and mark the US4 checklist item complete

## Phase 6: User Story 6 — Conditional ADRs (P3, built before US2 for the ADR path)

**Goal**: ADR only for architecturally significant decisions. **Independent test**: one task with a trade-off → ADR; one trivial fix → no ADR.

- [x] T042 [US6] Write failing test for the ADR model and conditional-production rule in `tests/unit/dev_workflow/technical_planner/test_adr.py`
- [x] T043 [US6] Implement the `ArchitectureDecisionRecord` Pydantic model in `src/ai_factory/dev_workflow/technical_planner/adr.py` (data-model.md, FR-008)
- [x] T044 [US6] Write failing contract test for the technical-planner library CLI in `tests/contract/dev_workflow/test_technical_planner_cli.py`
- [x] T045 [US6] Implement the technical-planner role library (assessment + TechnicalPlan + conditional ADR when `architecture_impact=true`) in `src/ai_factory/dev_workflow/technical_planner/planner.py` and `src/ai_factory/dev_workflow/technical_planner/cli.py` (FR-007, FR-008)
- [x] T046 [US6] Implement ADR-adherence validation in the code-reviewer library in `src/ai_factory/dev_workflow/code_reviewer/reviewer.py` (validates against linked ADR; FR-008)
- [x] T047 [US6] Validate US6 against quickstart Scenario 7 (trade-off → ADR; trivial fix → none) and mark the US6 checklist item complete

## Phase 7: User Story 2 — Build and Deliver a Pull Request from an Approved Spec (P1)

**Goal**: approved spec → factory-opened PR with all checks passing, no auto-merge. **Independent test**: run dev-run from an approved `spec_version_id` and receive a PR. Depends on US1 (hand-off), US4 (orchestrator), US5 (telemetry), US6 (ADR path).

- [x] T048 [US2] Write failing contract test for the code-worker library CLI in `tests/contract/dev_workflow/test_code_worker_cli.py`
- [x] T049 [US2] Implement the code-worker role library (implementation + unit tests, local validation, documentation when required) in `src/ai_factory/dev_workflow/code_worker/worker.py` and `src/ai_factory/dev_workflow/code_worker/cli.py` (FR-011)
- [x] T050 [US2] Write failing contract test for the code-reviewer library CLI in `tests/contract/dev_workflow/test_code_reviewer_cli.py`
- [x] T051 [US2] Implement the code-reviewer role library (validate and approve; ADR adherence) in `src/ai_factory/dev_workflow/code_reviewer/reviewer.py` and `src/ai_factory/dev_workflow/code_reviewer/cli.py` (FR-011)
- [x] T052 [US2] Write failing contract test for the test-engineer library CLI in `tests/contract/dev_workflow/test_test_engineer_cli.py`
- [x] T053 [US2] Implement the test-engineer role library (produce test suite) in `src/ai_factory/dev_workflow/test_engineer/engineer.py` and `src/ai_factory/dev_workflow/test_engineer/cli.py` (FR-011)
- [x] T054 [US2] Write failing contract test for the test-runner library CLI in `tests/contract/dev_workflow/test_test_runner_cli.py`
- [x] T055 [US2] Implement the test-runner role library (run tests; pass/fail evidence) in `src/ai_factory/dev_workflow/test_runner/runner.py` and `src/ai_factory/dev_workflow/test_runner/cli.py` (FR-011)
- [x] T056 [US2] Write failing contract test for the security-reviewer library CLI in `tests/contract/dev_workflow/test_security_reviewer_cli.py`
- [x] T057 [US2] Implement the security-reviewer role library (assess and approve; CRITICAL → halt + fix + re-audit) in `src/ai_factory/dev_workflow/security_reviewer/reviewer.py` and `src/ai_factory/dev_workflow/security_reviewer/cli.py` (FR-011, FR-014)
- [x] T058 [US2] Write failing test for the sandbox runner (AI-generated code isolated; repo mounted rw; host protected) in `tests/unit/shared/sandbox/test_sandbox.py`
- [x] T059 [US2] Implement the sandbox library (container/sandbox runner; fail-early if no runtime) in `src/ai_factory/shared/sandbox/runner.py` (FR-021, SC-013)
- [x] T060 [US2] Wire the test-runner to execute AI-generated tests inside the sandbox in `src/ai_factory/dev_workflow/test_runner/runner.py` (FR-021)
- [x] T061 [US2] Write failing contract test for the git-host client (open PR; pluggable adapter) in `tests/contract/shared/test_git_host_cli.py` (uses a fake host)
- [x] T062 [US2] Implement the pluggable git-host client (open PR via host API; credentials from secret store; no auto-merge) in `src/ai_factory/shared/git_host/client.py` and one adapter in `src/ai_factory/shared/git_host/adapters/github.py` (FR-022, SC-014)
- [x] T063 [US2] Write failing integration test for the dev workflow graph (plan → orchestrate → execute → review/test/security → deliver PR; no human gate between plan and execution) in `tests/integration/test_dev_workflow.py`
- [x] T064 [US2] Implement the Development Workflow LangGraph `StateGraph` (planner → orchestrator → code_worker → code_reviewer → test_engineer/test_runner → security_reviewer → deliver) in `src/ai_factory/dev_workflow/graph.py` (FR-007..012, FR-023)
- [x] T065 [US2] Write failing test that the run does NOT auto-merge and the PR is opened on the host in `tests/integration/test_dev_workflow.py`
- [x] T066 [US2] Implement the `dev-run` thin CLI (`spec_version_id`-in → PR out; `--resume`; exit codes 0/4/5) in `src/ai_factory/cli/dev_run.py` (contracts/dev-run-cli.md, FR-012, FR-022)
- [x] T067 [US2] Write failing test for resumability (interrupt → resume skips completed checkpoints) in `tests/integration/test_dev_workflow.py`
- [x] T068 [US2] Implement checkpointing at role/phase boundaries in `src/ai_factory/dev_workflow/graph.py` and `src/ai_factory/shared/state/checkpointer.py` (FR-020, SC-012)
- [x] T069 [US2] Write failing test for soft budget (continue + warn + record overspend; no hard-stop) in `tests/integration/test_dev_workflow.py`
- [x] T070 [US2] Implement soft-budget enforcement (warn + telemetry `overspend=true`; never abort on budget) in `src/ai_factory/dev_workflow/orchestrator/budget.py` (FR-019, SC-011)
- [x] T071 [US2] Wire telemetry emission into every dev-role library CLI in `src/ai_factory/dev_workflow/*/cli.py` (US5)
- [x] T072 [US2] Validate US2 end-to-end against quickstart Scenarios 2, 4, 6 and mark the US2 checklist item complete

## Phase 8: User Story 3 — Issue Handling, Retry, Escalation, Re-Planning (P1)

**Goal**: issues absorbed by bounded retry/escalation/re-plan; stop for a human only when re-planning fails. **Independent test**: inject a deterministic failure → routes to code-worker; inject a plan-breaking issue → re-plan without a human. Builds on US2's dev graph.

- [x] T073 [US3] Write failing test for bounded retry per issue type (deterministic → code_worker; transient/infra → exponential backoff) in `tests/integration/test_dev_workflow.py`
- [x] T074 [US3] Implement issue-category routing and bounded retry loops as LangGraph conditional edges in `src/ai_factory/dev_workflow/graph.py` (FR-013, FR-014)
- [x] T075 [US3] Write failing test for escalation to the appropriate role in `tests/integration/test_dev_workflow.py`
- [x] T076 [US3] Implement escalation edges (route to code_worker / technical_planner / infrastructure) in `src/ai_factory/dev_workflow/graph.py` (FR-013, FR-014)
- [x] T077 [US3] Write failing test that a retry/escalation limit exceeded triggers re-planning via the technical planner in `tests/integration/test_dev_workflow.py`
- [x] T078 [US3] Implement auto-re-plan (route back to technical_planner; produce updated TechnicalPlan + ADR if needed) in `src/ai_factory/dev_workflow/graph.py` (FR-015)
- [x] T079 [US3] Write failing test that the run stops for a human ONLY when re-planning fails (exit 5) in `tests/integration/test_dev_workflow.py`
- [x] T080 [US3] Implement the re-plan-failure stop-human path (surface impasse; preserve partial state) in `src/ai_factory/dev_workflow/graph.py` (FR-015)
- [x] T081 [US3] Write failing test for CRITICAL security handling (halt + immediate fix + full re-audit before merge) in `tests/integration/test_dev_workflow.py`
- [x] T082 [US3] Implement CRITICAL-security halt + re-audit gate in `src/ai_factory/dev_workflow/security_reviewer/reviewer.py` and `src/ai_factory/dev_workflow/graph.py` (FR-014, SC-007)
- [x] T083 [US3] Validate US3 against quickstart Scenario 3 and mark the US3 checklist item complete

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T084 [P] Add a `--format human` output path to every library CLI in `src/ai_factory/shared/cli_util.py` and `src/ai_factory/**/cli.py`
- [ ] T085 [P] Add end-to-end integration test: spec run + dev run as two distinct traces linked by `spec_version_id`/`spec_run_id` in `tests/integration/test_handoff.py` (FR-024, SC-016, SC-017)
- [ ] T086 [P] Add a `--resume` end-to-end test across the spec workflow (interrupt → resume) in `tests/integration/test_spec_workflow.py` (FR-020)
- [ ] T087 [P] Add a CI workflow (ruff + pytest unit/contract/integration) in `/home/helio/repos/ai-factory/.github/workflows/ci.yml`
- [ ] T088 [P] Add a top-level `README.md` with install (`uv sync`), the two-workflow model, and quickstart links in `/home/helio/repos/ai-factory/README.md`
- [ ] T089 [P] Audit all library CLIs for the library-CLI convention (JSON + human output, meaningful exit codes, redaction) in `src/ai_factory/shared/cli_util.py`
- [ ] T090 [P] Run the full quickstart suite (Scenarios 1–7) as integration tests and confirm all pass in `tests/integration/test_quickstart.py`