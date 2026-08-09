# Implementation Plan: AI Software Development Factory

**Branch**: `001-ai-dev-factory` | **Date**: 2026-08-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-ai-dev-factory/spec.md`

## Summary

An autonomous AI software development factory that turns a natural-language
feature request into a reviewed, merge-ready pull request on a remote git
host. It is composed of **two independent workflows**: a **Specification
Workflow** (what/why: request → approved, versioned spec) and a **Development
Workflow** (how/build/prove/assess: approved spec → technical plan →
orchestrated execution → PR). The two are joined only by a **version
reference** (`spec_version_id`): a dev run consumes an approved spec by
reference and is traceable back to the spec run that produced it. Nine stable
roles span the two workflows; execution intensity is right-sized via
**capability levels** and an Orchestrator decision layer; issues are
absorbed by bounded retry, escalation, and automatic re-planning.

**Technical approach** (from research — see `research.md`): Python ≥ 3.14 +
`uv`, `src`-style packaging; **LangGraph** as the orchestration-graph
substrate (each workflow is a separate `StateGraph`); **Pydantic** for
`FactoryState` and critical models (validated state, LangSmith-friendly
serialization), `TypedDict`/`dict` only for non-critical parts; **LangSmith**
as the observability backend (two distinct top-level traces, linked by
`spec_version_id`/`spec_run_id` metadata). The factory itself is built
library-first: each role and capability is a standalone, independently
testable library exposed through a CLI, composed by the two workflows.

## Technical Context

**Language/Version**: Python ≥ 3.14, managed with `uv` (pinned by the
constitution). No NEEDS CLARIFICATION — settled.

**Primary Dependencies**:
- `langgraph` — orchestration graph substrate; one `StateGraph` per
  workflow, conditional edges for retry/escalation/re-plan, checkpointing
  for resumability (FR-020).
- `langsmith` — observability backend; two distinct top-level traces
  (spec run, dev run), linked by `spec_version_id`/`spec_run_id` metadata
  (FR-016, FR-024, FR-025, SC-016, SC-017).
- `pydantic` — `FactoryState` and critical models (runtime validation, IDE
  autocomplete, LangSmith serialization); `TypedDict`/`dict` for
  non-critical parts only.
- LLM provider SDK(s) — pluggable; selected per-role by the Orchestrator
  (FR-009). Exact provider set is an implementation decision (see
  `research.md`).
- Container runtime client (e.g., Docker) — sandboxed execution of
  AI-generated code/tests (FR-021, SC-013).
- Git host API client (e.g., GitHub/GitLab REST) — factory-opened PRs
  (FR-022, SC-014). Host support is pluggable per remote.

**Storage**:
- Local filesystem for v1: specs (versioned), technical plans, ADRs,
  checkpoints, telemetry records, run state. SQLite is a candidate for
  run/telemetry/query indexes but is **a Phase-1+ research item**, not v1
  mandatory — see `research.md`. Cross-host sharing is out of scope for v1
  (per spec Assumptions).

**Testing**: `pytest` (unit + integration), per constitution Principle III
(Test-First, NON-NEGOTIABLE) and Principle IV (Integration Testing). Each
library ships its own contract tests; workflow integration tests assert the
two-workflow boundary and the version-reference hand-off.

**Target Platform**: Linux/macOS developer host with a container runtime
available; the factory runs locally, drives a local checkout of the target
repo, and opens PRs on a remote git host.

**Project Type**: Library-first CLI application — a set of standalone,
independently testable libraries (one per role/capability), each exposed via
a CLI, composed by two thin workflow CLIs (spec-run, dev-run). No web UI,
no long-running service in v1.

**Performance Goals**: v1 is single-user, one feature per run (per spec
Assumptions). No throughput SLOs; the measurable goal is **end-to-end
correctness and observability**, not latency. Per-task latency/cost is
recorded as telemetry (FR-016), not bounded by a target.

**Constraints**:
- Credentials only from env/secret store; codebase secrets auto-redacted
  from logs/telemetry (FR-018, SC-010).
- AI-generated code runs in an isolated sandbox; host otherwise protected
  (FR-021, SC-013).
- No auto-merge to main (FR-012/FR-022).
- Cost budget is **soft** — continue + warn + record overspend, never
  hard-stop on budget (FR-019, SC-011).
- Runs are resumable from the last completed checkpoint (FR-020, SC-012).

**Scale/Scope**: v1 = one feature per run, one user, local artifacts. 9
roles, 2 workflows, capability-level variants per role. Batch runs,
multi-host, and concurrent users are explicitly out of scope (spec
Assumptions).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence / Plan |
|-----------|--------|-----------------|
| **I. Library-First** | ✅ PASS | FR-017 + Project Structure: each role/capability is a standalone, independently testable library; CLIs/workflows compose libraries, never the reverse. No organizational-only grouping libraries. |
| **II. CLI Interface** | ✅ PASS | FR-017: every library exposes JSON + human-readable output with meaningful exit codes; the two workflows are thin CLIs (`spec-run`, `dev-run`) over the libraries. |
| **III. Test-First (NON-NEGOTIABLE)** | ✅ PASS | Red-Green-Refactor enforced per task in `tasks.md`; contract tests per library; no implementation merge without user-approved passing tests. |
| **IV. Integration Testing** | ✅ PASS | Workflow integration tests at the two-workflow boundary (version-reference hand-off, separate traces); contract tests at every library seam. |
| **V. Simplicity & Observability** | ✅ PASS | LangSmith traces + structured per-role telemetry (FR-016); YAGNI applied (no batch, no multi-host, no web UI in v1); complexity justified in `research.md`. |

**Gate result**: PASS — no violations. No Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-dev-factory/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── spec-run-cli.md
│   ├── dev-run-cli.md
│   └── library-cli-convention.md
└── tasks.md             # Phase 2 output (/speckit.tasks — not created here)
```

