# Contract: Per-capability-level model map

**Purpose**: Resolve a nominal capability label to a **real model id** (with an
embedded provider prefix) so the `dev_workflow` live executor can dispatch each
role with the right model on the right provider.

**Function**: `resolve_model_id(level: str) -> str` (in
`ai_factory.capability_levels.model_map`).

## Mapping rules (FR-010)

Each nominal level maps to a **fully-qualified model id** whose prefix selects
the provider. The two supported providers — `opencode-go` and `openrouter` —
can be used **simultaneously**: each level picks whichever provider it wants.

| Nominal level | Source | Example (opencode-go) | Example (openrouter) |
|---------------|--------|----------------------|----------------------|
| `fast-cheap`   | `MODEL_FAST_CHEAP` (JSON/code) | `opencode-go/deepseek-v4-flash` | `openrouter/deepseek/deepseek-v4-flash-0731` |
| `capable`      | `MODEL_CAPABLE` | `opencode-go/deepseek-v4-pro` | `openrouter/qwen/qwen3.8-max` |
| `deep`         | `MODEL_DEEP` | `opencode-go/kimi-k3` | `openrouter/moonshotai/kimi-k2.5` |
| unknown/fallback | `MODEL_DEFAULT` | `opencode-go/deepseek-v4-flash` | `openrouter/deepseek/deepseek-v4-flash-0731` |

## Configuration surface

Two providers, both configured simultaneously:

| Env var | Purpose |
|---------|---------|
| `OPENCODE_GO_API_KEY` | opencode-go API key (never committed) |
| `OPENROUTER_API_KEY` | openrouter API key (never committed) |
| `OPENCODE_GO_BASE_URL` | opencode-go base URL (optional; known default) |
| `OPENROUTER_BASE_URL` | openrouter base URL (optional; known default) |
| `MODEL_FAST_CHEAP` / `MODEL_CAPABLE` / `MODEL_DEEP` / `MODEL_DEFAULT` | model id overrides (fully-qualified, provider-prefixed) |
| `AI_FACTORY_LIVE` | dual-mode opt-in gate (`1` = live) |

**Optional `model-map.json`** (commit-safe, no secrets): a JSON mapping
`{ "models": { "fast-cheap": "...", "capable": "...", "deep": "...", "default": "..." } }`
merged over code defaults and overridden by env vars.

**Precedence**: code defaults `< model-map.json` `< env vars`.

## Behavior

- Each level resolves to a fully-qualified model id (provider-prefixed); the
  same run can mix providers across levels (simultaneous use).
- Unknown level → fallback to `MODEL_DEFAULT` (never an empty/garbage model id;
  fail-closed in live mode).
- The dispatcher parses the provider prefix (`opencode-go`/`openrouter`),
  selects the matching key (`OPENCODE_GO_API_KEY`/`OPENROUTER_API_KEY`) and
  base URL, then calls the OpenAI-compatible `/v1/chat/completions` endpoint.
