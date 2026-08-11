# Feature Specification: Researcher Role (Low-Cost Lookup / Context Probe)

**Feature Branch**: `003-researcher`

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "No ai-factory, o planner, o coder, o tester, etc. — às vezes precisam consultar arquivos ou outras coisas (código, docs, e na web) para tomar decisões. Para não sujar o context do agente principal e poder usar um modelo mais barato, quero um agente utilitário de pesquisa, chamado `researcher`, que busca no repositório e na web e devolve só um resumo conciso — usando um modelo `fast-cheap`."

**Scope clarification**: This feature adds a **`researcher` role** to the ai-factory: a low-cost lookup library (Library-First) that the principal roles (`technical_planner`, `code_worker`, `test_engineer`, `code_reviewer`, etc.) can invoke to **query the repository (local `repo` scope) and the web (`web` scope)** and receive a **concise summary** with sourced pointers — instead of loading whole content into the invoking role's context. `researcher` is a **mono-capacity, fixed role**: its capability does **not** vary, so it does **not** participate in the `capability_levels` system (which exists for roles that escalate, e.g. `coder`/`tester`/`security` via `bump_level`). It carries its **own constant execution profile** inside its library. The deterministic `repo` core is network-free (constitution III/IV); the **`web` scope is part of this v1** (network-bound, tested under `-m integration`).

## Input (extended)

User request: "Não quero definir limites ainda; só quero que os agents possam usar o `researcher`, incluindo consultas ao repositório e à web. Otimização de custo/limites de modelos vem depois, no futuro." → concision/cost limits are out of scope for v1 and become future work.

## Clarifications

### Session 2026-08-11

- Q: What scopes does v1 support? → A: **`repo` and `web`** in v1. The deterministic, network-free `repo` core resolves relevant local files from a query and returns a concise summary + exact source pointers. The **`web` scope is part of the same deliverable** (network-bound, exercised via `-m integration`), layered on the same interface. Both scopes return a `ResearchResult`; concision/cost limits are explicitly **future work** and not acceptance criteria of this v1.
- Q: How should roles invoke the researcher? → A: As a **library function** (`lookup`) callable within the `dev_workflow` StateGraph, **and** exposed as a standalone CLI (`ai-factory-researcher`) for out-of-band use. The `repo` core is deterministic/network-free; the `web` scope requires network.
- Q: Which model does the researcher use? → A: `researcher` is a **mono-capacity fixed role**. It does **not** use `capability_levels` (there is nothing to escalate); it carries a **constant execution profile** defined in its own library. Its exact logical-model mapping is an implementation detail in code, not specified in this spec (concision/cost tuning is future work).
- Q: Should the researcher produce a full artifact (`research.md`) or just a concise result to the caller? → A: The primary output is a **concise `ResearchResult`** returned to the invoking role (and printed by the CLI as JSON/human). Writing a `research.md` brief is an **optional** convenience, not required for the core.
- Q: How should the `web` scope select which results to summarize? → A: **Multi-angle, best-per-angle (Option A)** — mirroring the `web_search` spirit: run 2–4 queries across distinct angles, rank each candidate by source quality (prefer official/primary over commentary; drop stale/SEO), and take the **best result per angle** to keep variety; cap the total by a **configurable context-window limit** (not a rigid N). Deterministic and unit-testable via `FakeProvider`/fakes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Query the Repository for Context (repo scope) (Priority: P1)

A role (`technical_planner`, `code_worker`, etc.) needs to know how something works in the repository before planning/editing. Instead of reading whole files, it calls the researcher with a natural-language query; the researcher scans the repo and returns a **concise summary** plus exact `path`/line pointers to the relevant files — keeping the caller's context small.

**Why this priority**: This is the core ask: keep the principal role's context clean and use a cheap model for the mechanical lookup.

