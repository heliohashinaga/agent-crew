# Feature Specification: AI Software Development Factory

**Feature Branch**: `001-ai-dev-factory`

**Created**: 2026-08-09

**Status**: Draft

**Input**: User description: "in folder docs exists the project brainstorm idea" — the reference design in `docs/ai-factory.md` describes an AI Software Development Factory with two decoupled workflows, nine stable roles, capability levels, issue handling, and automatic re-planning that delivers a pull request on a branch for the user to review and merge.

## Clarifications

### Session 2026-08-09

- Q: How should the factory protect LLM-provider credentials and any secrets it encounters in the target codebase? → A: Credentials are loaded only from the environment or a dedicated secret store; secret-looking values read from the codebase are auto-redacted from logs and telemetry.
- Q: What should the factory do when an execution run exceeds the Orchestrator's cost budget before all checks pass? → A: Continue the run to completion, emit a warning, and report the overspend in telemetry; do not hard-stop solely on budget overrun.
- Q: If a factory run is interrupted (process crash, manual cancel, host reboot) mid-execution, what should happen to the partially completed run? → A: Runs are resumable; the run is checkpointed at role/phase boundaries, and a re-launch continues from the last completed checkpoint.
- Q: How should the factory execute the AI-generated code and tests it produces during a development run? → A: Inside an isolated container/sandbox by default, with the target repository mounted read-write and the rest of the host isolated.
- Q: What does "deliver a pull request" mean for v1 — should the factory itself open the PR on a remote git host, or prepare a local branch and leave opening the PR to the user? → A: The factory opens the PR itself on the remote git host via the host's API, using host credentials from the secret store.
- Q: After the Technical Plan and any ADR are produced but before coding begins, must a human approve the plan/ADR, or does the factory proceed autonomously? → A: The factory proceeds autonomously from the approved spec through planning and execution to PR delivery; humans only approve the spec and merge the PR; ADRs are reviewed at PR time.
- Q: Are the Specification Workflow and Development Workflow one combined workflow or two separate workflows? → A: Two separate workflows — the Specification Workflow and the Development Workflow are distinct, independent workflows rather than a single merged one, with the approved-spec hand-off as a clean boundary.
- Q: How is the result of the spec-workflow joined to the dev-workflow if they are two separate workflows? → A: By version reference — the spec-workflow emits an approved Spec with a stable spec_version_id; a dev run takes that spec_version_id as input, loads the spec by reference (no re-derivation), and carries spec_version_id and the originating spec_run_id so the two separate workflows remain linked and traceable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Specify a Feature from a Natural-Language Request (Priority: P1)

A user submits a feature idea or change request as plain text. The
Specification Workflow turns that request into a **validated, approved
specification** that captures *what* the feature is and *why* it matters —
its intent, rationale, testable acceptance criteria, a definition of done,
and identified edge cases — **without writing any implementation code** and
**without performing codebase-specific technical refinement**. The Spec
Agent role drafts the specification; the Requirements Reviewer role
validates it for clarity, completeness, consistency, testability, and
edge-case coverage; a human approves it before it is final.

**Why this priority**: A specification is the entry point to the entire
factory. Without a request becoming a structured, validated, approved spec,
the Development Workflow has no trustworthy input. This is the
Specification Workflow's heartbeat and the first link of the chain.

