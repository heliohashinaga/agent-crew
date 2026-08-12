# Contract: `openai-compatible` provider (Live LLM)

**Role**: An `LLMProvider` implementation speaking the OpenAI-compatible
`/v1/chat/completions` HTTP contract (shared by `opencode-go` and `openrouter`).

**Configuration surface (env vars)** — this is how an operator configures
"which model the agents use", portable to a VPS:

| Env var | Purpose | Default |
|---------|---------|---------|
| `OPENAI_COMPATIBLE_API_KEY` | Bearer token / API key | none (fail-fast or `FakeProvider`) |
| `OPENAI_COMPATIBLE_BASE_URL` | Server base URL | OpenRouter-compatible default |
| `OPENAI_COMPATIBLE_MODEL` | Default model id | `openrouter/auto` |
| `AI_FACTORY_LIVE` | Dual-mode opt-in gate (`1` = live) | unset → offline |
| `AI_FACTORY_MODEL_FAST_CHEAP` / `_CAPABLE` / `_DEEP` / `_DEFAULT` | Per-capability-level real model ids | opencode-go defaults |

## Interface — `complete(messages, **kwargs) -> LLMResult`

Implements the `LLMProvider` ABC (FR-003):

- `messages: list[LLMMessage]` — required; each has `role` + `content`.
- `kwargs` (per-call overrides, FR-004):
  - `model` — override the provider default model id
  - `temperature` — override temperature
  - `max_tokens` / `max_completion_tokens` — cap output tokens

**Return `LLMResult`**: `content`, `model`, `tokens_in`, `tokens_out`, `raw`.

**HTTP request**: `POST <base_url>/chat/completions`, JSON body
`{model, messages, [temperature], [max_tokens]}`, `Authorization: Bearer <key>`.

## Failure contract (FR-006)

- Non-2xx status or non-JSON body → raise **`OpenAICompatibleError`**.
- The message **redacts the API key** (reuse `redact_secret_like`/`REDACTED`).
- Construction is network-free (FR-005); HTTP only on `complete()`.

## Invocation (existing CLIs)

No new CLI. Dual-mode opt-in is via existing role CLIs:
`AI_FACTORY_LIVE=1` (env) or `--live` (flag). JSON + human + exit codes of each
role are preserved unchanged.
