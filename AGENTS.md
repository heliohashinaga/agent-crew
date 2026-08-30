# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project

The focus of this project is **agent-to-agent interaction across the software
development lifecycle**: a swarm of specialized AI role-agents (planner,
builder, tester, reviewer, security) that collaborate — handing work between
one another — to turn a natural-language feature request into a reviewed,
merge-ready pull request.

> **Fresh start.** The previous `src/ai_factory` implementation and `specs/`
> design artifacts were removed. The foundation is being rebuilt around the
> swarm/interaction vision. This file will grow as the project's conventions
> are re-established.

## Conventions

- Managed with `uv`; Python ≥ 3.14.
- Lint: `uv run ruff check .`
- Test: `uv run pytest`