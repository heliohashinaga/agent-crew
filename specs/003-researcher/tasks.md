# Tasks: Researcher Role (Low-Cost Lookup / Context Probe)

> `003-researcher`
> Status: In progress

- [ ] **Constitution**: TDD is non-negotiable — every implementation task starts
      from a failing (Red) test. No code merges without passing tests. Ruff must
      pass (`uv run ruff check .`). `pytest` (unit + contract) must pass with no
      network required; web-scope tests are gated `-m integration`.
- [ ] Implementation order: Phase 1 (scaffold + model) → Phase 2 (deterministic
      repo core, US1) → Phase 3 (CLI, US2) → Phase 4 (mono-capacity profile,
      US3) → Phase 5 (telemetry + polish + full green suite).

## Phase 1 — Scaffold & Data Models

### US1-US3 Foundation

- [x] **T001 — Specify & approve** — Author this feature spec
      (`specs/003-researcher/spec.md`), research notes (`research.md`), and task
      list (`tasks.md`). Approved by user before implementation begins.
- [x] **T002 — Scaffold `researcher` package [Red→Green]** — Create package
      skeleton `src/ai_factory/researcher/__init__.py`, `models.py`, `agent.py`,
      `cli.py` (empty imports only). Add `tests/unit/researcher/` and
      `tests/contract/researcher/`. **Red**: a smoke test importing
      `ai_factory.researcher.agent` and `.models` fails to collect.
- [x] **T003 — Define `ResearchSource` model [Red→Green]** —
      `src/ai_factory/researcher/models.py`. Fields: `path: str`, `lines: str|None = None`
      (range like `"14-40"`), `snippet: str|None = None`, `truncated: bool = False`.
      **Red**: unit test builds and round-trips a `ResearchSource` via
      `model_validate_json`.
- [x] **T004 — Define `ResearchResult` model [Red→Green]** —
      `src/ai_factory/researcher/models.py`. Fields: `role: str = "researcher"`,
      `query: str`, `summary: str = ""`, `sources: list[ResearchSource] = []`,
      `scopes_used: list[str] = ["repo"]`, plus telemetry/observability ancillaries
      (`tokens: int = 0`, `cost_usd: float = 0.0`, `latency_s: float = 0.0`).
      **Red**: unit test round-trips a `ResearchResult` and checks defaults.

## Phase 2 — Deterministic Repository Core (US1)

### User Story 1 - Query the Repository for Context (repo scope)

- [x] **T010 — Deterministic `lookup(query, *, roots)` core [Red→Green]** —
      `src/ai_factory/researcher/agent.py`. For `repo` scope: scan text files under
      `roots` (recursively), skip non-text/binary files and noise dirs
      (`.git`, `.venv`, `node_modules`, caches); match a tokenized query against
      file path/names and (for small files) head contents; cap per-file reads;
      return a **concise** `ResearchResult` with `sources` as exact `path`
      (+ line-range/snippet). Deterministic, no LLM, no
      network. **Red**: tests in `tests/unit/researcher/test_agent.py` — return a
      deterministic result, default scope `["repo"]`, empty-query is an empty result,
      unrelated dirs ignored, summary stays concise (fits context window).
- [x] **T011 — Empty query / no-match behavior [Red→Green]** — A query with no
      matching files returns empty `sources` and empty `summary` (not an error);
      empty query is also an empty result. **Red**: tests assert empty result shape.
- [x] **T012 — Skip binary + noise + cap large files [Red→Green]** — Binary/non-UTF8
      files and common noise dirs are skipped; large files are bounded (head/tail or
      token cap) and the matching source sets `truncated=True`. **Red**: tests with a
      binary blob, a noise dir, and a large file assert correct skip/truncation.
- [x] **T013 — Conciseness invariant [Green]** — Add an internal implementation constant
      (e.g. a summary-length cap and a per-file read bound) to keep the generated
      summary **concise** — held as code detail, **not** specified numerically in the
      spec (qualitative, context-window). Concrete assertion: the summary MUST NOT
      contain a verbatim full-file dump (aligns FR-002/SC-001 and
      `test_lookup_summary_is_concise_not_a_dump`); a large matched file is bounded
      and its source sets `truncated=True`. No new public API.
- [ ] **T014 — Deterministic `web` core (Option D) with injected fakes [Red→Green]** —
      `src/ai_factory/researcher/agent.py` (and `web.py`): the `web` scope runs
      **multi-angle queries** (2–4 angles) → **rank** candidates by source quality
      via `LLMProvider` (**best-per-angle**) → **fetch content** of the selected URLs
      via `ContentFetcher` → **summarize** via `LLMProvider`, capped by a configurable
      **context-window limit**; `LLMProvider`, `WebFetcher`, and `ContentFetcher` are all
      **injected** (pluggable). On any fetch/LLM failure, raise a typed exception
      (never silently empty). **Red**: unit tests in
      `tests/unit/researcher/` with `FakeProvider` + `FakeWebFetcher` +
      `FakeContentFetcher` assert (a) `scope=web` yields best-per-angle (varied) URL
      `sources` + an LLM-summarized concise `summary`, (b) fetcher/provider failure raises
      `ResearcherWebError` — all deterministic and network-free.
