# Contract: Per-role capability-level model map

**Purpose**: Resolve a **role + capability level** to a **real, provider-prefixed
model id** so the `dev_workflow` live executor can dispatch each role with the
right model on the right provider.

**Function**: `resolve_model_id(role: str, level: str) -> str` (in
`ai_factory.capability_levels.model_map`).

## Two level axes (from `capability_levels`)

| Role category | Roles | Level axis |
|---------------|-------|------------|
| Task | `code_worker`, `test_engineer` | `simple` → `standard` → `complex` |
| Review | `code_reviewer`, `security_reviewer` | `shallow` → `standard` → `deep` |
| Fixed | `technical_planner`, `orchestrator`, `test_runner` | `standard` (pinned) |

Both axes are handled by the same nested JSON: each role lists the levels it
uses, and each level maps to a model id.

## Configuration surface

**API keys in env only (FR-018), never in the JSON:**

| Env var | Purpose |
|---------|---------|
| `OPENCODE_GO_API_KEY` | opencode-go API key (never committed) |
| `OPENROUTER_API_KEY` | openrouter API key (never committed) |
| `OPENCODE_GO_BASE_URL` / `OPENROUTER_BASE_URL` | per-provider base URL (optional; known default) |
| `MODEL_FAST_CHEAP` / `MODEL_CAPABLE` / `MODEL_DEEP` / `MODEL_DEFAULT` | per-*level* env override (flattens the role axis) |
| `AI_FACTORY_LIVE` | dual-mode opt-in gate (`1` = live) |

**Optional `model-map.json`** (commit-safe, no secrets): nested role → level →
model id.

## `model-map.json` shape

```json
{
  "roles": {
    "code_worker": {
      "simple":   "opencode-go/deepseek-v4-flash",
      "standard": "openrouter/qwen/qwen3.8-max",
      "complex":  "opencode-go/kimi-k3"
    },
    "test_engineer": {
      "simple":   "opencode-go/deepseek-v4-flash",
      "standard": "openrouter/qwen/qwen3.8-max",
      "complex":  "opencode-go/kimi-k3"
    },
    "code_reviewer": {
      "standard": "openrouter/qwen/qwen3.8-max",
      "deep":     "opencode-go/kimi-k3"
    },
    "orchestrator": {
      "standard": "opencode-go/deepseek-v4-flash"
    }
  },
  "default": "opencode-go/deepseek-v4-flash"
}
```

Both providers (`opencode-go`/`openrouter`) are usable **simultaneously** — each
cell is a provider-prefixed model id.

## Resolution rules (FR-010)

- `resolve_model_id(role, level)`:
  1. **env override** (flattened by level): `MODEL_FAST_CHEAP`/`MODEL_CAPABLE`/`MODEL_DEEP`
     win for the matching level label, regardless of role (documented).
  2. else **`model-map.json`**: `roles[role][level]` (precise per-role config).
   ...
- **env overrides are flattened by LEVEL** (`MODEL_FAST_CHEAP`/`MODEL_CAPABLE`/
  `MODEL_DEEP`): they apply to any role at that level label and do **not**
  distinguish role or axis (e.g. `MODEL_DEEP` affects both `code_reviewer` deep
  and any `deep`-mapped task). For role-precise selection use `model-map.json`.
  Per-role env overrides (`MODEL_<ROLE>_<LEVEL>`) are out of scope for v1.
  3. else **code defaults** (most specific available).
  4. missing role/level/model → fall back to `MODEL_DEFAULT`/`default`.
- Precedence overall: **code defaults < `model-map.json` < env**.
- Unknown role/level or empty/garbage id → **fail-closed** in live mode (use the
  deterministic path or raise a clear error), never dispatch with a bad id.
- **Concrete default ids**: the defaults are provider-dependent — T010 pins the
  concrete provider-prefixed ids (e.g. an opencode-go flash/pro/deep class for
  each axis) used by tests and by `MODEL_*` fallback. Documented as the
  authoritative defaults; operators override per deploy via JSON/env.

The dispatcher parses the model-id prefix (`opencode-go`/`openrouter`), selects
the matching key (`OPENCODE_GO_API_KEY`/`OPENROUTER_API_KEY`) and base URL, then
calls the OpenAI-compatible `/v1/chat/completions` endpoint.
