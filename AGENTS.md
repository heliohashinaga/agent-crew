# AGENTS.md — ai-factory

Guidance for AI coding agents working in this repository.

## Project

The **AI Software Development Factory** turns a natural-language feature
request into a reviewed, merge-ready pull request. It has **two independent
workflows** — a **Specification Workflow** (what/why: request → approved,
versioned spec) and a **Development Workflow** (how/build/prove/assess:
approved spec folder → plan → orchestrated execution → PR). `dev-run <folder>`
enters directly from an approved speckit spec folder; traceability derives from
the folder feature name, not a factory-issued `spec_version_id` (the standalone
`spec-run`/`spec-workflow` entry was removed, FR-006/009).

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

- A folder-driven `dev-run` enters directly from an approved speckit spec
  folder (`spec.md` / `plan.md` / `tasks.md`) and runs the `dev_workflow`
  StateGraph as a distinct observable run.
- The factory never re-derives or re-clarifies requirements (FR-005); it
  consumes the approved folder as-is. Traceability identity is the folder
  feature name (FR-011/012); the standalone `spec_workflow` entry and the
  `spec_version_id` join key were removed (FR-006/009).

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
