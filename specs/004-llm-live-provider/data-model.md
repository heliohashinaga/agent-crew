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
| `base_url` | `str` | env/inject | `OPENAI_COMPATIBLE_BASE_URL` → default OpenRouter-compatible |
| `api_key` | `str` | env/inject | `OPENAI_COMPATIBLE_API_KEY` (never committed) |
| `model` | `str` | env/inject | `OPENAI_COMPATIBLE_MODEL` → default `openrouter/auto` |
| `endpoint` | `str` | derived | `<base_url>/chat/completions` |

**Relationship**: `1` provider → `n` call sites (`researcher` web scope, `dev_workflow` role executor).

### `PerCapabilityModelMap` (new)

Maps nominal capability labels to real model ids, env-overridable.

| Level (nominal) | Env override | Default behavior |
|-----------------|--------------|------------------|
| `fast-cheap` | `AI_FACTORY_MODEL_FAST_CHEAP` | flash-class opencode-go id |
| `capable` | `AI_FACTORY_MODEL_CAPABLE` | pro-class opencode-go id |
| `deep` | `AI_FACTORY_MODEL_DEEP` | best-class opencode-go id |
| *(unknown/fallback)* | `AI_FACTORY_MODEL_DEFAULT` | documented default id |

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
- **FR-002**: credentials only via env/`SecretSource`; never committed. Missing
  API key → fail fast with `OpenAICompatibleError` (or `FakeProvider` fallback
  where the caller tolerates it).
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
live = (opts in via AI_FACTORY_LIVE|--live) AND (api_key resolvable)
   ├─ false ──> offline path (deterministic, no network)
   └─ true  ──> resolve model id per RoleAssignment.capability_level -> dispatch via provider
```
