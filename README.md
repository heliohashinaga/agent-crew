# AI Software Development Factory

Turns a natural-language feature request into a **reviewed, merge-ready pull
request** through two independent, traceable workflows (FR-024).

## The two workflows

```
                  ┌──────────────── spec workflow ────────────────┐
 feature request →│  spec-agent → requirements-reviewer → human   │→ approved
 (text)           │             (amend loop)      approval gate   │  SpecVersion
                  └──────────────────────────┬───────────────────┘
                                             │  joined ONLY by spec_version_id (FR-025)
                                             ▼
                  ┌────────────────── dev workflow ──────────────────┐
                  │  planner → orchestrator → code-worker →          │→ merge-ready
                  │  code-reviewer → test-engineer → test-runner →   │  pull request
                  │  security-reviewer → deliver                     │  (never auto-merged)
                  └──────────────────────────────────────────────────┘
```

Each workflow is a distinct run; a dev run loads the approved spec **by
reference** (`spec_version_id`) and is traceable back through `spec_run_id`.

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

Create and approve a spec, then deliver a PR (uses the deterministic fake
sandbox/git host; no LLM or container needed):

```sh
# 1. Specification workflow -> approved, versioned spec (exit 0)
uv run python -m ai_factory.cli.spec_run \
  --request "Sessions must expire after 30 minutes" \
  --auto-approve --store .factory/specs

# 2. Development workflow -> merge-ready PR (exit 0)
uv run python -m ai_factory.cli.dev_run \
  --spec-version <spec_version_id> \
  --spec-store .factory/specs --repo .factory/work \
  --sandbox fake --git-host fake
```

### Exit codes

| code | meaning |
|------|---------|
| `0` | success (spec approved / PR delivered) |
| `2` | spec rejected |
| `3` | needs clarification / human deferred |
| `4` | dev delivery failed |
| `5` | stopped — re-planning exhausted, human required |

## Documentation

See [`specs/001-ai-dev-factory/quickstart.md`](specs/001-ai-dev-factory/quickstart.md)
for the full guide and validation Scenarios 1–7, and the `tasks.md` /
`spec.md` in the same directory for the design and functional requirements.
