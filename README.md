# AI Dev Factory

Turns a natural-language feature request into a **reviewed, merge-ready pull
request** through two independent, traceable workflows (FR-024).

## The folder-driven dev workflow

```
                  ┌──────────────────── dev workflow ───────────────┐
 speckit spec     │  folder-adapter → planner → orchestrator →      │→ merge-ready
 folder (specs/…) │  code-worker → code-reviewer → test-engineer →  │  pull request
                  │  test-runner → security-reviewer → deliver       │  (never auto-merged)
                  └─────────────────────────────────────────────────┘
```

`dev-run <folder>` enters directly from an approved speckit spec folder
(`spec.md` / `plan.md` / `tasks.md`). The factory never re-derives or
re-clarifies requirements (FR-005). Traceability identity derives from the
folder feature name — there is no factory-issued `spec_version_id` join key
(FR-006/009); the standalone `spec-run`/`spec-workflow` entry point was removed.

## Requirements

- Python ≥ 3.14 (managed with [uv](https://docs.astral.sh/uv/))
- Credentials (LLM, GitHub) come from the **environment or a secret store**
  only — never from committed config (FR-018).

## Install & verify

```sh
uv sync --dev
uv run ruff check .      # lint
uv run pytest            # unit + contract (network blocked)
uv run pytest -m integration   # end-to-end (deterministic, container-free)
```

## Quick usage

Deliver a merge-ready PR from a speckit spec folder (uses the deterministic
fake sandbox/git host; no LLM or container needed):

```sh
uv run python -m ai_factory.cli.dev_run \
  specs/002-folder-dev-run \
  --repo .factory/work --run-dir .factory/runstate \
  --sandbox fake --git-host fake
```

### `dev-run` exit codes

| code | meaning |
|------|---------|
| `0` | success — merge-ready PR delivered |
| `4` | dev delivery failed |
| `5` | stopped — re-planning exhausted, human required |

`1` signals a CLI/usage error. The retained spec role libraries (`spec_agent`,
`requirements_reviewer`) use `2` (review failed) / `3` (waiting on user) when
invoked through their own CLIs.

## `researcher` lookup library (mono-capacity)

`researcher` is a low-cost, **mono-capacity / non-escalating** lookup library
(see `specs/003-researcher/`). It returns a concise summary plus source
pointers — never a full-file dump — so a downstream planner/coder node can
quickly ground its work.

Run the `repo` scope (deterministic, **network-free**) from the CLI:

```sh
uv run python -m ai_factory.researcher.cli \
  --scope repo --query "login authentication password" \
  --roots specs/003-researcher --format json
```

Or from a library seam inside a workflow:

```python
from ai_factory.researcher import lookup

result = lookup("login authentication password", roots=["src"])
print(result.summary)   # concise, fits the invoking role's context window

# The `web` scope is network-bound: inject collaborators and run under
# `-m integration` (gated; skippable when network/LLM is unavailable).
# from ai_factory.researcher.web import UrllibWebFetcher, UrllibContentFetcher
# from ai_factory.shared.llm.provider import create_provider
# result = lookup("login", scope=["web"], llm=..., fetcher=...,
#                 content_fetcher=...)
```

## Live LLM provider & dual-mode (`specs/004-llm-live-provider/`)

The factory ships a stdlib-only, OpenAI-compatible **live** provider
(`openai-compatible`) with a **dual-mode** dev workflow: deterministic/offline
by default, opt-in live with a real model per capability level. The same
provider backs the `researcher` `web` scope (call-site #1) and the `dev_workflow`
role executor (call-site #2, via `ai_factory.dev_workflow.executor.runner`).

**Config surface (env-var only; no committed secrets, FR-018/SC-003):**

| Variable | Purpose |
|----------|---------|
| `OPENCODE_GO_API_KEY` / `OPENROUTER_API_KEY` | keys (never committed) |
| `OPENCODE_GO_BASE_URL` / `OPENROUTER_BASE_URL` | optional per-provider base URL |
| `MODEL_FAST_CHEAP`/`MODEL_CAPABLE`/`MODEL_DEEP` | per-*level* model override |
| `MODEL_DEFAULT` | global fallback model id |
| `AI_FACTORY_LIVE` | opt-in gate (`1`/true = live; unset = offline) |

**Offline vs live:** without `AI_FACTORY_LIVE` (and creds), every role stays
deterministic and network-free (`FakeProvider`). A run goes live only when the
operator opts in **and** a credential is present; an unmappable capability level
fails closed rather than dispatching a bad model id.

See [`specs/004-llm-live-provider/quickstart.md`](specs/004-llm-live-provider/quickstart.md)
for scenarios and the env-var / model-map walkthrough.

## Documentation

See [`specs/001-ai-dev-factory/quickstart.md`](specs/001-ai-dev-factory/quickstart.md)
for the full guide and validation Scenarios 1–7, and the `tasks.md` /
`spec.md` in the same directory for the design and functional requirements.
