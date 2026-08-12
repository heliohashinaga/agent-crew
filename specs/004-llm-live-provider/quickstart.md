# Quickstart — Live LLM Provider & Dual-Mode Dev-Workflow (004)

This feature adds a portable, OpenAI-compatible live LLM provider and gives the
`dev_workflow` a **dual-mode**: deterministic/offline by default, opt-in live
with a real model per capability level. This guide shows how to validate both
modes without spending (offline) and, optionally, with a real model.

## Prerequisites

- Python ≥ 3.14, `uv` (project `ai-factory`)
- No network required for the offline path.
- Optional, for live mode: an OpenAI-compatible endpoint — either your
  `opencode-go` or `openrouter` credentials.

## Setup

```bash
uv sync --group dev
uv run ruff check .        # enforce harden
```

## Scenario 1 — Offline (default): roles stay deterministic & network-free

Prove the default never touches HTTP.

```bash
# Block network by running the unit+contract suite; live HTTP must not fire.
uv run pytest -m "not integration" -q
```

**Expected**: all unit + contract tests pass with no network; the live provider
is exercised only with a **stubbed transport** (`urlopen` frozen); no real HTTP.
See [data-model.md](./data-model.md) and [contracts/](./contracts/).

**Also assert explicitly** (SC-006): with the network blocked and live not
opted-in, `dev_workflow` roles produce identical deterministic output; even if
`OPENAI_COMPATIBLE_*` creds are set, **no** HTTP call happens.

## Scenario 2 — Empty / missing credentials boundary

Run a lookup/role path with **no** `OPENAI_COMPATIBLE_API_KEY`.

**Expected**: falls back to `FakeProvider` (no network, no cost) — never a
silent hang or secret leak. `FakeProvider` remains the default (SC-002). A
typed `OpenAICompatibleError` is raised only when live mode is **explicitly**
requested.

## Scenario 3 — Live mode (opt-in) *(needs credentials; `-m integration`)*

When you have credentials, validate the real provider end-to-end.

```bash
# Point at a provider (opencode-go or openrouter)
export OPENAI_COMPATIBLE_BASE_URL="https://.../v1"
export OPENAI_COMPATIBLE_API_KEY="..."
export OPENAI_COMPATIBLE_MODEL="..."       # optional default model

# Opt in to live and run the gated real-network/LLM tests
export AI_FACTORY_LIVE=1
uv run pytest -m integration -q
```

**Expected**: `-m integration` (best-effort) hits the real endpoint when creds
are present; skipped gracefully when unavailable. Live-mode roles resolve a
real model id per capability level via the model map
(`AI_FACTORY_MODEL_*`) — see [contracts/model-map.md](./contracts/model-map.md).

> Switch providers without code edits: change `OPENAI_COMPATIBLE_BASE_URL` /
> `_MODEL` and any `AI_FACTORY_MODEL_*` overrides.

## Scenario 4 — Per-capability-level model resolution

```bash
export AI_FACTORY_LIVE=1
export AI_FACTORY_MODEL_FAST_CHEAP="opencode-go/deepseek-v4-flash"
export AI_FACTORY_MODEL_CAPABLE="opencode-go/deepseek-v4-pro"
export AI_FACTORY_MODEL_DEEP="opencode-go/kimi-k3"
```

**Expected**: a `fast-cheap` role uses the flash id, `capable` the pro id, `deep`
the best id; unknown level falls back to `AI_FACTORY_MODEL_DEFAULT`. Verified by
unit test (`test_model_map.py`) with a stubbed transport (offline).

## Cross-references

- **Data model**: [data-model.md](./data-model.md) → `OpenAICompatibleProvider`,
  `PerCapabilityModelMap`, `LLMResult`.
- **Contracts**: [provider](./contracts/openai-compatible-provider.md) and
  [model map](./contracts/model-map.md).
- **Implementation**: [tasks.md](./tasks.md) — T002..T024 (unit), T040 (integration).