**Independent Test**: Submit one concrete feature request (e.g., "add a
password-reset flow") and receive an approved specification containing a
clear intent, rationale, testable acceptance criteria, a definition of
done, and at least one identified edge case — containing no implementation
code — without invoking the Development Workflow.

**Acceptance Scenarios**:

1. **Given** a single feature request as text, **When** the Specification
   Workflow runs, **Then** the Spec Agent role produces a draft
   specification containing intent, rationale, acceptance criteria,
   definition of done, and edge cases.
2. **Given** the draft specification, **When** the Requirements Reviewer
   role validates it, **Then** it returns an explicit Approve or Reject
   with specific reasons; on Reject it routes back to the Spec Agent role
   with actionable feedback.
3. **Given** a specification that passes Requirements Reviewer validation,
   **When** it is presented for finalization, **Then** a human approves or
   rejects it before it is marked final and consumable by the Development
   Workflow.
4. **Given** a request with a scope-critical ambiguity, **When** the
   Spec Agent role detects it, **Then** it surfaces a bounded set of
   clarifications with suggested options rather than silently guessing.

---

### User Story 2 - Build and Deliver a Pull Request from an Approved Spec (Priority: P1)

Given an approved specification, the Development Workflow plans the work
technically, orchestrates execution across coding, review, testing, and
security, and delivers a **pull request on a branch** with all checks
passed, ready for the user to review and merge. The Technical Planner maps
the spec to existing components, assesses complexity/risk/test
scope/security surface, and produces a technical plan (and an ADR only if
an architecturally significant decision is present). The Orchestrator then
decides per-role model, capability level, budget, timeout,
parallelization, and retry policy. Execution runs the Code Worker, Code
Reviewer, Test Engineer + Test Runner, and Security Reviewer roles, with
documentation produced when required.

**Why this priority**: This is the factory's core value — turning an
approved spec into reviewable, mergeable code. Without it the factory does
not produce software. It is the Development Workflow's heartbeat and the
second link of the chain, and it is where the bulk of the factory's
distinctive behavior (orchestration, capability levels, issue handling)
lives.

**Independent Test**: Given an approved specification, run the Development
Workflow end-to-end and receive a pull request on a branch with passing
code review, tests, and security review — without re-deriving requirements
and without auto-merging to the main branch.

**Acceptance Scenarios**:

1. **Given** an approved specification, **When** the Development Workflow
   begins, **Then** the Technical Planner role produces a technical plan
   and an assessment (complexity, technical risk, architecture impact, test
   scope, security surface, documentation required) by mapping the spec to
   existing components and identifying dependencies and risks.
2. **Given** the technical assessment, **When** the Orchestrator role
   decides, **Then** it produces an Execution Plan specifying per-role
   model, capability level, budget, timeout, parallelization, and retry
   policy based on the assessment.
3. **Given** the Execution Plan, **When** execution runs, **Then** the Code
   Worker produces implementation and unit tests with local validation
   passing, the Code Reviewer validates and approves, the Test Engineer +
   Test Runner produce and run the test suite with passing evidence, and
   the Security Reviewer assesses and approves.
4. **Given** all checks have passed, **When** the workflow completes,
   **Then** it delivers a pull request on a branch ready for a human to
   review and merge, and it does NOT auto-merge to the main branch.
5. **Given** the assessment indicates documentation is required, **When**
   execution completes, **Then** the relevant documentation (e.g., README,
   API docs, runbooks) is produced and updated.

---

### User Story 3 - Handle Issues Automatically with Retry, Escalation, and Re-Planning (Priority: P1)

When issues emerge during execution — across infrastructure, technical
limitations, logic bugs, security, data-driven edge cases, and third-party
integration — the factory **handles them as part of the design**: it
retries locally within bounded limits, escalates to the appropriate role
when local retry fails, and re-plans with the Technical Planner when issues
break core Technical Plan assumptions. When a retry/escalation limit is
exceeded, the factory **automatically re-plans**; it stops to ask a human
**only when re-planning itself fails** to produce a viable plan.

**Why this priority**: Issues are expected in real software development.
A factory that cannot absorb them either loops forever, produces broken
PRs, or stops constantly for human intervention. Automatic retry,
escalation, and re-planning are what make the factory autonomous in
practice and are a core principle of the reference design.

**Independent Test**: Inject a reproducible issue (e.g., a failing
deterministic test) mid-execution and observe the factory route it to the
Code Worker for a fix; inject a deeper issue that breaks a planning
assumption and observe the factory re-plan via the Technical Planner
without asking a human.

**Acceptance Scenarios**:

1. **Given** a deterministic, reproducible issue rooted in current code
   with no architectural change needed, **When** it is detected, **Then**
   the factory retries locally via the appropriate role within a bounded
   retry limit.
2. **Given** a transient or infrastructure failure (e.g., network
   timeout, container restart), **When** it is detected, **Then** the
   factory retries with exponential backoff up to a bounded limit before
   escalating to infrastructure.
3. **Given** an issue whose root cause is a design decision affecting
   multiple components or requiring an ADR, **When** it is detected,
   **Then** the factory escalates to the Technical Planner to re-assess.
4. **Given** a retry or escalation limit is exceeded, **When** the factory
   handles it, **Then** it automatically re-plans via the Technical Planner
   to produce an updated Technical Plan (and ADR if applicable).
5. **Given** re-planning itself fails to produce a viable plan, **When**
   the factory cannot proceed, **Then** it stops and surfaces the impasse
   to a human rather than looping indefinitely.
6. **Given** a CRITICAL security issue is found, **When** it is detected,
   **Then** the factory halts implementation, triggers an immediate fix,
   and requires a full security re-audit before merge.

---

### User Story 4 - Right-Size Execution via Capability Levels and Orchestrator Decisions (Priority: P2)

The Orchestrator acts as a **decision layer** (it does no specialized work
itself): from the Technical Planner's assessment, it selects per role and
per task the model, **capability level**, budget, timeout, parallelization,
and retry policy. Execution roles support capability levels — Code Worker
and Test Engineer at simple/standard/complex; Code Reviewer and Security
Reviewer at shallow/standard/deep — so execution intensity matches
complexity, risk, and security surface rather than being fixed.

**Why this priority**: The factory replaces "a new agent for every
variation" with a few stable roles plus capability levels plus intelligent
orchestration. Right-sizing execution is what keeps cost, latency, and
depth proportional to the task, and it is a core principle of the
reference design.

**Independent Test**: Submit two tasks of clearly different complexity
(e.g., a one-line typo fix and a multi-service feature) and observe the
Orchestrator assign different capability levels, models, and budgets to
each based on the assessment.

**Acceptance Scenarios**:

1. **Given** a Technical Planner assessment, **When** the Orchestrator
   decides, **Then** it produces an Execution Plan specifying model,
   capability level, budget, timeout, parallelization, and retry policy
   per role.
2. **Given** an assessment of low complexity and low risk, **When** the
   Orchestrator selects levels, **Then** it chooses the lower capability
   levels and a smaller budget/timeout for the relevant roles.
3. **Given** an assessment whose security surface includes authentication
   or sensitive data, **When** the Orchestrator selects levels, **Then**
   it selects at least the deepest Security Reviewer level.
4. **Given** an execution that is a retry after a prior failure, **When**
   the Orchestrator re-plans, **Then** it raises the capability level by
   at least one step and adds validation depth (deeper review, more tests)
   and/or budget.

---

### User Story 5 - Make the Factory Observable and Data-Driven (Priority: P2)

For every role invocation, the factory records **per-task telemetry** —
role, model, capability level, tokens (input + output), cost, latency,
tool calls, retries, errors, escalations, and result (pass/fail/rework) —
exposed via the CLI in both machine-readable and human-readable forms.
This makes execution measurable so model selection, testing strategy,
planning quality, retry effectiveness, and cost/quality ratios can be
optimized over time.

**Why this priority**: The reference design treats observability as a
first-class principle ("measure to optimize"). Without telemetry the
factory cannot improve its own orchestration decisions or prove its
quality/cost claims; it would be a black box.

**Independent Test**: Run one feature through the factory end-to-end and
retrieve, for the resulting pull request, a complete telemetry record for
every role invocation including capability level, tokens, cost, latency,
retries, and escalations.

**Acceptance Scenarios**:

1. **Given** any role invocation during a run, **When** it completes,
   **Then** the factory records role, model, capability level, tokens
   (input + output), cost, latency, tool calls, retries, errors,
   escalations, and result.
2. **Given** a completed pull request, **When** a user requests its
   telemetry, **Then** the factory returns the full per-role telemetry
   record within seconds, in both a machine-readable and a human-readable
   format.
3. **Given** accumulated telemetry across many tasks, **When** a user
   compares capability levels and models, **Then** they can determine the
   cost/quality and latency trade-offs per role and task type.

---

### User Story 6 - Produce Architecture Decision Records Only When Needed (Priority: P3)

When the Technical Planner identifies a **significant architectural
decision** — a non-conventional choice, an important trade-off, a
workaround for a constraint, a legacy/system limitation, or an unusual bug
fix — the factory produces an Architecture Decision Record (ADR)
documenting the decision, rationale, trade-offs, and alternatives
considered. The Code Reviewer validates adherence to the ADR, and the ADR
becomes the source of truth during implementation. ADRs are **skipped**
for simple fixes and obvious optimizations that have no architectural
impact.

**Why this priority**: Conditional ADRs keep the design lightweight while
preserving traceability for the decisions that actually matter. This is a
core principle of the reference design and prevents both decision loss and
ADR noise.

**Independent Test**: Run two tasks — one involving a non-conventional
architectural trade-off and one a simple null-check fix — and observe an
ADR produced for the first and no ADR produced for the second.

**Acceptance Scenarios**:

1. **Given** a Technical Planner assessment that identifies a significant
   architectural decision, **When** planning completes, **Then** an ADR is
   produced recording decision, rationale, trade-offs, and alternatives
   considered.
2. **Given** a change assessed as simple with no architectural impact
   (e.g., a null-check fix, adding an index), **When** planning completes,
   **Then** no ADR is produced.
3. **Given** an ADR exists for a task, **When** the Code Reviewer
   validates the implementation, **Then** it checks adherence to the ADR,
   and the ADR serves as the source of truth during implementation.

---

### Edge Cases

- **What happens when the Spec Agent's output is malformed or missing
  required fields?** The factory MUST detect the malformed output and
  re-request it, bounded by a retry limit before escalating to the user.
- **What happens when an empty or trivial request is submitted?** The
  factory MUST reject it early with a clear reason rather than fabricating
  a spec.
- **What happens when the request contains conflicting constraints?** The
  factory MUST flag the conflict and request resolution before producing
  a draft.
- **What happens when a CRITICAL security issue is found during
  execution?** The factory MUST halt implementation, trigger an immediate
  fix, and require a full security re-audit before merge (User Story 3,
  scenario 6).
- **What happens when repeated reject cycles in the Spec Workflow exceed a
  bounded threshold?** The factory MUST stop, preserve partial state, and
  surface the impasse to the user.
- **What happens when re-planning itself fails to produce a viable plan?**
  The factory MUST stop and ask a human rather than looping indefinitely
  (User Story 3, scenario 5).
- **What happens when all checks pass but the user rejects the pull
  request at merge?** Merging is the user's call; the factory MUST NOT
  auto-merge to the main branch.
- **What happens when a transient test failure persists beyond the
  backoff retry limit?** The factory MUST escalate to infrastructure
  rather than treating it as a code bug.
- **What happens when a run is interrupted (crash, cancel, reboot)?** The
  factory MUST checkpoint at role/phase boundaries and resume from the last
  completed checkpoint on re-launch, re-running no completed work.
- **What happens when the execution sandbox cannot be started (no container
  runtime available)?** The factory MUST fail the run early with a clear
  reason rather than falling back to running AI-generated code directly on
  the host.
- **What happens when the git host is unreachable, or host credentials are
  missing or invalid, at delivery time?** The factory MUST fail delivery with
  a clear reason and keep the local branch intact, rather than silently
  retrying indefinitely or auto-merging.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The factory MUST provide two decoupled workflows — a
  Specification Workflow that defines *what* and *why*, and a Development
  Workflow that defines *how/build/prove/assess*. The Specification
  Workflow MUST NOT perform codebase-specific technical refinement.
- **FR-002**: The Specification Workflow MUST accept a feature request as
  text and, via the Spec Agent role, produce a draft specification
  containing intent, rationale, testable acceptance criteria, a definition
  of done, and identified edge cases — without writing implementation code.
- **FR-003**: Every acceptance criterion produced MUST be testable and
  unambiguous; every specification MUST include a clear, verifiable
  definition of done.
- **FR-004**: The Requirements Reviewer role MUST validate each draft
  specification against clarity, completeness, consistency, testability,
  and edge-case coverage, returning an explicit Approve or Reject with
  specific reasons; on Reject, the workflow MUST route the specification
  back to the Spec Agent role with actionable feedback.
- **FR-005**: A human approval gate MUST be enforced before a
  specification is considered final and before it is consumable by the
  Development Workflow.
- **FR-006**: The Specification Workflow MUST surface scope-critical
  ambiguity in a request as a bounded set of clarifications with suggested
  options, and MUST make informed, documented assumptions only for
  non-scope-critical details.
- **FR-007**: The Development Workflow MUST consume an approved
  specification and, via the Technical Planner role, produce a technical
  plan and an assessment — complexity, technical risk, architecture impact,
  test scope, security surface, and documentation required — by mapping
  the spec to existing components, identifying dependencies and risks, and
  planning the test strategy.
- **FR-008**: The Technical Planner role MUST produce an Architecture
  Decision Record (ADR) ONLY when a significant architectural decision is
  present (non-conventional choice, important trade-off, workaround,
  legacy/system constraint, or unusual bug fix); it MUST NOT produce an
  ADR for simple fixes or obvious optimizations. Each ADR MUST record
  decision, rationale, trade-offs, and alternatives considered.
- **FR-009**: The Orchestrator role MUST act as a decision layer only — it
  MUST NOT perform specialized work — and MUST, from the Technical
  Planner's assessment, produce an Execution Plan specifying per-role
  model, capability level, budget, timeout, parallelization, and retry
  policy.
- **FR-010**: The factory MUST support capability levels per execution
  role: Code Worker and Test Engineer at simple/standard/complex, and
  Code Reviewer and Security Reviewer at shallow/standard/deep. Higher
  levels MUST correspond to greater depth, context, iterations, and tool
  access.
- **FR-011**: Execution MUST run the Code Worker (implementation and unit
  tests, with local validation), the Code Reviewer, the Test Engineer +
  Test Runner, and the Security Reviewer roles; documentation (e.g.,
  README, API docs, runbooks) MUST be produced when the assessment
  requires it.
- **FR-012**: The factory MUST deliver, as the output of the Development
  Workflow, a pull request on a branch with all checks passed, ready for a
  human to review and merge. The factory MUST NOT auto-merge to the main
  branch.
- **FR-013**: The factory MUST handle issues that emerge during execution
  across at least the categories infrastructure, technical limitations,
  logic bugs, security, data-driven edge cases, and third-party
  integration — via bounded automatic retry loops, escalation to the
  appropriate role, and re-planning.
- **FR-014**: Retry loops MUST be bounded per issue type; transient and
  infrastructure failures MUST use exponential backoff; deterministic
  failures MUST be routed to the Code Worker for a fix; CRITICAL security
  issues MUST halt implementation, trigger an immediate fix, and require a
  full re-audit before merge.
- **FR-015**: When a retry or escalation limit is exceeded, the factory
  MUST automatically re-plan by routing back to the Technical Planner to
  reassess and produce an updated Technical Plan (and ADR if applicable);
  the factory MUST stop and ask a human ONLY when re-planning itself fails
  to produce a viable plan.
- **FR-016**: The factory MUST be observable: for every role invocation it
  MUST record role, model, capability level, tokens (input + output),
  cost, latency, tool calls, retries, errors, escalations, and result
  (pass/fail/rework), exposed via the CLI in both machine-readable and
  human-readable forms.
- **FR-017**: Every capability of the factory MUST be built as a
  standalone, independently testable library with a single clear purpose,
  each exposed through a command-line interface with machine-readable
  (JSON) and human-readable output and meaningful exit codes — per the
  project constitution.
- **FR-018**: The factory MUST load LLM-provider credentials only from the
  environment or a dedicated secret store — never from committed
  configuration — and MUST auto-redact secret-looking values read from the
  target codebase from all logs and telemetry before emission.
- **FR-019**: When an execution run exceeds the Orchestrator's cost budget
  before all checks pass, the factory MUST emit a warning, continue the
  run to completion, and report the overspend in telemetry; it MUST NOT
  hard-stop or abandon the run solely because the budget was exceeded.
- **FR-020**: A development run MUST be resumable: it MUST checkpoint progress
  at role/phase boundaries, and a re-launch of an interrupted run MUST
  continue from the last completed checkpoint rather than restarting from
  scratch.
- **FR-021**: The factory MUST execute AI-generated code and tests produced
  during a development run inside an isolated container or sandbox by
  default, mounting the target repository read-write while isolating the
  rest of the host.
- **FR-022**: The factory MUST open the pull request itself on the remote
  git host via the host's API, using host credentials loaded from the
  environment or a dedicated secret store; it MUST NOT auto-merge the PR
  to the main branch.
- **FR-023**: The Development Workflow MUST proceed autonomously from the
  approved specification through planning and execution to pull-request
  delivery without requiring a human to approve the Technical Plan or any
  ADR. Human gates are limited to (a) approving the final specification and
  (b) reviewing and merging the pull request; ADRs are recorded for human
  review at PR time.
- **FR-024**: The Specification Workflow and the Development Workflow MUST be
  two separate, independent workflows rather than a single merged workflow.
  The hand-off from an approved specification to a development run MUST be
  a clean boundary (the spec run and the dev run are separate, with the dev
  run referencing the approved spec version it consumes).
- **FR-025**: The hand-off from the Specification Workflow to the Development
  Workflow MUST be by version reference: the Specification Workflow MUST
  emit an approved Specification with a stable `spec_version_id`, persisted
  locally; a Development run MUST accept that `spec_version_id` as input,
  load the corresponding approved Specification by reference (not re-derive
  requirements), and carry `spec_version_id` and the originating
  `spec_run_id` so each Development run is traceable back to the
  Specification run that produced it.

### Key Entities *(include if feature involves data)*

- **Feature Request**: User-supplied input describing the feature or
  change. Attributes: raw text, target scope (if any), constraints, linked
  materials.
- **Specification**: The artifact produced by the Specification Workflow.
  Attributes: intent, rationale, acceptance criteria, definition of done,
  edge cases, version, approval status (draft / under-review / approved /
  rejected / superseded). Relationships: supersedes prior versions;
  consumable by zero or more Development runs.
- **Acceptance Criterion / Definition of Done / Edge Case**: Sub-artifacts
  of a Specification. Attributes: testable statement; verifiable
  completion criteria; described boundary condition.
- **Clarification / Assumption**: Scope-critical question surfaced to the
  user (with options and chosen answer), vs. a non-critical documented
  default. Relationships: belong to one Specification version.
- **Review Decision**: Outcome of a Requirements Reviewer validation pass.
  Attributes: decision, criteria checked, specific findings, targeted
  sections. Relationships: belongs to one Specification version; a human
  approval finalizes it.
- **Technical Plan**: The artifact produced by the Technical Planner.
  Attributes: implementation strategy, affected components/services/
  databases, API/schema/event changes, test strategy, ordered technical
  subtasks, version. Relationships: derived from one approved
  Specification; may reference an ADR.
- **Assessment**: The Technical Planner's evaluation. Attributes:
  complexity, technical risk, architecture impact, test scope, security
  surface, documentation required. Relationships: input to the
  Orchestrator.
- **Architecture Decision Record (ADR)**: Conditional artifact. Attributes:
  title, context, decision, rationale, trade-offs, alternatives
  considered, approvers, date. Relationships: belongs to one Technical
  Plan; validated by the Code Reviewer.
- **Execution Plan**: The Orchestrator's output. Attributes: per-role
  model, capability level, budget, timeout, parallelization, retry
  policy. Relationships: derived from one Assessment.
- **Code / Test Suite / Test Evidence / Security Assessment /
  Documentation**: Execution artifacts produced by the Code Worker, Test
  Engineer + Test Runner, and Security Reviewer. Attributes: content,
  pass/fail status, evidence.
- **Pull Request**: The final delivery artifact, created by the factory on
  the remote git host via the host's API. Attributes: host, branch, linked
  approved spec version, checks status, PR URL/identifier. Relationships:
  the user reviews and merges; the factory does not auto-merge.
- **Role Invocation (Telemetry Record)**: A single execution of a role.
  Attributes: role, model, capability level, tokens (input + output),
  cost, latency, tool calls, retries, errors, escalations, result.
- **Issue / Retry Attempt / Escalation / Re-Plan**: Issue-handling
  artifacts. Attributes: issue category, root-cause class, retry count,
  escalation target, re-plan outcome.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can submit a single natural-language feature request
  and receive a fully approved specification (intent, rationale, testable
  acceptance criteria, definition of done, edge cases) — with no
  implementation code — in a single continuous run in the majority of
  cases.
- **SC-002**: Given an approved specification, the factory delivers a pull
  request on a branch with all checks (code review, tests, security)
  passed; the only remaining human action is to review and merge.
- **SC-003**: At least 80% of issues that emerge during execution are
  resolved automatically by retry, escalation, or re-planning without human
  intervention.
- **SC-004**: When a retry or escalation limit is exceeded, the factory
  auto-re-plans; it stops to ask a human only when re-planning itself
  fails to produce a viable plan.
- **SC-005**: For any delivered pull request, the user can retrieve, within
  seconds, the complete per-role telemetry (role, capability level,
  tokens, cost, latency, retries, escalations, result) in both
  machine-readable and human-readable forms.
- **SC-006**: The factory's per-task cost, latency, and retry rate can be
  compared across capability levels and models so the most cost-effective
  execution configuration for a given task type is identifiable.
- **SC-007**: No pull request is delivered with an unresolved CRITICAL
  security finding; CRITICAL findings halt implementation and require a
  full re-audit before merge.
- **SC-008**: Architecture Decision Records are produced only for
  architecturally significant decisions: changes assessed as simple with
  no architectural impact produce zero ADRs.
- **SC-009**: An approved specification can be produced without triggering
  any implementation, and a development run consumes a specific approved
  spec version — the two workflows remain decoupled and independently
  triggerable.
- **SC-010**: No LLM-provider credential or codebase secret appears in any
  log or telemetry output of the factory — verifiable by scanning all
  emitted logs and telemetry for known secret patterns and credential
  values and finding zero matches.
- **SC-011**: When a run exceeds its cost budget, a warning is emitted and
  the overspend is recorded in telemetry, and the run is not aborted solely
  on budget grounds (verifiable by driving a run over budget and asserting
  the run completes with a recorded overspend entry).
- **SC-012**: An interrupted development run can be resumed from its last
  completed checkpoint, re-running no already-completed role or phase
  (verifiable by interrupting a run and confirming the resumed run skips
  completed checkpoints).
- **SC-013**: AI-generated code and tests execute inside an isolated sandbox
  with the host otherwise protected — verifiable by running a development
  task and asserting the generated code/tests cannot touch host resources
  outside the mounted repository.
- **SC-014**: The factory opens the pull request on the remote git host via
  the host's API — verifiable by running a development task and asserting a
  PR is created on the host, with credentials sourced from the secret
  store and the PR not auto-merged.
- **SC-015**: A development run proceeds from the approved specification to
  a delivered pull request with no human-approval step between planning
  and execution (verifiable by running a development task end-to-end and
  asserting no plan/ADR approval gate interrupts the run).
- **SC-016**: The Specification Workflow and the Development Workflow are
  two separate workflows — verifiable by finding the specification run and
  the development run as two distinct runs, with the development run
  referencing the approved spec version.
- **SC-017**: A Development run accepts a `spec_version_id` as input and
  carries `spec_version_id` and `spec_run_id` so it is traceable back to
  the originating Specification run — verifiable by starting a dev run from
  an approved spec and asserting the dev run carries the correct
  `spec_version_id` and `spec_run_id` and loaded the spec by reference with
  no re-derivation of requirements.

## Assumptions

- v1 delivery target is a **pull request on a branch**; the **factory
  opens the PR itself** on the remote git host via the host's API using host
  credentials from the secret store; the user reviews and merges; the
  factory does not auto-merge to the main branch.
- On retry/escalation limit exceeded, the factory **auto-re-plans**; it
  stops to ask a human only when re-planning itself fails to produce a
  viable plan.
- The factory comprises **nine stable roles** across the two workflows:
  Spec Agent and Requirements Reviewer (Specification); Technical Planner,
  Orchestrator, Code Worker, Code Reviewer, Test Engineer, Test Runner,
  and Security Reviewer (Development). Documentation is produced by the
  Code Worker when the assessment requires it.
- **Capability levels**: Code Worker and Test Engineer use
  simple/standard/complex; Code Reviewer and Security Reviewer use
  shallow/standard/deep. The exact model, token budget, iteration count,
  and tool-access mapping per level is an implementation decision left to
  planning.
- The factory is governed by the project **constitution** (library-first,
  CLI interface, test-first, integration testing, simplicity &
  observability) and the **Spec Kit flow** (constitution → specify → plan
  → tasks → implement, in that order, before code).
- The runtime, language, frameworks, orchestration substrate, and
  observability backend (e.g., the pi-vs-LangGraph, pydantic, and LangSmith
  decisions discussed in `docs/`) are implementation decisions left to
  planning; this specification is agnostic to them. The Specification and
  Development Workflows are two separate workflows (FR-024) regardless of
  which observability backend is chosen.
- v1 collects **basic per-task telemetry** (tokens, cost, latency, retries,
  escalations, results); advanced tracing and evaluation frameworks are
  deferred beyond v1.
- **Human-in-the-loop gates**: a human approves the final specification and
  a human reviews and merges the pull request; there is no human gate
  between planning and execution (the factory proceeds autonomously), and
  the factory escalates to a human only when re-planning fails.
- The maximum number of clarifications per spec, retries per issue type,
  and re-plan attempts follow **documented bounded defaults**; the exact
  caps are implementation decisions left to planning.
- **Multi-feature batch runs** are out of scope for v1: the factory
  processes one feature per run.
- **Cross-host sharing** of specifications, plans, and telemetry is out of
  scope for v1; artifacts are persisted locally.
- The Specification Workflow produces the feature specification (intent,
  rationale, acceptance criteria, definition of done, edge cases) only;
  the technical plan and task breakdown belong to the Development
  Workflow's Technical Planner.
