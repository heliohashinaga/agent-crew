# Contract: `openai-compatible` provider (Live LLM)

**Role**: An `LLMProvider` implementation speaking the OpenAI-compatible
`/v1/chat/completions` HTTP contract (shared by `opencode-go` and `openrouter`).

**Configuration surface (env vars + optional JSON)** — this is how an operator
configures "which model the agents use", portable to a VPS. **API keys live in
env vars only (FR-018), never in the JSON.** The two supported providers are
`opencode-go` and `openrouter`.

| Env var | Purpose | Default |
|---------|---------|---------|
| `OPENCODE_GO_API_KEY` | opencode-go API key (Bearer) | none (fail-fast or `FakeProvider`) |
| `OPENROUTER_API_KEY` | openrouter API key | none (fail-fast or `FakeProvider`) |
| `OPENCODE_GO_BASE_URL` | opencode-go base URL | opencode-go default |
| `OPENROUTER_BASE_URL` | openrouter base URL | openrouter default |
| `MODEL_DEFAULT` | default model id (provider-prefixed) | code default |
| `AI_FACTORY_LIVE` | dual-mode opt-in gate (`1` = live) | unset → offline |

Both providers are available **simultaneously**: the per-role capability-level model
ids (fully-qualified, provider-prefixed) each choose which provider to use, and
the dispatcher selects the matching `OPENCODE_GO_API_KEY`/`OPENROUTER_API_KEY`
and base URL by parsing the model id prefix.

Per-capability-level model ids resolve through **`model-map.json`** (optional,
commit-safe, no secrets) merged with code defaults and final per-level env
override `MODEL_FAST_CHEAP` / `MODEL_CAPABLE` / `MODEL_DEEP`. Precedence: code
defaults < JSON < env.

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
