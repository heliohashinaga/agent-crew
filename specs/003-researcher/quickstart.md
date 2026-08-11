# Quickstart — Researcher (003-researcher)

A runnable validation guide for the `researcher` role. This proves the feature
works end-to-end (repo lookup; web scope; mono-capacity role). For contract
details, see [contracts/](./contracts/researcher-cli.md) and the
[data model](./data-model.md).

## Prerequisites

- Python ≥ 3.14, package installed via `uv sync` (brings `ai-factory` + the
  `ai-factory-researcher` console script).
- **No network required** for `repo` scope. `web` scope needs network + an
  `LLMProvider` (see Setup); its tests run under `-m integration`.

## Setup

```bash
uv sync
uv run pytest -q          # unit + contract (network-free)
```

## Scenario 1 — Query the repository (repo scope)

**Goal**: a role gets a concise summary + source pointers for a query, without
dumping whole files into its context.

```bash
uv run ai-factory-researcher --scope repo \
  --query "login authentication password" \
  --roots ./src ./tests --output-format json
```

**Expected outcome**:
- Exit code `0`; stdout is a JSON `ResearchResult` with `role == "researcher"`,
  `scopes_used == ["repo"]`, a concise `summary`, and `sources` pointing to the
  relevant files (e.g. `service.py`, line `14-40`).
- `sources` are exact path + line-range pointers; the `summary` does **not**
  contain a verbatim full-file dump (FR-002).
- Diagnostics/notes go to **stderr**, never stdout.
- Validate the payload: `uv run python -c "from ai_factory.researcher.models import ResearchResult; import json,sys; print(ResearchResult.model_validate_json(sys.stdin.read()).role)"`.

## Scenario 2 — Empty / missing inputs boundary

```bash
uv run ai-factory-researcher --scope repo --roots ./src        # missing --query  → usage error, exit 1
uv run ai-factory-researcher --scope repo --query "zzz-nomatch" --roots ./src  # → summary "" + sources [] (exit 0)
```

**Expected outcome**:
- Missing `--query` argument → exit `1`, clear usage error on stderr.
- Query with no matches → `ResearchResult` with empty `summary` and `sources`
  (FR-004), exit `0`. Missing/invalid `--roots` for `repo` → exit `1`.

## Scenario 3 — Web scope (v1, Option D) *(needs network + LLM)*

**Goal**: a role queries the web and receives a synthesized `summary` with URL
sources (multi-angle best-per-angle).

```bash
uv run pytest -m integration -q tests/integration/  # real network/LLM path
# or, in a configured env:
uv run ai-factory-researcher --scope web --query "python async best practices" --output-format json
```

**Expected outcome**:
- `ResearchResult` with `scopes_used == ["web"]`, `summary` a concise synthesis,
  `sources` as URLs varied across angles (best-per-angle), capped to the
  context-window limit.
- On network/LLM failure → exit `4` with a clear error on stderr, never a
  silent empty result (FR-010).

## Scenario 4 — Deterministic unit/contract offline

```bash
uv run pytest tests/unit/researcher tests/contract/researcher -q
```

**Expected outcome**: All researcher unit + contract tests pass **without
network** using `FakeProvider`/fakes (SC-002); web logic covered deterministically.
