# Quickstart: LangChain Foundation — Hello-World Node

Validation guide proving the base works end-to-end. Implementation details live
in `tasks.md`.

## Prerequisites

- `uv` installed.
- No API keys, credentials, or network required — the node is offline and
  deterministic.

## Setup

```sh
uv sync
```

## Run the hello-world node

```sh
uv run python -m agentcrew.cli hello "world"
# expect: Hello, world!
```

Equivalent console script (post-install):

```sh
uv run agentcrew-hello "world"
# expect: Hello, world!
```

JSON output:

```sh
uv run python -m agentcrew.cli hello "world" --format json
# expect: {"input": "world", "greeting": "Hello, world!"}
```

## Verify (tests)

```sh
uv run ruff check .          # lint
uv run pytest                # unit + integration (network-free)
```

Expected: all tests pass, `ruff` reports no issues.

## Acceptance mapping

| Scenario (spec) | How to verify |
|-----------------|---------------|
| US1-A1 fresh checkout installs | `uv sync` succeeds |
| US1-A2 run node returns greeting | `uv run python -m agentcrew.cli hello "world"` → `Hello, world!` |
| US1-A3 tests pass, no network | `uv run pytest` passes offline |
| US1-A4 extensible source layout | `src/agentcrew/nodes/` holds the node library |

Contracts: [hello-world-node-cli.md](./contracts/hello-world-node-cli.md).
Data model: [data-model.md](./data-model.md).