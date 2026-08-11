# Research: Researcher Role (Low-Cost Lookup / Context Probe)

## Summary

`researcher` is a **mono-capacity, fixed role** in the ai-factory: a Library-First
lookup library under `src/ai_factory/researcher/` that the principal roles
(planner/coder/tester/reviewer) invoke to query the repository (`repo` scope) and
the web (`web` scope, in v1) and receive a **concise, sourced `ResearchResult`**
instead of loading whole content into their context. It does **not** participate in
`capability_levels` (there is nothing to escalate); it carries a **constant execution
profile** in its own library. Cost/concision tuning is explicitly out of scope for v1.

## Decisions

### D1 — Mono-capacity fixed role, outside `capability_levels`
- **Decision**: `researcher` is a fixed, non-escalating role with a constant
  execution profile defined in its own library (`src/ai_factory/researcher/`); it is
  **not** added to `capability_levels`/`FIXED_ROLES` and has no `bump_level`.
- **Rationale**: Unlike `coder`/`tester`/`security` (which escalate capability via
  `bump_level`/FR-015), the researcher's capability never varies — it always does the
  same lookup. Routing it through `capability_levels` would be dead complexity (YAGNI,
  Simplicity). The exact logical-model mapping is an implementation detail, tuned later.
- **Alternatives considered**: Adding it as a fixed role in `capability_levels`
  (rejected: implies an escalation axis that doesn't apply); adding `bump_level`
  support (rejected: nothing to escalate).

### D2 — `repo` core deterministic & network-free; `web` in v1
- **Decision**: v1 ships **both `repo` and `web` scopes**. The `repo` core is
  deterministic and network-free (constitution III/IV); `web` is network-bound,
  exercised under `-m integration`.
- **Rationale**: User wants the agents to be able to use the researcher against both
  the repository and the web; deterministic core keeps unit/contract tests offline;
  web is an integration-gated increment on the same `ResearchResult` interface.
- **Alternatives considered**: repo-only v1 with web-later (rejected: user asked for
  web now); web-only (rejected: repo lookup is the primary deterministic need).

### D3 — `web` scope: Option D (LLM rank + content fetch + LLM summarize), multi-angle
- **Decision**: `web` runs **2–4 queries across distinct angles** → **rank** candidates
  by source quality via `LLMProvider` (**best-per-angle**) → **fetch content** of the
  selected URLs via `ContentFetcher` → **summarize** via `LLMProvider`, capped by a
  **configurable context-window limit** (not a rigid N). All collaborators injected.
- **Rationale**: Mirrors the `web_search` spirit (multi-angle queries, quality-over-priority,
  best source per angle, citations). Injected `LLMProvider`/`WebFetcher`/`ContentFetcher`
  make it unit-testable offline via `FakeProvider` + fakes (the factory already ships
  `FakeProvider` in `shared/llm/provider.py`).
- **Alternatives considered**: A (first-N raw) — rejected: weak, no angle variety;
  B (deterministic top-N + LLM seam) — valid but user chose D for synthesized summary;
  C (LLM rank only, simple summary) — valid but user chose full synthesis (D).

### D4 — Library-First pattern mirrors `spec_agent.agent.draft_spec`
- **Decision**: Model the deterministic core on `spec_agent.agent.draft_spec` — pure,
  network-free function with an optional injected `LLMProvider` used only to enrich.
- **Rationale**: This is the repo's canonical role-library pattern (deterministic core,
  optional LLM, CLI + telemetry). Reusing it keeps the researcher consistent.
- **Alternatives considered**: A new bespoke pattern (rejected: inconsistency).

### D5 — Reuse `shared/cli_util` + `shared/telemetry`
- **Decision**: The `ai-factory-researcher` CLI reuses `add_output_format_arg`, `emit`,
  `write_stdout`/`write_stderr`, `run`, and exit codes; each lookup emits a
  `TelemetryRecord` with `role == "researcher"`, redating secrets via `redact_secrets`.
- **Rationale**: Repo-wide library-cli-convention and observability (FR-008); no
  derivative for a utility role. Models `ResearchSource`/`ResearchResult` are Pydantic.
- **Alternatives considered**: standalone CLI plumbing (rejected: violates convention).

## Dependencies / Interfaces

- **`shared/llm/provider.py`**: `LLMProvider` (ABC) + `FakeProvider` + `PROVIDERS["fake"]`
  — used by the `web` scope (rank + summarize) and by unit tests (network-free).
- **`shared/cli_util.py`**: CLI helpers + exit codes.
- **`shared/telemetry/record.py`**: `TelemetryRecord` + role literal (add `"researcher"`).
- **Filesystem scanning**: `os.walk`/`fnmatch`-based deterministic repo scan (no stdlib
  beyond core; skip binary and noise dirs `.git`/`.venv`/`node_modules`; cap per-file reads).

## Gaps / Next Steps

- `web` requires network/LLM; the deterministic `repo` core never does (SC-002).
- Real `web` fetchers + real `LLMProvider` wiring are integration-only (`-m integration`).
- Exact `n_angles` and the context-window cap default are implementation detail
  (T014/T015), not committed spec numbers.