### Source Code (repository root)

```text
src/ai_factory/
├── shared/                      # cross-workflow libraries
│   ├── state/                   # Pydantic FactoryState, run state, checkpoints
│   ├── secrets/                 # env/secret-store loaders + redaction
│   ├── telemetry/               # per-role telemetry record + emission
│   ├── sandbox/                 # container/sandbox runner for AI-generated code
│   ├── git_host/                # pluggable git-host API client (open PR)
│   ├── llm/                     # pluggable LLM provider abstraction
│   └── spec_store/              # versioned spec persistence (spec_version_id)
│
├── spec_workflow/              # Specification Workflow (LangGraph StateGraph)
│   ├── graph.py                #   the workflow graph
│   ├── spec_agent/             #   role library + CLI
│   └── requirements_reviewer/  #   role library + CLI
│
├── dev_workflow/               # Development Workflow (LangGraph StateGraph)
│   ├── graph.py                #   the workflow graph (planning → execution → PR)
│   ├── technical_planner/      #   role library + CLI (assessment + ADR)
│   ├── orchestrator/           #   role library + CLI (decision layer only)
│   ├── code_worker/            #   role library + CLI (impl + unit tests)
│   ├── code_reviewer/          #   role library + CLI
│   ├── test_engineer/          #   role library + CLI
│   ├── test_runner/            #   role library + CLI (executes tests in sandbox)
│   └── security_reviewer/      #   role library + CLI
│
├── capability_levels/         # per-role level definitions (simple/standard/complex, shallow/standard/deep)
│   └── levels.py               #   model/budget/timeout/tool-access mapping per level
│
└── cli/                       # thin workflow CLIs composing the libraries
    ├── spec_run.py             #   entrypoint: request → approved spec
    └── dev_run.py              #   entrypoint: spec_version_id → PR

tests/
├── unit/                       # one test module per library
├── contract/                   # contract tests per library seam
└── integration/
    ├── test_spec_workflow.py    # end-to-end spec workflow
    ├── test_dev_workflow.py    # end-to-end dev workflow
    └── test_handoff.py         # the two-workflow boundary + version reference
```

**Structure Decision**: Single-project, `src`-style packaging via
`pyproject.toml` (constitution-mandated), with internal packages organized by
workflow and by role. Every role/capability is a package with its own CLI
module (Library-First + CLI Interface), composed by two thin workflow CLIs.
The two workflows live in separate packages (`spec_workflow/`,
`dev_workflow/`) to keep them decoupled and independently testable (FR-024).
Shared infrastructure (state, secrets, telemetry, sandbox, git host, llm,
spec store) lives under `shared/` and depends on nothing workflow-specific.

## Complexity Tracking

> None — Constitution Check passes with no violations.