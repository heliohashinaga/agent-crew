# Contract: Per-capability-level model map

**Purpose**: Resolve a nominal capability label to a **real model id** so the
`dev_workflow` live executor can dispatch each role with the right model.

**Function**: `resolve_model_id(level: str) -> str` (in
`ai_factory.capability_levels.model_map`).

## Mapping rules (FR-010)

| Nominal level | Real model id via |
|---------------|-------------------|
| `fast-cheap`   | `AI_FACTORY_MODEL_FAST_CHEAP` (default: flash-class opencode-go id) |
| `capable`      | `AI_FACTORY_MODEL_CAPABLE` (default: pro-class opencode-go id) |
| `deep`         | `AI_FACTORY_MODEL_DEEP` (default: best-class opencode-go id) |
| unknown/fallback | `AI_FACTORY_MODEL_DEFAULT` (documented default id) |

## Behavior

- Precedence: **env override** > **code default**.
- Unknown level → fallback to `AI_FACTORY_MODEL_DEFAULT` (never an empty/garbage
  model id; fail-closed in live mode).
- Defaults target opencode-go OpenAI-compatible ids when
  `OPENAI_COMPATIBLE_BASE_URL` points at opencode-go; switching to openrouter is
  done by swapping base_url / env overrides.
