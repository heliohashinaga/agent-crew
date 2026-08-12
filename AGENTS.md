# AGENTS.md — ai-factory

Guidance for AI coding agents working in this repository.

## Project

The **AI Dev Factory** turns a natural-language feature
request into a reviewed, merge-ready pull request. Providers contribute **spec
role libraries** (a `spec_agent` that drafts a `SpecVersion` and a
`requirements_reviewer` that gates it) plus a **Development Workflow**
(how/build/prove/assess: approved spec folder → plan → orchestrated execution →
PR). `dev-run <folder>` is the factory's sole entry point: it enters directly
from an approved speckit spec folder; traceability derives from the folder
feature name, not a factory-issued `spec_version_id`. The standalone
`spec-run` entry and the `spec-workflow` production graph were removed
(FR-006/009); the spec role libraries are retained and independently tested.

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

- `dev-run <folder>` is the factory's only entry point: it enters directly from
  an approved speckit spec folder (`spec.md` / `plan.md` / `tasks.md`) and runs
  the `dev_workflow` StateGraph as a distinct observable run.
- The factory never re-derives or re-clarifies requirements (FR-005); it
  consumes the approved folder as-is. Traceability identity is the folder
  feature name (FR-011/012); there is no factory spec graph or
  `spec_version_id` join key (FR-006/009). The spec role libraries
  (`spec_workflow.spec_agent`, `spec_workflow.requirements_reviewer`) are
  standalone libraries under `src/ai_factory/spec_workflow/` with their own
  CLIs and contract tests — they do not form a factory production workflow.

## Role libraries

### `researcher` (mono-capacity lookup)

The `researcher` role (`src/ai_factory/researcher/`) is a **mono-capacity,**
**non-escalating** low-cost lookup library. It exposes
`lookup(query, *, scope=...)` and two scopes:

- **`repo`** — deterministic, **network-free** core (the default). It scans text
  files under the given roots, matches a tokenized query against file
  paths/names and (for small files) head contents, and returns a concise
  `ResearchResult` (`sources` of `ResearchSource` + a `summary` that fits the
  invoking role's context window — never a full-file dump).
- **`web`** — **network-bound**, Option D (multi-angle best-per-angle),
  layered on injectable collaborators
  (`LLMProvider` / `WebFetcher` / `ContentFetcher`) in
  `src/ai_factory/researcher/web.py`. Always integration-gated
  (`-m integration`) and skippable when network/LLM is unavailable.

`researcher` is a **fixed, non-escalating** role: it carries its own constant
mono-capacity `ResearcherProfile` (`profile.py`) and is deliberately **not**
part of `capability_levels.FIXED_ROLES` (no `bump_level`). Its execution
profile is `mono` — a single fixed capacity, never escalating.

The intended call site is a **library function seam**: a downstream
planner/coder node may call `researcher.lookup(...)` to gather a concise
summary before writing code. This pass documents that seam without wiring
it into every planner/coder node.

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

The factory now ships the folder-driven `dev-run` workflow plus a standalone
`researcher` mono-capacity lookup library (repo + web scopes). See the active
feature's `specs/003-researcher/tasks.md` for the current task list.
