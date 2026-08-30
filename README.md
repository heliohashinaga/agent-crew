# AI Dev Factory

> **Agent-to-agent interaction across the software development cycle**: a swarm
> of specialized AI role-agents (planner, coder, reviewer, tester, security)
> that hand work between one another to turn a natural-language feature
> request into a **reviewed, merge-ready pull request** — every step traceable
> and auditable.

[![CI](https://github.com/heliohashinaga/agentic-relay/actions/workflows/ci.yml/badge.svg)](https://github.com/heliohashinaga/agentic-relay/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.14-blue)](#requirements)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Why this exists

Coding agents are powerful, but **one prompt → one answer** is fragile. AI Dev
Factory inverts the loop: instead of a single model doing a single pass, a
**swarm of interacting role-agents** (planner, coder, reviewer, tester, security,
orchestrator) works through the development cycle — each agent passes its
output to the next, and the change is **verified by an independent agent**, not
by the model that wrote it.

The result is a **reviewed, merge-ready PR**, always grounded in a
specification, with observable telemetry for every step and every handoff.

## Highlights

- **Library-First architecture** — every role/capability is a standalone,
  independently testable library exposed through a CLI; workflows *compose*
  libraries, never the reverse.
- **Spec-driven (spec-kit)** — each feature starts with a `spec` → `plan` →
  `tasks`, so every change traces back to an approved specification.
- **External verification, no self-grading** — work is gated by an independent
  reviewer; the actor that produced it can never mark its own work done.
- **Durable & resumable** — the production workflow checkpoints by phase, and
  the optional `loop_engine` persists an autonomous control loop to a ledger
  so long runs survive crashes.
- **Deterministic by default, live on demand** — unit/contract tests and the
  library cores are **network-free**; real LLM calls are opt-in behind
  injectable seams (so CI stays hermetic and trustworthy).
- **Observable** — per-role telemetry (tokens, cost, latency, retries, errors,
  escalations), with secrets auto-redacted before any emission.

---

## Requirements

- Python ≥ 3.14 (managed with [uv](https://docs.astral.sh/uv/))
- Credentials (LLM, GitHub) come from the **environment or a secret store**
  only — never from committed config (FR-018).

## Install & verify

```sh
uv sync --dev
uv run ruff check .            # lint
uv run pytest                  # unit + contract (network blocked)
uv run pytest -m integration   # end-to-end (deterministic, container-free)
```

### CI is hermetic

Deterministic `lint`/`test`/`integration` jobs **block network access**. The
real-network `live` job runs only on demand, so CI always gives trustworthy,
reproducible results.

---

## The folder-driven dev workflow

```
                  ┌───────────────────── dev workflow ───────────────────┐
 speckit spec     │  folder-adapter → planner → orchestrator →           │→ merge-ready
 folder (specs/…) │  code-worker → code-reviewer → test-engineer →       │  pull request
                  │  test-runner → security-reviewer → deliver            │  (never auto-merged)
                  └──────────────────────────────────────────────────────┘
```

`dev-run <folder>` enters directly from an approved speckit spec folder
(`spec.md` / `plan.md` / `tasks.md`). The factory never re-derives or
re-clarifies requirements (FR-005); traceability identity derives from the
folder feature name.

Deliver a merge-ready PR from a spec folder (uses the deterministic fake
sandbox/git host; no LLM or container needed):

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

---

## `researcher` lookup library (mono-capacity)

A low-cost, **mono-capacity / non-escalating** lookup library. It returns a
concise summary plus source pointers — never a full-file dump — so a downstream
planner/coder node can quickly ground its work.

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

---

## `loop_engine` autonomous control loop

A standalone **Library-First** control-loop capability: **actor → external gate
→ repair → repeat** until the gate passes or termination conditions
(`max_iterations`, budget, stall ratchet) are met, persisting a **durable
ledger/spine** so a run can be paused/resumed. It is **not** wired inside
`dev_workflow` nodes in v1 (FR-010) — workflows/CLIs compose it.

```sh
uv run ai-factory-loop --actor factory --gate composite \
  --run-id demo --max-iterations 3 --format json
```

Or compose it as a library (inject `Actor`/`Gate` seams):

```python
from ai_factory.loop_engine import LoopConfig, run_loop
from ai_factory.loop_engine.gate import CompositeGate, artifact_exists

config = LoopConfig(
    actor=my_actor,            # injectable Actor seam
    gate=CompositeGate(deterministic=[artifact_exists]),
    max_iterations=5,
    run_id="demo",
)
result = run_loop(config, ledger_dir=".factory/loops")
print(result.status, result.iterations)  # passed / exhausted / stalled
```

**Safety invariants**: no self-grading (success derives only from the external
gate, FR-002); `stalled` is distinct from `exhausted`; actor-exceptions are
budget-bounded retries separate from `max_iterations`; budget is a **hard stop**
within `loop_engine`. The deterministic core is network-free; the
independent-reviewer gate is integration-gated.

---

## Live LLM provider & dual-mode

A stdlib-only, OpenAI-compatible **live** provider with a **dual-mode** dev
workflow: deterministic/offline by default, opt-in live with a real model per
capability level. The same provider backs the `researcher` `web` scope
(call-site #1) and the `dev_workflow` role executor (call-site #2).

**Config surface (env-var only; no committed secrets):**

| Variable | Purpose |
|----------|---------|
| `OPENCODE_GO_API_KEY` / `OPENROUTER_API_KEY` | keys (never committed) |
| `OPENCODE_GO_BASE_URL` / `OPENROUTER_BASE_URL` | optional per-provider base URL |
| `MODEL_FAST_CHEAP` / `MODEL_CAPABLE` / `MODEL_DEEP` | per-*level* model override |
| `MODEL_DEFAULT` | global fallback model id |
| `AI_FACTORY_LIVE` | opt-in gate (`1`/true = live; unset = offline) |

**Offline vs live:** without `AI_FACTORY_LIVE` (and creds), every role stays
deterministic and network-free (`FakeProvider`). A run goes live only when the
operator opts in **and** a credential is present; an unmappable capability level
fails closed rather than dispatching a bad model id.

See [`specs/004-llm-live-provider/quickstart.md`](specs/004-llm-live-provider/quickstart.md)
for scenarios and the env-var / model-map walkthrough.

---

## Architecture principles

The factory is built around a **constitution** (see
[`AGENTS.md`](AGENTS.md)) that its own agents must follow:

1. **Library-First** — each role/capability is a standalone, independently
   testable library with its own CLI; workflows compose, never depend on.
2. **CLI Interface** — every library exposes JSON + human-readable output and
   meaningful exit codes.
3. **Test-First (TDD, non-negotiable)** — a failing test precedes every
   implementation.
4. **Integration Testing** — the workflow boundary is tested end-to-end.
5. **Simplicity & Observability** — per-role telemetry; YAGNI.

`specs/001-ai-dev-factory/` holds the full design: quickstart, data-model,
contracts and the FAQ.

---

## Security

- **Credentials are env-only** (FR-018): no keys, tokens, or secrets are ever
  committed. They load only from the environment or a secret store via
  `ai_factory.shared.secrets.loader`.
- **Auto-redaction**: secret-looking values (`Bearer …`, `api_key=…`,
  `password=…`) are redacted from all logs, CLI output, and telemetry before
  emission.
- **Hermetic CI**: deterministic jobs block network access; the real-network
  `live` job runs only on `workflow_dispatch`.
- **Deterministic library cores** are network-free; any network/LLM path sits
  behind injectable seams and is integration-gated.
- **Review/merge**: no auto-merge to `main`; changes land through reviewed
  pull requests.

---

## License & contributing

**License**: MIT — see [`LICENSE`](LICENSE).

**Contributing**: implementation is driven by the spec-kit workflow
(`specs/*/tasks.md`); see [`AGENTS.md`](AGENTS.md) for the constitution and
conventions. Design artifacts for new capabilities live under `specs/<n>-*/`.