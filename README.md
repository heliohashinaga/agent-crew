# agent-crew

> A swarm of AI agents collaborating across the software development lifecycle.

[![CI](https://github.com/heliohashinaga/agent-crew/actions/workflows/ci.yml/badge.svg)](https://github.com/heliohashinaga/agent-crew/actions/workflows/ci.yml)

This repository focuses on **agent-to-agent interaction in the software
development cycle**: specialized AI agents that hand work between one another —
planning, building, testing, reviewing and securing a change — instead of a
single model doing a single pass.

> **Status: drafting.** The previous `src/ai_factory` implementation was removed
> and the foundation is being rebuilt from scratch around the swarm/interaction
> vision above. A LangChain hello-world node (`agentcrew`) establishes the base.

## Getting started

```bash
# Install the project and dev tooling (uv-based).
uv sync

# Run the hello-world node via the console script.
uv run agentcrew-hello "world"

# Or in Python.
uv run python -m agentcrew.cli hello "world"

# Lint + tests.
uv run ruff check .
uv run pytest
```

See [`specs/001-langchain-hello-node/`](specs/001-langchain-hello-node/) for the
current design (spec, plan, tasks).

## License

MIT — see [`LICENSE`](LICENSE).