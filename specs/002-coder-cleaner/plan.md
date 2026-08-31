# Implementation Plan: Coder → Cleaner Agent Pipeline

**Branch**: `004-coder-cleaner` | **Date**: 2026-08-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-coder-cleaner/spec.md`

## Summary

Deliver the first **multi-node LangGraph orchestration** in `agent-crew`: a
two-stage pipeline where a **coder** agent writes code from a task and a
**cleaner** agent refines it (semantic clean code). This is the first concrete
agent-to-agent handoff in the swarm vision. The graph plumbing runs fully offline
(testable with mocked node outputs, credential-free); the LLM-backed coder and
semantic cleaner reuse the existing provider infra and remain opt-in. Formatting
is delegated to Black/ruff, outside the cleaner (FR-005).

## Technical Context

**Language/Version**: Python ≥ 3.14 (managed with `uv`, already configured)

**Primary Dependencies**: adds `langgraph>=1.2.10` (explicit, FR-009); keeps
`langchain>=1.0`, `langchain-core>=1.0`, `langchain-openai>=0.3`,
`python-dotenv>=1.2.3`. InMemorySaver comes from `langgraph-checkpoint` (dev/test).

**Storage**: N/A across processes; InMemorySaver only for dev/tests if memory is
needed. Out of scope for durable persistence.

**Testing**: `pytest` (unit + contract + integration), `ruff` for lint. Follows
the existing markers (`unit`, `contract`, `integration`, `live`).

**Target Platform**: Python (CLI), cross-platform via `uv`

**Project Type**: library + CLI (`src-layout` package `agentcrew`)

**Constraints**: Graph offline-testable; Coder + semantic Cleaner LLM opt-in
(`ANTHROPIC`/OpenRouter/OpenCode keys via `.env`); formatting stays in
Black/ruff (FR-005).

**Scale/Scope**: Fixed linear two-node pipeline. No routing, loops, HITL, or
cross-process persistence.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Principles from `.specify/memory/constitution.md`:

1. **I. Library-First** — PASS. Agents live as standalone library nodes under
   `src/agentcrew/agents/`; the graph under `src/agentcrew/graphs/` *composes*
   them. CLI composes the graph; the reverse never happens.
2. **II. CLI Interface** — PASS. `agentcrew-code` exposes the pipeline with
   text/JSON output and exit codes `0`/`1`/`4`.
3. **III. Test-First (NON-NEGOTIABLE)** — PASS. Failing unit/contract tests
   precede implementation; documented in `tasks.md` (tests before code).
4. **IV. Integration Testing** — PASS. A contract test verifies the
   coder→cleaner handoff with mocked nodes (node-to-node handoff, FR-008); an
   end-to-end CLI run is included.
5. **V. Simplicity & Observability** — PASS. Minimal linear graph; the
   deterministic/LLM split keeps the offline slice simple; LangSmith tracing
   surfaces each node (observability).

**Result**: Gate passes. No complexity-tracking table required (no violations).

## Project Structure

### Documentation (this feature)

```text
specs/002-coder-cleaner/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (pipeline contract)
├── checklists/
│   └── requirements.md  # spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/agentcrew/
├── agents/
│   ├── __init__.py
│   ├── coder.py             # build_coder_node(): LLM-backed, task -> code
│   └── cleaner.py           # build_cleaner_node(): semantic clean code via LLM
│                            #   (formatting NOT here — FR-005)
├── graphs/
│   ├── __init__.py
│   └── coder_cleaner.py     # build_coder_cleaner_graph(): StateGraph coder->cleaner
├── nodes/
│   ├── __init__.py
│   ├── hello_world.py
│   ├── llm.py               # reused provider infra
│   └── models.py            # + CoderOutput / CleanerOutput / TaskState
└── ... (existing cli.py, llm_cli.py)

tests/
├── contract/test_coder_cleaner_graph.py  # handoff ordering + shape (mocked)
└── integration/test_coder_cleaner.py     # real LLM (marker integration/live)
```

**Structure Decision**: Keep the agents as standalone library nodes
(Library-First) and the graph as a *separate* composition layer, so nodes stay
independently testable and the graph stays a thin orchestration seam. The cleaner
holds a single responsibility — semantic clean code — and never formats.

## Complexity Tracking

No constitution violations — table intentionally omitted.