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