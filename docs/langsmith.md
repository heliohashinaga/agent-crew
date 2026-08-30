# LangSmith: observability for agent-crew

[LangSmith](https://smith.langchain.com) is LangChain's hosted tracing and
observability platform: traces, latency, token usage, cost, and model/hyperparam
insights in a dashboard.

**This is OPT-IN.** Enabling it requires an outbound network connection and a
LangSmith API key, which **violates the project's offline / zero-credential
default** (see the constitution: the base must run with no keys, no network,
no secrets). Use it only when you explicitly want observability for debugging,
benchmarking, or production monitoring — and never commit the key.

> For credential-free, offline metrics (latency, counts, inputs/outputs per
> run), prefer the built-in [`MetricsCallbackHandler`](../src/agentcrew/telemetry.py)
> — no LangSmith needed.

## 1. Prerequisites

- A LangSmith account and a project (free tier is enough to try).
- An **API key** (Settings → API keys in LangSmith).
- Network access to the LangSmith ingest endpoints.

## 2. Configure environment

Copy the example env file and fill in your key. Real keys live in `.env`
(gitignored) — never in the repository.

```bash
cp .env.example .env
# edit .env: set LANGSMITH_API_KEY=<your key>
```

If you are not using a `.env` loader, export the variables directly:

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=lsv2_xxxxxxxxxxxxx
export LANGSMITH_PROJECT=agent-crew
```

The three variables:

| Variable | Purpose |
|----------|---------|
| `LANGSMITH_TRACING` | `true` to enable tracing |
| `LANGSMITH_API_KEY` | Your secret API key |
| `LANGSMITH_PROJECT` | Optional project label (defaults to the project name) |

## 3. Run with tracing

LangChain auto-instruments when the env vars are set — **no code changes needed**.

```bash
uv run python -m agentcrew.cli hello "world"
```

Each run is captured as a trace. Open **smith.langchain.com → your project** to
see spans, latency, inputs/outputs, and (for real model-backed nodes) token
usage and cost.

## 4. Integrate with the metrics callback handler

The offline handler works alongside tracing and is independent of it:

```python
from agentcrew.nodes.hello_world import build_hello_world_node
from agentcrew.telemetry import MetricsCallbackHandler

handler = MetricsCallbackHandler()
node = build_hello_world_node()
node.invoke("world", config={"callbacks": [handler]})
print(handler.avg_latency_ms())   # average latency (ms), entirely offline
```

When LangSmith tracing is enabled via env, the same run is also sent to the
dashboard.

## 5. Security & default behavior

- **Never commit `LANGSMITH_API_KEY`.** It must only live in local `.env`
  (gitignored). `.env.example` is tracked and contains placeholder only.
- Keep LangSmith **disabled by default** so the base stays offline and
  credential-free (constitution). Enable it only in contexts you explicitly
  choose (debugging, a production deploy with real credentials).
- CI stays hermetic and never has the key, so the deterministic pipeline never
  reaches the network.