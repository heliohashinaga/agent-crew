# AGENTS.md — ai-factory

Guidance for AI coding agents working in this repository.

## Project

The **AI Software Development Factory** turns a natural-language feature
request into a reviewed, merge-ready pull request. It has **two independent
workflows** — a **Specification Workflow** (what/why: request → approved,
versioned spec) and a **Development Workflow** (how/build/prove/assess:
approved spec → plan → orchestrated execution → PR). They are joined only by
a **version reference** (`spec_version_id`): a dev run consumes an approved
spec by reference and is traceable back to the spec run that produced it.

Design artifacts live under `specs/001-ai-dev-factory/`:
`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`,
`quickstart.md`, `tasks.md`.

## Non-negotiable principles (from the constitution)

1. **Library-First** — every role/capability is a standalone, independently
   testable library under `src/ai_factory/`. Workflows and CLIs *compose*
   libraries; libraries never depend on a workflow. No organizational-only
   grouping libraries.
2. **CLI Interface** — every library exposes a CLI with JSON **and**
   human-readable output and meaningful exit codes.
3. **Test-First (TDD, NON-NEGOTIABLE)** — write a failing test before each
   implementation (Red–Green–Refactor). No code is merged without its
   passing tests.
4. **Integration Testing** — run the two-workflow boundary end-to-end in
   `tests/integration/`.
5. **Simplicity & Observability** — YAGNI; emit per-role telemetry
   (role, model, capability level, tokens, cost, latency, retries, errors,
   escalations, result).

## Workflow boundary

- `spec_workflow/` and `dev_workflow/` are separate LangGraph `StateGraph`s;
  each is a distinct observable run.
- The hand-off is `spec_version_id`: the spec workflow emits an approved,
  versioned `SpecVersion`; a dev run loads it **by reference** and carries
  `spec_version_id` + `spec_run_id` — never re-derives requirements.

## Conventions

- Python ≥ 3.14, managed with `uv`; `src`-layout package `ai_factory`.
- Harden: `ruff` + `pytest`. Run:
  - `uv run ruff check .`
  - `uv run pytest` (unit + contract; network blocked)
  - `uv run pytest -m integration` (end-to-end; needs network + container)
- Both the repository's `AGENTS.md` and the feature's `specs/.../tasks.md`
  take precedence over any generic guidance.
- Implement in task order; each task lists its exact file path.

## Task status

Current: **Phase 1 (Setup)** — project scaffolding (pyproject, package
skeleton, test skeleton, AGENTS.md). See `tasks.md` T001–T005.
