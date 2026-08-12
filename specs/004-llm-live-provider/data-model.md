# Data Model: Live LLM Provider & Dual-Mode Dev-Workflow

**Feature**: `004-llm-live-provider` | **Date**: 2026-08-12

This feature builds on the existing `LLMProvider`/`LLMResult`/`LLMMessage`
contract from `ai_factory.shared.llm.provider` (used by the `researcher` web
scope). It adds a concrete provider and a per-capability-level model map. No
changes to the `dev_workflow` data model (`RoleAssignment`) are required — it
already carries `model` and `capability_level`.

## Entities

### `LLMResult` (extant, consumed)

| Field | Type | Notes |
|-------|------|-------|
| `content` | `str` | assistant message text (may be empty for tool/non-string responses) |
| `model` | `str` | model id echoed by the provider (falls back to configured model) |
| `tokens_in` | `int` | `usage.prompt_tokens` (0 if absent) |
| `tokens_out` | `int` | `usage.completion_tokens` (0 if absent) |
| `raw` | `dict` | full provider payload |

### `LLMMessage` (extant)

| Field | Type | Notes |
|-------|------|-------|
| `role` | `str` | `"user"` / `"assistant"` / `"system"` |
| `content` | `str` | message text |

### `OpenAICompatibleProvider` (new)

A concrete `LLMProvider` speaking `POST /v1/chat/completions` (stdlib `urllib` only).

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `model_name` | `str` | constant | `"openai-compatible"` (registry key) |
| `provider` | `str` | model-id prefix | `opencode-go` \| `openrouter` (from the resolved model id) |
| `api_key` | `str` | env/inject | `OPENCODE_GO_API_KEY` / `OPENROUTER_API_KEY` (never committed) |
| `base_url` | `str` | env/inject | `OPENCODE_GO_BASE_URL` / `OPENROUTER_BASE_URL` → per-provider default |
| `model` | `str` | env/inject/json | `MODEL_DEFAULT` or per-level id (provider-prefixed) |
| `endpoint` | `str` | derived | `<base_url>/chat/completions` |

**Relationship**: `1` provider → `n` call sites (`researcher` web scope, `dev_workflow` role executor).

### `PerCapabilityModelMap` (new)

Maps nominal capability labels to real model ids, provider-prefixed, via code
defaults `< optional`model-map.json`` `< env. Both providers can be used
simultaneously.

| Level (nominal) | Env override | Default behavior |
|-----------------|--------------|------------------|
| `fast-cheap` | `MODEL_FAST_CHEAP` | flash-class model id (provider-prefixed) |
| `capable` | `MODEL_CAPABLE` | pro-class model id |
| `deep` | `MODEL_DEEP` | best-class model id |
| *(unknown/fallback)* | `MODEL_DEFAULT` | documented default id |

**Relationship**: `1` map → `1` real model id per capability level; consumed by the dual-mode executor.

## Relationships

```text
OpenAICompatibleProvider ──<injects>── researcher.web (call site #1)
OpenAICompatibleProvider ──<dispatches>── dev_workflow role executor   (call site #2)
PerCapabilityModelMap ──<resolves model id>── RoleAssignment.capability_level (live mode)
LLMResult ──<returned by>── OpenAICompatibleProvider.complete(...)
```

## Validation Rules (from FRs)

- **FR-001 / FR-005**: `OpenAICompatibleProvider` construction performs **no
  network I/O**; one HTTP call only inside `complete()`. `FakeProvider`
  remains the default.
- **FR-002**: credentials only via env (`OPENCODE_GO_API_KEY`/`OPENROUTER_API_KEY`)
  /`SecretSource`; never committed. Missing key → fail fast with
  `OpenAICompatibleError` (or `FakeProvider` fallback where tolerated).
- **FR-003**: `complete()` parses `choices[0].message.content`, `usage`,
  `model` into `LLMResult`; conforms to the `LLMProvider` contract.
- **FR-006**: non-2xx / non-JSON → `OpenAICompatibleError` with the API key
  **redacted** (`redact_secret_like`, FR-018).
- **FR-009 / FR-010**: live only when `AI_FACTORY_LIVE=1`/`--live` **AND** a
  resolvable API key; model id resolved from `capability_level` via the
  per-capability model map; missing level → fail-closed (deterministic path or
  clear error), never an empty/garbage model id.

## State Transitions

`OpenAICompatibleProvider` is **stateless** for call purposes: construction is
network-free; each `complete()` is an independent HTTP POST. Error states:

```text
constructed (no network)
   └─> complete() ──> HTTP 2xx ──> parse ──> LLMResult
        │
        └─> HTTP non-2xx / URLError / non-JSON ──> OpenAICompatibleError (key redacted)
```

Dual-mode run state (per run):

```text
live = (opts in via AI_FACTORY_LIVE|--live) AND (a provider api_key resolvable)
   ├─ false ──> offline path (deterministic, no network)
   └─ true  ──> resolve provider-prefixed model id per level -> pick key/base_url
                 by provider prefix -> dispatch via provider
```
