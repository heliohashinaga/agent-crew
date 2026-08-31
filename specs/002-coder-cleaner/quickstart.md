# Quickstart: Coder → Cleaner Agent Pipeline

**Spec**: [spec.md](./spec.md) | **Contract**: [contracts/coder-cleaner-pipeline.md](./contracts/coder-cleaner-pipeline.md)

## Install & verify

```bash
uv sync                 # installs deps incl. langgraph (T001)
uv run ruff check .     # lint clean
uv run pytest           # unit + contract (offline)
```

## Offline (testable) path — no key needed

The graph plumbing and the coder→cleaner handoff are exercised without
network/credentials using **mocked node outputs**:

```bash
uv run pytest -m contract tests/contract/test_coder_cleaner_graph.py
uv run ruff check .   # formatting stays the job of ruff/Black (FR-005)
```

## Opt-in LLM path (real agents)

Set a provider key in `.env` (see root `.env.example`):

```dotenv
OPENROUTER_API_KEY=sk-or-v1-xxxx     # or OPENCODE_GO_API_KEY=xxxx
LANGSMITH_TRACING=true                # optional: observe the run
```

Run the pipeline:

```bash
uv run agentcrew-code "write a python function that returns the nth fibonacci number"
# text (default): prints the cleaned code

uv run agentcrew-code "..." --format json
# JSON: {"task": "...", "coder_output": "...", "cleaner_output": "...", "model": "..."}

uv run agentcrew-code "..." --provider opencode
```

## Observability

With `LANGSMITH_TRACING=true`, each real run appears in the LangSmith project
with the graph and its `coder`/`cleaner` nodes visible (SC-004).

## Exit codes

`0` success · `1` usage error · `4` runtime failure (missing key, LLM failure).

## Command reference (summary)

| Task | Command |
|------|---------|
| Run offline handoff contract tests | `uv run pytest -m contract tests/contract/test_coder_cleaner_graph.py` |
| Format (deterministic, out of the cleaner) | `uv run ruff format .` |
| Run the pipeline (OpenRouter) | `uv run agentcrew-code "<task>"` |
| Run the pipeline (OpenCode Go) | `uv run agentcrew-code --provider opencode "<task>"` |
| JSON output | append `--format json` |