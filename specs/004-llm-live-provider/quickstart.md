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
`OPENCODE_GO_API_KEY`/`OPENROUTER_API_KEY` creds are set, **no** HTTP call
happens.
## Scenario 2 — Empty / missing credentials boundary

Run a lookup/role path with **no** `OPENCODE_GO_API_KEY`/`OPENROUTER_API_KEY`.

**Expected**: falls back to `FakeProvider` (no network, no cost) — never a
silent hang or secret leak. `FakeProvider` remains the default (SC-002). A
typed `OpenAICompatibleError` is raised only when live mode is **explicitly**
requested.

## Scenario 3 — Live mode (opt-in) *(needs credentials; `-m integration`)*

When you have credentials, validate the real provider end-to-end. Both
providers (`opencode-go` and `openrouter`) can be used **simultaneously** —
each capability level picks its own provider via the model-id prefix.

```bash
# API keys always in env (never in git / model-map.json)
export OPENCODE_GO_API_KEY="sk-opencode-..."
export OPENROUTER_API_KEY="sk-or-..."

# Optional: a commit-safe model-map.json (no secrets) or per-level env overrides
export MODEL_FAST_CHEAP="opencode-go/deepseek-v4-flash"
export MODEL_CAPABLE="openrouter/qwen/qwen3.8-max"       # already mixing providers
export MODEL_DEEP="opencode-go/kimi-k3"
export MODEL_DEFAULT="opencode-go/deepseek-v4-flash"

# Opt in to live and run the gated real-network/LLM tests
export AI_FACTORY_LIVE=1
uv run pytest -m integration -q
```

**Expected**: `-m integration` (best-effort) hits the real endpoints when creds
are present; skipped gracefully when unavailable. Live-mode roles resolve a
real, provider-prefixed model id per capability level via the model map
(`MODEL_*` env or `model-map.json`) — see
[contracts/model-map.md](./contracts/model-map.md).

## Scenario 4 — Per-capability-level model resolution

```bash
export AI_FACTORY_LIVE=1
# ENV override (code < model-map.json < env)
export MODEL_FAST_CHEAP="opencode-go/deepseek-v4-flash"
export MODEL_CAPABLE="openrouter/qwen/qwen3.8-max"
export MODEL_DEEP="opencode-go/kimi-k3"
# or instead: commit a model-map.json with the same mapping (no secrets)
```

**Expected**: a `code_worker`→`simple` role uses the config'd fast id (opencode-go), `capable`
the config'd id (openrouter — mixing providers), `deep` its own; unknown level falls
back to `MODEL_DEFAULT`. Precedence code `< JSON < env. Verified by unit test
(`test_model_map.py`) with a stubbed transport (offline).

## Cross-references

- **Data model**: [data-model.md](./data-model.md) → `OpenAICompatibleProvider`,
  `PerRoleCapabilityModelMap`, `LLMResult`.
- **Contracts**: [provider](./contracts/openai-compatible-provider.md) and
  [model map](./contracts/model-map.md).
- **Implementation**: [tasks.md](./tasks.md) — T002..T024 (unit), T040 (integration).
