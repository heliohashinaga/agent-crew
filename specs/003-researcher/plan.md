# Plan: Researcher Role (Low-Cost Lookup / Context Probe)

**Feature Branch**: `003-researcher`
**Last Updated**: 2026-08-11
**Spec**: [`spec.md`](./spec.md) | **Tasks**: [`tasks.md`](./tasks.md)

## Summary

Add a low-cost `researcher` role to the ai-factory: a deterministic, Library-First
lookup library under `src/ai_factory/researcher/` that lets the principal roles
(planner/coder/tester/reviewer) query the repository (`repo` scope) **and the web
(`web` scope)** — both in v1 — and receive a **concise, sourced `ResearchResult`**
instead of loading whole content into their context. The role is a **mono-capacity,
fixed role** with a **constant execution profile carried in its own library**
(outside the `capability_levels` escalation system used by `coder`/`tester`/
`security`). Per the
constitution, the deterministic `repo` core is network-free; `web` is network-bound
and exercised under `-m integration`. Concision/cost limits are **future work** and
are not acceptance criteria of this v1 (user: "otimização de custo/limites vem depois").

## Technical Context

- **Deterministic core mirror**: Model the core on `spec_agent.agent.draft_spec` —
  a pure, network-free function with an optional `LLMProvider` used only to enrich,
  never to gate correctness.
- **Capability model**: `researcher` is a **mono-capacity, fixed role**. It does
  NOT participate in `capability_levels`/`FIXED_ROLES` (which escalates
  `coder`/`tester`/`security` via `bump_level`, FR-015). Instead, `researcher`
  carries a **constant execution profile inside its own library** (e.g. a
  `ResearcherProfile`/constant), so there is nothing to escalate or tune per-run;
  the exact logical-model mapping is an implementation detail (future tuning).
- **CLI convention**: Reuse `shared/cli_util` (`add_output_format_arg`, `emit`,
  `run`, `write_stdout`/`write_stderr`) so JSON goes to stdout and diagnostics to
  stderr with meaningful exit codes, per the repo-wide `library-cli-convention`.
- **Telemetry**: `shared/telemetry/record.py` provides `TelemetryRecord`
  (zero-defaulted tokens/cost/latency/tool_calls). Register a `"researcher"` role and
  emit one record per lookup, redacting secrets.
- **Repo scanning (repo scope)**: plain deterministic `os.walk`/`fnmatch` + bounded
  reads; skip binary/noise dirs (`.git`, `.venv`, `node_modules`, caches); cap
  per-file reads; match tokenized query terms against paths/names and small contents;
  surface exact `path` (+ line-range/snippet) pointers.
- **No network in core**: unit + contract tests never hit HTTP and never require an
  `LLMProvider` for correctness (constitution III/IV). Web-scope tests run only via
  `uv run pytest -m integration`.

## Design Decisions

- **`repo` + `web` both v1**: v1 ships the deterministic `repo` core, the `web`
  scope (network-bound, `-m integration`), the CLI, and the registered role. Both
  scopes return a `ResearchResult`. A network/LLM error in `web` surfaces clearly
  (non-zero CLI / typed exception), never silently returns nothing.
- **Library callable in the StateGraph**: expose `lookup(query, *, roots, scopes=None)`
  so principal roles can compose it later; wiring it into each planner/coder/test node
  is explicitly out of scope for v1 (FR-009) — the documented seam ships now.
- **Cheap, fixed role**: researcher never escalates to a capable/deep model; each
  lookup returns a **concise** `summary` that fits the invoking role's **context
  window**, keeping the caller's context small and cost low.

## Implementation Phases

### Phase 1 — Scaffold & Models (`specs` => lintable package)
- T002 scaffold `ai_factory/researcher/`; T003 `ResearchSource`; T004 `ResearchResult`.
- Exit: Red tests import-fail then turn green; ruff clean.

### Phase 2 — Deterministic Repository Core (US1)
- T010 `lookup(query, *, roots)` deterministic scan+summary; T011 empty/no-match;
  T012 skip-binary/noise/cap-large; T013 conciseness invariant.
- Exit: `tests/unit/researcher/test_agent.py` green, no network.

### Phase 3 — Library-First CLI (US2)
- T020 parser; T021 `repo` JSON stdout + stderr diagnostics + exit 0; T022 human
  output + `web` scope CLI (URL sources; network failure → non-zero).
- Exit: `tests/contract/researcher/test_cli.py` green.

### Phase 4 — Mono-capacity Profile (US3)
- T030 define a constant execution profile for `researcher` in its own library
  (NOT in `capability_levels`/`FIXED_ROLES`);
  T031 register role in telemetry and emit per-lookup record.
- Exit: unit tests assert a constant mono-capacity profile + telemetry shape; ruff clean.

### Phase 5 — Polish, Docs & Full Green
- T040 wire telemetry; T041 docs (AGENTS.md role list + README/quickstart example);
  T042 full suite green (`ruff check .` clean, `pytest -q` no network, integration gated).

### Acceptance Handoff
- T050 worked-example repo (auth micro-repo) lookup correctness + concision (SC-001);
  T051 empty/error boundary checks; T052 deep read-only review (Library-First, no
  network in core).

## Risks & Mitigations

- **Web network dependency** → `web` is v1 but network-bound: the deterministic
  `repo` core never requires network; `web`-scope tests run under `-m integration`
  and surface clear errors on failure (never silent empty result).
- **Context/future tuning** → initial v1 returns a concise summary (fits the
  invoking role's context window) with bounded per-file reads and a `truncated` flag
  on sources; explicit concision/cost/model tuning is **future work**, not an
  acceptance criterion of this v1.