**Independent Test**: Can be tested by calling the deterministic `lookup(query, roots=[...])` against a known `tmp_path` repo with a few files and asserting the returned `ResearchResult` surfaces the expected source file(s) for a given query, with a concise summary (well within the invoking role's **context window**) and correct `path`/line pointers.

**Acceptance Scenarios**:

1. **Given** a query mentioning terms present in a repo file, **When** the researcher runs `repo` scope, **Then** it returns a `ResearchResult` whose `sources` include that file and a concise `summary` that fits the invoking role's **context window** and does **not** dump the whole file.
2. **Given** a query with no matching sources, **When** the researcher runs, **Then** it returns an empty result (no sources, empty summary) rather than an error.
3. **Given** a repo with unrelated directories, **When** the researcher runs a query, **Then** only relevant files are surfaced (unrelated dirs are ignored).

---

### User Story 2 - Expose a Library-First CLI (Priority: P1)

The researcher is exposed as `ai-factory-researcher ... ` with JSON and human-readable output and meaningful exit codes, following the repo-wide `library-cli-convention`.

**Why this priority**: Every library exposes a CLI per the constitution; the researcher is no exception.

**Independent Test**: Can be tested by invoking the CLI against a `tmp_path` repo and validating the stdout JSON parses into a `ResearchResult` with `role == "researcher"` and correct `sources`.

**Acceptance Scenarios**:

1. **Given** a query and a root, **When** the CLI runs with `--scope repo --format json`, **Then** stdout carries a valid JSON `ResearchResult` and diagnostics go to stderr.
2. **Given** no query, **When** the CLI runs, **Then** it exits non-zero with a clear usage error.
3. **Given** an unresolvable/missing root, **When** the CLI runs, **Then** it exits non-zero with a clear error.

---

### User Story 3 - Register the researcher role (Priority: P2)

The `researcher` is a **mono-capacity, fixed role** with its own constant execution profile (outside the `capability_levels` escalation system). Its invocations emit per-role telemetry. Its result stays small so the invoking role's **context window** is not flooded.

**Why this priority**: This is what makes the role "cheap" and observable; it is required for the cost/context goal.

**Independent Test**: Can be tested by asserting `researcher` is a mono-capacity role with a constant execution profile (not in `capability_levels`/`FIXED_ROLES`), and that an invocation emits a telemetry record with `role == "researcher"`.

**Acceptance Scenarios**:

1. **Given** the researcher library, **When** its constant execution profile is read, **Then** it is defined (not from `capability_levels`/`FIXED_ROLES`).
2. **Given** a lookup, **When** telemetry is emitted, **Then** the record has `role == "researcher"`, its fixed model, tokens, cost, latency, and no secret-looking values.

---

### User Story 4 - Query the Web (web scope) (Priority: P1)

A role (planner/coder/tester) needs external context (docs, standards, benchmarks, a library's API) beyond the repo. It calls the researcher with a natural-language query and `scope=web`; the researcher searches the web (network-bound) **across 2–4 distinct angles**, ranks candidates by source quality (best-per-angle), and returns a **concise `ResearchResult`** with a `summary` and `sources` pointing to URLs — so the caller gets external grounding without an ad-hoc browser search polluting its context.

**Why this priority**: The user explicitly wants the agents to be able to use the researcher **for both the repository and the web**; both scopes are v1.

**Independent Test**: Can be tested at the library layer with injected **fake fetchers + a `FakeProvider`** (deterministic, network-free fixtures) asserting a `web`-scope `lookup` runs **multi-angle queries**, ranks candidates by quality (best-per-angle), and returns a `ResearchResult` with URL `sources` (varied across angles) and an LLM-summarized `summary` capped to the context-window limit; the real-HTTP/LLM path is exercised under `-m integration`.

**Acceptance Scenarios** (deterministic part via `FakeProvider` + `FakeWebFetcher` + `FakeContentFetcher`):

1. **Given** a `web`-scope query and fake fetch(es) across multiple angles + fake content + `FakeProvider` that ranks/summarizes, **When** `lookup(scope=web)` runs, **Then** it returns a `ResearchResult` whose `sources` are the **best-per-angle** URLs (varied) and whose `summary` is a concise synthesized text fitting the invoking role's context window.
2. **Given** a `web`-scope query where the fetcher/LLM fails/unreachable, **When** `lookup(scope=web)` runs, **Then** it surfaces a clear error (typed exception in library / non-zero exit in CLI) rather than silently returning nothing.
3. **Given** the integration environment with network+LLM, **When** the `web`-scope tests run with `-m integration`, **Then** they pass against a real (best-effort) fetch+summarize or are explicitly skipped when the network/LLM is unavailable.

### Edge Cases

- What happens when the query is empty string (`""`)? Return an **empty result** (no sources, empty summary), consistent with FR-004 — not an error. An empty/absent `--query` **argument on the CLI** is a usage error (non-zero exit, FR-007).
- What happens when the root does not exist / is not a directory? A clear non-zero error (CLI) or a typed exception (library).
- What happens when a file is binary/non-UTF8? Skip non-text files; only index plain-text source files.
- What happens when a matching file is very large? Cap indexing per file (e.g., read head/tail or a token cap) and note truncation in the source pointer — never load unbounded content.
- What happens when a directory contains vendored/generated files (`.venv`, `node_modules`, `.git`)? Exclude common noise/skip paths so the summary stays focused.
- What happens if the `web` scope hits a network error / the source is unreachable? The `repo` core still works network-free; for `web`, the lookup returns a clear non-zero error (CLI) / typed exception (library) rather than silently returning nothing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a network-free, deterministic core `lookup(query, *, roots)` that scans text files under `roots`, matches **repo scope** queries, and returns a `ResearchResult`. (This is the deterministic `repo`-core signature; the full repo+web signature `lookup(query, *, roots, scopes=..., llm=..., fetcher=..., content_fetcher=...)` is defined under Key Entities.)
- **FR-002**: For `repo` scope, the `ResearchResult` MUST contain a **concise** `summary` that (a) fits the invoking role's **context window**, and (b) does **NOT contain a verbatim replica of any matched source file** (the summary is prose/pointers, never a full-file dump). Concision is an implementation invariant (mechanism/constant lives in code, not specified numerically here). `sources` must be exact `path` (+ optional line-range/snippet) pointers. (See FR-005 for bounded reads and `truncated` handling of large files.)
- **FR-003**: The `ResearchResult` MUST include `role == "researcher"`, the original `query`, and the `scopes_used`.
- **FR-004**: A query with no matches MUST return an empty result (no sources, empty summary), not an error; an **empty-string query** also yields an empty result (an empty/absent `--query` on the CLI is a usage error, FR-007).
- **FR-005**: Non-text or binary files and common noise dirs (`.git`, `.venv`, `node_modules`, caches) MUST be skipped; large files MUST be capped per source (bounded reads).
- **FR-006**: System MUST define `researcher`'s execution profile as **mono-capacity and constant**, carried in its own library and **NOT** routed through the `capability_levels` system (which escalates `coder`/`tester`/`security`). There is no `bump_level` for `researcher`.
- **FR-007**: System MUST expose `ai-factory-researcher` CLI with `--scope repo|web --query ... --roots ... [--format json|human]`, JSON stdout + diagnostics stderr, and meaningful exit codes (0 ok, non-zero for usage/resolution errors). For `repo` scope **`--roots` is required**; a missing `--roots` or missing `--query` is a usage error (non-zero exit).
- **FR-008**: System MUST emit **per-role telemetry** for each lookup (role `researcher`, the **fixed profile model** — constant, per FR-006, not a variable capability level — tokens, cost, latency, errors, result), with no secret-looking values logged.
- **FR-009**: System MUST provide a callable library function (e.g. `lookup`) usable **inside the `dev_workflow` StateGraph** by the principal roles, returning a concise `ResearchResult` so the caller's context stays small (this is a future-integration seam; wiring it into every planner/coder node is NOT in scope for v1 — the library + CLI are, with a documented call site).
- **FR-010**: System MUST implement the **`web` scope** (network-bound) in v1 as **Option D**: run **2–4 queries across distinct angles** → **rank** candidates by source quality via the injected `LLMProvider` (**best-per-angle**, prefer official/primary over commentary, drop stale/SEO) → **fetch content** of the selected URLs via an injected `ContentFetcher` → **summarize** via the `LLMProvider` into the `ResearchResult.summary`, capped by a **configurable context-window limit** (not a rigid N). All three collaborators (`LLMProvider`, `WebFetcher`, `ContentFetcher`) are **injected** / pluggable so unit tests run deterministic and network-free with `FakeProvider` + fakes. Errors are surfaced clearly (typed exception / non-zero CLI exit), never silently empty. Real network/LLM path is exercised under `-m integration`.

### Key Entities *(include if feature involves data)*

- **`researcher` role**: a mono-capacity, fixed low-cost role with its own constant execution profile (outside `capability_levels`); its results are **concise** summaries that fit the invoking role's **context window**.
- **`ResearchResult`** (Pydantic model): `role`, `query`, `summary`, `sources: list[ResearchSource]`, `scopes_used`, plus telemetry/observability ancillary fields.
- **`ResearchSource`** (Pydantic model): `path`, optional line-range/snippet, optional note about truncation.
- **`lookup(query, *, roots, scopes=None, llm=None, fetcher=None, content_fetcher=None)`**: the core function returning `ResearchResult`. `repo` scope is deterministic (no deps); `web` scope runs **multi-angle queries**, ranks candidates by source quality (**best-per-angle**), fetches content, and summarizes via the injected `LLMProvider` + `WebFetcher` + `ContentFetcher` (deterministic via `FakeProvider`/fakes in unit tests).
- **`ai-factory-researcher` CLI**: the library CLI wrapper.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A `repo`-scope lookup against any small repo returns a `ResearchResult` whose `sources` point to the correct files and whose `summary` is **concise**: it fits the invoking role's **context window** and does **NOT** contain a verbatim full-file dump (asserted by `test_lookup_summary_is_concise_not_a_dump`).
- **SC-002**: 100% of the deterministic `repo`-core unit/contract tests pass **without network**. The `web`-scope library logic is also testable **without network** (via `FakeProvider` + `FakeWebFetcher` + `FakeContentFetcher`); only the real network/LLM path is gated `-m integration`.
- **SC-003**: `researcher` is a mono-capacity fixed role with a constant execution profile defined in its own library (not in `capability_levels`/`FIXED_ROLES`); its summary fits the invoking role's context window.
- **SC-004**: The CLI emits valid JSON/human output to stdout, diagnostics to stderr, and correct exit codes for ok / empty / usage-error / resolution-error.
- **SC-005**: Every invocation emits a telemetry record with `role == "researcher"` and no secret-looking values.
- **SC-006**: `uv run ruff check .` passes and the full `pytest` suite remains green; the `repo`-core unit/contract tests run **without network**, and the `web`-scope integration tests run under `-m integration` when network is available.

## Assumptions

- **`repo` + `web` in v1**: both scopes are part of this deliverable. The deterministic `repo` core is network-free; `web` is Option D (LLM rank + content fetch + LLM summarize) with all collaborators injected so it is unit-testable offline via `FakeProvider`/fakes; the real network/LLM path is integration-gated.
- **Limits/cost are future**: concision thresholds, cost budgets, and model-limit tuning are explicitly **not** acceptance criteria of v1 (user: "otimização de custo/limites vem depois"); the v1 goal is that agents can **use** the researcher.
- **Mono-capacity role**: `researcher` has a fixed, non-escalating execution profile outside `capability_levels`; unlike `coder`/`tester`/`security`, its capability never varies. Concrete model/cost tuning is future work.
- **Library-First**: The researcher is a standalone library under `src/ai_factory/researcher/` with its own CLI, telemetry, and tests; the principal workflows compose it, not the reverse.
- **Deterministic core, optional LLM**: The core does not require an LLM or network; LLM enrichment is optional and never required for correctness.