- [ ] **T015 — Real network/LLM `web` path (integration) [Red→Green]** —
      `src/ai_factory/researcher/web.py`: real `WebFetcher` + `ContentFetcher` + a
      real `LLMProvider` wired to the `web` scope. **Red**: integration tests under
      `-m integration` assert a best-effort real fetch+summarize returns
      `ResearchResult` with URL sources + synthesized summary, or skip when
      network/LLM is unavailable (no failure on offline CI).

## Phase 3 — Library-First CLI (US2)

### User Story 2 - Expose a Library-First CLI

- [x] **T020 — `ai-factory-researcher` CLI parser [Red→Green]** —
      `src/ai_factory/researcher/cli.py`. `--query` (required), `--roots`
      (repeatable / comma), `--scope {repo,web}` (default `repo`), `--output-format
      {json,human}` via `add_output_format_arg`, reuse `run`/`emit`/`write_stdout`.
      **Red**: contract test asserts usage error (non-zero) when `--query` is missing.
- [x] **T021 — `repo` scope stdout → valid JSON + diagnostics to stderr [Red→Green]** —
      Calling the CLI with `--scope repo --query "..." --roots <tmp>` prints valid JSON
      `ResearchResult` to stdout (parses via `ResearchResult.model_validate_json`,
      `role=="researcher"`, correct `sources`), diagnostics to stderr, exit `0`.
      **Red**: contract CLI test drives `run(main, [...])` with `capsys`.
- [x] **T022 — Human-readable output + `web` scope CLI [Red→Green]** —
      `--output-format human` prints a readable brief; `--scope web` calls the same
      `ResearchResult` interface (web core from Phase 2) and prints the web `sources`
      (URLs) to stdout; on a network/unreachable error it exits non-zero with a clear
      error (never silently empty). **Red**: contract tests assert human output
      contains summary/source paths; a web stub success prints URL sources; a web
      stub failure exits non-zero.

## Phase 4 — Mono-capacity Profile (US3)

### User Story 3 - Define the researcher mono-capacity profile

- [ ] **T030 — Define constant execution profile for `researcher` [Red→Green]** —
      In `src/ai_factory/researcher/` (e.g. `profile.py`): define a **constant,
      non-escalating** execution profile for `researcher` (a typed object/constant:
      logical model, limits). This profile lives in the researcher library AND is
      **NOT** routed through `capability_levels`/`FIXED_ROLES` — `researcher` does
      not participate in the escalation system that serves `coder`/`tester`/
      `security` (no `bump_level`). **Red**: unit test asserts `researcher` exposes
      a constant mono-capacity profile and that `researcher` is NOT in
      `capability_levels.FIXED_ROLES`.
- [x] **T031 — Telemetry record for researcher [Red→Green]** — Add `"researcher"` to
      the `DevRole`/role literal (or a dedicated role union) in
      `src/ai_factory/shared/telemetry/record.py`. Emit a `TelemetryRecord` per lookup
      with `role=="researcher"`, its fixed profile model, tokens, cost, latency,
      result; redact secrets. **Red**: unit test asserts an emitted record carries
      `role=="researcher"` and no secret-looking values.

## Phase 5 — Polish, Docs & Full Green

- [x] **T040 — Wire telemetry into `lookup`/CLI [Green]** — The deterministic core
      and CLI optionally record telemetry; no new public API. Ensure invariants hold
      and tests remain green.
- [ ] **T041 — Docs**: Add `researcher` to `AGENTS.md` role list and a short section
      / example in `README.md` (and `quickstart.md` of this feature). Document the
      intended StateGraph call site (library function seam) without wiring it into
      every planner/coder node in this pass.
- [ ] **T042 — Full suite Green + Ruff** — `uv run ruff check .` clean; `uv run
      pytest -q` (unit+contract) all pass with **no network**; web-scope integration
      tests gated `-m integration` pass when network is available.

## Acceptance Handoff

- [ ] **T050 — Against the worked example** — A `repo` lookup for
      "login authentication password" against a micro auth repo returns a
      `ResearchResult` whose `sources` include `service.py` and a concise
      `summary` (fits the invoking role's context window, no full-file dump)
      — matching US1 / SC-001.
- [ ] **T051 — Boundary check** — Empty query, missing `--query`, missing/invalid
      root, binary/noise skip, and `web` scope network/unreachable failure: all
      handled (empty result or clear non-zero error, never silent empty).
- [ ] **T052 — Deep review** — Read-only review of the diff verifying Library-First
      (workflows never depend on researcher); the deterministic `repo` core has no
      network, and `web` is network-bound/integration-gated; approve merge.
