# Data Model: AI Software Development Factory

**Feature**: 001-ai-dev-factory | **Date**: 2026-08-09 | **Spec**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

Pydantic models for `FactoryState` and critical entities (R3). All
identifiers are stable strings. State transitions are named explicitly.
This document defines the **shape** of the data that crosses the two
workflows and the hand-off boundary; it does not define implementation
bodies.

---

## Cross-workflow hand-off (the boundary)

### SpecVersion
The stable reference a dev run consumes (FR-025). Emitted by the
Specification Workflow, persisted locally.

| Field | Type | Notes |
|-------|------|-------|
| `spec_version_id` | `str` | Stable, unique. The join key. |
| `spec_run_id` | `str` | The spec run that produced this version. |
| `version` | `int` | Monotonic per feature. |
| `intent` | `str` | What the feature is. |
| `rationale` | `str` | Why it matters (business value). |
| `acceptance_criteria` | `list[AcceptanceCriterion]` | Testable, unambiguous (FR-003). |
| `definition_of_done` | `str` | Verifiable completion criteria (FR-003). |
| `edge_cases` | `list[EdgeCase]` | Identified boundary conditions. |
| `clarifications` | `list[Clarification]` | Scope-critical Q&A (FR-006). |
| `assumptions` | `list[Assumption]` | Non-critical documented defaults (FR-006). |
| `approval_status` | `ApprovalStatus` | `draft` → `under_review` → `approved` → `superseded`. |
| `human_approved` | `bool` | False until the human gate passes (FR-005). |
| `supersedes` | `Optional[str]` | Prior `spec_version_id`, if an amendment (User Story 4). |
| `created_at` | `datetime` | |

**Lifecycle**: `draft` → `under_review` → (`approved` | `rejected`) →
(`superseded` by a later version). An amended approved spec produces a new
version that supersedes the prior and re-enters `under_review` (re-review
before re-approval).

---

## Specification Workflow entities

### FeatureRequest
| Field | Type | Notes |
|-------|------|-------|
| `raw_text` | `str` | The user's natural-language request. |
| `target_scope` | `Optional[str]` | Optional scope hint. |
| `constraints` | `list[str]` | |
| `linked_materials` | `list[str]` | Paths/URLs, if any. |

### AcceptanceCriterion
| Field | Type | Notes |
|-------|------|-------|
| `statement` | `str` | Testable, unambiguous (FR-003). |
| `verified_by` | `str` | How it will be checked (test/inspection). |

### EdgeCase
| Field | Type | Notes |
|-------|------|-------|
| `description` | `str` | |
| `expected_behavior` | `str` | |

### Clarification
| Field | Type | Notes |
|-------|------|-------|
| `question` | `str` | |
| `suggested_options` | `list[str]` | Bounded (FR-006). |
| `chosen_answer` | `Optional[str]` | Filled by the user. |
| `affects_section` | `str` | |

### Assumption
| Field | Type | Notes |
|-------|------|-------|
| `assumption` | `str` | |
| `rationale` | `str` | |
| `affects_section` | `str` | |

### ReviewDecision
| Field | Type | Notes |
|-------|------|-------|
| `decision` | `Literal["approve","reject"]` | (FR-004) |
| `criteria_checked` | `list[str]` | clarity, completeness, consistency, testability, edge-case coverage. |
| `findings` | `list[str]` | Specific reasons. |
| `targeted_sections` | `list[str]` | |

### SpecRoleInvocation (telemetry per spec-role call)
| Field | Type | Notes |
|-------|------|-------|
| `role` | `Literal["spec_agent","requirements_reviewer"]` | |
| `attempt` | `int` | 1-indexed. |
| `outcome` | `Literal["pass","fail","rework"]` | |
| `feedback` | `Optional[str]` | Rejection feedback, if any. |
| `telemetry` | `TelemetryRecord` | See below. |

---

## Development Workflow entities

### TechnicalPlan
| Field | Type | Notes |
|-------|------|-------|
| `plan_id` | `str` | Stable. |
| `spec_version_id` | `str` | Consumed by reference (FR-025). |
| `implementation_strategy` | `str` | |
| `affected_components` | `list[str]` | Services/modules/databases. |
| `api_schema_changes` | `list[str]` | API/schema/event changes. |
| `test_strategy` | `str` | |
| `subtasks` | `list[TechnicalSubtask]` | Ordered. |
| `adr_id` | `Optional[str]` | Linked ADR, if produced (FR-008). |
| `version` | `int` | |

### Assessment
| Field | Type | Notes |
|-------|------|-------|
| `complexity` | `Literal["low","medium","high"]` | |
| `technical_risk` | `Literal["low","medium","high"]` | |
| `architecture_impact` | `bool` | True triggers ADR (FR-008). |
| `test_scope` | `str` | |
| `security_surface` | `str` | e.g., "auth", "sensitive data", "none". |
| `documentation_required` | `bool` | |

### ArchitectureDecisionRecord (ADR) — conditional (FR-008)
| Field | Type | Notes |
|-------|------|-------|
| `adr_id` | `str` | |
| `title` | `str` | |
| `context` | `str` | |
| `decision` | `str` | |
| `rationale` | `str` | |
| `tradeoffs` | `list[str]` | |
| `alternatives` | `list[str]` | |
| `approvers` | `list[str]` | Reviewed at PR time (FR-023). |
| `date` | `date` | |

