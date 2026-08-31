# agent-crew

> A swarm of AI agents collaborating across the software development lifecycle.

[![CI](https://github.com/heliohashinaga/agent-crew/actions/workflows/ci.yml/badge.svg)](https://github.com/heliohashinaga/agent-crew/actions/workflows/ci.yml)

This repository focuses on **agent-to-agent interaction in the software
development cycle**: specialized AI agents that hand work between one another —
planning, building, testing, reviewing and securing a change — instead of a
single model doing a single pass.

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

## Coder → Cleaner pipeline

The first multi-node agent handoff: a **coder** agent writes code from a task
and a **cleaner** agent applies semantic clean code (descriptive naming, small
functions, removing redundant comments). It is **language-agnostic** (any
language the task requests). Requires an LLM provider key in your local `.env`
(see `.env.example`).

```bash
uv run agentcrew-code "write a python function that returns the nth fibonacci number"
uv run agentcrew-code --provider opencode "export a React form component that validates email"
uv run agentcrew-code "..." --format json
```

Formatting stays with Black/ruff (the cleaner is **not** responsible for
formatting) — see [`specs/002-coder-cleaner/`](specs/002-coder-cleaner/spec.md).

## Observability

Offline per-run metrics (latency, counts, inputs/outputs) come from
[`MetricsCallbackHandler`](src/agentcrew/telemetry.py) — credential-free, no
network:

```python
from agentcrew.nodes.hello_world import build_hello_world_node
from agentcrew.telemetry import MetricsCallbackHandler

handler = MetricsCallbackHandler()
build_hello_world_node().invoke("world", config={"callbacks": [handler]})
print(handler.avg_latency_ms())
```

For hosted traces, token/cost dashboards, and model insights, LangSmith is an
**opt-in** integration (requires network + API key; see
[docs/langsmith.md](docs/langsmith.md)). It stays disabled by default so the
base remains offline and credential-free.

## License

MIT — see [`LICENSE`](LICENSE).