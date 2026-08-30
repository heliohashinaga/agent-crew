# Implementation Plan: LangChain Foundation — Hello-World Node

**Branch**: `001-langchain-hello-node` | **Date**: 2026-08-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-langchain-hello-node/spec.md`

## Summary

Establish the technical foundation for `agent-crew` on **LangChain**, proven
by a minimal, fully **offline and deterministic** "hello world" node. The node
accepts simple text input and returns a fixed greeting, running entirely without
external models, credentials, or network. This single vertical slice validates
the build, the source layout, the CLI, and the test suite — the base from which
future swarm nodes will grow.

## Technical Context

**Language/Version**: Python ≥ 3.14 (managed with `uv`, already configured)

**Primary Dependencies**: `langchain>=1.0`, `langchain-core>=1.0`, `pydantic>=2.0`
(already declared in `pyproject.toml`)

**Storage**: N/A — stateless single node, no persistence

**Testing**: `pytest` (unit + integration), `ruff` for lint

**Target Platform**: Python (CLI), cross-platform via `uv`

**Project Type**: library + minimal CLI (src-layout package `agentcrew`)

**Performance Goals**: N/A for a hello-world slice; deterministic and instant

**Constraints**: Offline/deterministic; zero credentials; zero network at
runtime; reproducible via lockfile

**Scale/Scope**: Single node, first slice. No orchestration, no live LLM.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The repository `AGENTS.md` supplies the constitution's non-negotiable
principles. Pass/fail evaluation:

1. **Library-First** — PASS. The node is a standalone library
   (`src/agentcrew/nodes/hello_world.py`); the CLI *composes* it, never the
   reverse.
2. **CLI Interface** — PASS. A CLI exposes the node with JSON + human-readable
   output and meaningful exit codes (`0` success / `4` error / `1` usage).
3. **Test-First (TDD, NON-NEGOTIABLE)** — PASS. A failing unit test precedes the
   implementation; no code merges without its passing tests.
4. **Integration Testing** — PASS. An end-to-end test runs the CLI and verifies
   real output/exit code.
5. **Simplicity & Observability** — PASS. Scope is deliberately minimal (YAGNI);
   the run emits a minimal structured result (observable) without adding
   telemetry machinery premature for a hello-world slice.

**Result**: Gate passes. No complexity-tracking table required (no violations).

## Project Structure

### Documentation (this feature)

```text
specs/001-langchain-hello-node/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/agentcrew/
├── __init__.py
├── nodes/
│   ├── __init__.py
│   └── hello_world.py       # standalone library node (LangChain Runnable)
└── cli.py                   # thin CLI composing the library

tests/
├── unit/
│   └── test_hello_world.py  # deterministic node behavior (network-free)
└── integration/
    └── test_hello_world_cli.py  # end-to-end CLI run + exit codes
```

**Structure Decision**: Single Python src-layout project (`agentcrew`).
The node lives as a **standalone library** under `src/agentcrew/nodes/`
(Library-First), and the CLI lives separately so it *composes* the library.

## Complexity Tracking

No constitution violations — table intentionally omitted.