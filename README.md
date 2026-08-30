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

## Quality gates

### Cyclomatic complexity
Enforced in CI: a `quality` gate (`tests/quality/test_complexity.py`) fails if
any function in `src/agentcrew/` exceeds a cyclomatic complexity budget of 10.
Runs automatically with `uv run pytest`.

### Mutation testing (local / opt-in)
Mutation testing is expensive, so it runs on demand — it is **not** part of the
deterministic CI `test` job. It is scoped to the pure library logic (`nodes/`).

```sh
uv run mutmut run        # mutate nodes/ and try to kill each mutant with the unit tests
uv run mutmut results    # show any surviving mutants (target: high kill rate)
```

Current baseline: 7/7 mutants killed (100%).

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