### ExecutionPlan (Orchestrator output, FR-009)
| Field | Type | Notes |
|-------|------|-------|
| `role` | `str` | |
| `model` | `str` | Per-role selection. |
| `capability_level` | `str` | From `capability_levels/` (R9). |
| `budget` | `Budget` | Token/cost/time. |
| `timeout` | `float` | Seconds. |
| `parallelization` | `Literal["serial","parallel"]` | |
| `retry_policy` | `RetryPolicy` | Per FR-014. |

### TechnicalSubtask
| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | |
| `description` | `str` | |
| `order` | `int` | |
| `depends_on` | `list[str]` | Subtask ids. |

### DevRoleInvocation (telemetry per dev-role call, FR-016)
| Field | Type | Notes |
|-------|------|-------|
| `role` | `Literal["technical_planner","orchestrator","code_worker","code_reviewer","test_engineer","test_runner","security_reviewer"]` | |
| `model` | `str` | |
| `capability_level` | `str` | |
| `telemetry` | `TelemetryRecord` | |

### TelemetryRecord (FR-016)
| Field | Type | Notes |
|-------|------|-------|
| `tokens_in` | `int` | |
| `tokens_out` | `int` | |
| `cost` | `float` | |
| `latency` | `float` | Seconds. |
| `tool_calls` | `int` | |
| `retries` | `int` | |
| `errors` | `int` | |
| `escalations` | `int` | |
| `result` | `Literal["pass","fail","rework"]` | |
| `overspend` | `Optional[bool]` | Set when budget exceeded (FR-019). |

### Budget
| Field | Type | Notes |
|-------|------|-------|
| `tokens` | `Optional[int]` | |
| `cost_usd` | `Optional[float]` | Soft — never hard-stops (FR-019). |
| `time` | `Optional[float]` | |

### RetryPolicy (FR-014)
| Field | Type | Notes |
|-------|------|-------|
| `max_retries` | `int` | Bounded. |
| `backoff` | `Literal["exponential","none"]` | Exponential for transient/infra. |
| `on_limit_exceeded` | `Literal["escalate","replan","stop_human"]` | Replan by default (FR-015). |

### PullRequest (delivery artifact, FR-012/FR-022)
| Field | Type | Notes |
|-------|------|-------|
| `host` | `str` | e.g., "github", "gitlab". |
| `branch` | `str` | |
| `spec_version_id` | `str` | Linked approved spec. |
| `checks_status` | `Literal["pass","fail"]` | All checks must pass (FR-012). |
| `pr_url` | `str` | Factory-opened (FR-022). |
| `auto_merged` | `bool` | Always false (FR-012). |

### Issue / RePlan (issue handling, FR-013/014/015)
| Field | Type | Notes |
|-------|------|-------|
| `issue_id` | `str` | |
| `category` | `Literal["infrastructure","technical_limitation","logic_bug","security","data_edge_case","third_party"]` | |
| `root_cause_class` | `str` | |
| `retry_attempts` | `list[RetryAttempt]` | |
| `escalation_target` | `Optional[str]` | Role, if escalated. |
| `replan_outcome` | `Optional[RePlanOutcome]` | If re-planned. |
| `severity` | `Literal["critical","high","medium","low"]` | Critical halts + re-audits (FR-014). |

---

## Cross-cutting

### Checkpoint (FR-020)
| Field | Type | Notes |
|-------|------|-------|
| `run_id` | `str` | |
| `workflow` | `Literal["spec","dev"]` | |
| `phase` | `str` | Role/phase boundary. |
| `state_ref` | `str` | Reference to persisted state (LangGraph checkpointer). |
| `completed` | `bool` | |
| `created_at` | `datetime` | |

### ApprovalStatus (enum)
`draft` | `under_review` | `approved` | `rejected` | `superseded`

### RunState (top-level run envelope)
| Field | Type | Notes |
|-------|------|-------|
| `run_id` | `str` | |
| `workflow` | `Literal["spec","dev"]` | Two independent workflows (FR-024). |
| `spec_version_id` | `Optional[str]` | Dev runs carry this + `spec_run_id` (FR-025). |
| `spec_run_id` | `Optional[str]` | Traceability back to the spec run (SC-017). |
| `checkpoints` | `list[Checkpoint]` | Resumability (FR-020). |
| `telemetry` | `list[SpecRoleInvocation \| DevRoleInvocation]` | |

---

## State transitions (named)

- **Spec approval**: `draft → under_review → (approved | rejected)`;
  `approved → superseded` (on amendment, re-enters `under_review`).
- **Dev run**: `planned → executing → (delivered | failed | stopped_human)`.
  `stopped_human` only when re-planning itself fails (FR-015).
- **PR**: `opened` (terminal for the factory; merge is the user's action).

---

## Validation rules (from requirements)

- `AcceptanceCriterion.statement` MUST be testable and unambiguous (FR-003).
- `SpecVersion.human_approved` MUST be true before `approval_status=approved`
  (FR-005).
- `PullRequest.auto_merged` MUST always be false (FR-012/FR-022).
- `TelemetryRecord` MUST NOT contain secret-looking values (FR-018) —
  enforced by the redaction library before emission.
- `ADR` is present iff `Assessment.architecture_impact` is true (FR-008).
- Dev `RunState.spec_version_id` MUST reference an approved, human-approved
  `SpecVersion` (FR-0025).