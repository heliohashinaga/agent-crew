---

description: "Task list for the Coder → Cleaner agent pipeline"
---

# Tasks: Coder → Cleaner Agent Pipeline

**Input**: Design documents from `/specs/002-coder-cleaner/`

**Prerequisites**: plan.md, spec.md (US1), research.md, data-model.md, contracts/coder-cleaner-pipeline.md

**Tests**: The project constitution (`.specify/memory/constitution.md`; runtime guidance in `AGENTS.md`) mandates **TDD (non-negotiable)**, including automated tests for the node-to-node handoff seam (Principle IV) — test tasks MUST be written to fail before implementing.

**Organization**: Grouped by user story. This feature has one user story (US1, P1, MVP) plus cross-cutting phases.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1)
- Include exact file paths in descriptions

## Path Conventions

Single Python project: `src/`, `tests/` at repository root (package `agentcrew`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Declare the orchestration dependency and package scaffolding

^- [X] T001 Add explicit `langgraph>=1.2.10` to `pyproject.toml` deps; `uv lock`/`uv sync` resolves cleanly (FR-009). `langgraph-checkpoint` is OPTIONAL for v1 — add only if a threaded/checkpointed dev run is needed (YAGNI); otherwise `data-model.md`'s "InMemorySaver (if used)" stays un-reified.
^- [X] T002 [P] Create `src/agentcrew/agents/__init__.py` and `src/agentcrew/graphs/__init__.py` package inits

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared state that MUST exist before US1

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

^- [X] T003 Add `TaskState`, `CoderOutput`, `CleanerOutput` to `src/agentcrew/nodes/models.py` (per `data-model.md`), with blank-`task` validation. `CoderOutput`/`CleanerOutput` are language-agnostic (no language field — the task may request any language).

**Checkpoint**: Foundation ready — US1 implementation can begin.

---

## Phase 3: User Story 1 - Run the coder→cleaner pipeline (Priority: P1) 🎯 MVP

**Goal**: A developer can run a two-agent pipeline (coder→cleaner) for a task and
see both handoffs, with the graph and the semantic-clean-code cleaner verified
offline. It is **language-agnostic** (the task may request any language); the
coder emits code in that language and the cleaner applies generic clean-code
heuristics. Formatting is deferred to Black/ruff (Python-only), outside the
cleaner (FR-005).

**Independent Test**: `uv run pytest` passes offline (mocked node outputs verify
coder-before-cleaner ordering); real LLM calls opt-in via `integration`/`live`.

### Tests for User Story 1 (TDD — write FIRST, ensure they FAIL before implementation) ⚠️

^- [X] T004 [P] [US1] Unit test (fails first, TDD): `build_coder_node()` wires `task` → `coder_output` with a STUBBED model (no network, so a non-Python task is trivial to stub) — in `tests/unit/test_coder.py` (precedes T007 impl)
^- [X] T005 [P] [US1] Unit test (fails first, TDD): `build_cleaner_node()` applies semantic rules with a stubbed LLM and **fails gracefully to `coder_output` on model error** — in `tests/unit/test_cleaner.py` (precedes T008 impl)
^- [X] T006 [P] [US1] Contract test (offline; mark `@pytest.mark.contract`): the graph runs `coder` before `cleaner` and produces `coder_output` then `cleaner_output` (mocked nodes, no network; also assert blank-task rejection) — in `tests/contract/test_coder_cleaner_graph.py`

### Implementation for User Story 1

^- [X] T007 [US1] Implement `build_coder_node()` returning a LangGraph node (LLM-backed via `build_llm_node`/provider infra; **language-agnostic** — build the prompt from the task without assuming a language → produces `coder_output`) — in `src/agentcrew/agents/coder.py` (after failing T004)
^- [X] T008 [US1] Implement `build_cleaner_node()` applying **generic semantic clean code standards** via LLM (opt-in; **language-agnostic**; produces `cleaner_output`; fails gracefully to `coder_output` on model error). Formatting is **out of scope** here — verify `ruff format`/Black is NOT invoked by the cleaner — in `src/agentcrew/agents/cleaner.py` (after failing T005)
^- [X] T009 [US1] Implement `build_coder_cleaner_graph()` (`StateGraph`: START → coder → cleaner → END) composing T007+T008 — in `src/agentcrew/graphs/coder_cleaner.py`

**Checkpoint**: US1 fully functional and testable independently — the MVP.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: CLI, docs, validation

^- [X] T010 Implement CLI `main()` composing the built graph (text/JSON output, exit codes `0`/`1`/`4`, clear missing-key hint). Pin the error mapping: a node that RAISES maps to `TaskState.error` + exit `4`; the cleaner's graceful fallback (returns `coder_output`) is NOT an error → exit `0` — in `src/agentcrew/coder_cli.py`
^- [X] T011 [P] Add console-script entry point `agentcrew-code = "agentcrew.coder_cli:main"` under `[project.scripts]` in `pyproject.toml`; `uv sync`/`uv build` succeed (constitution Principle II)
^- [X] T012 [P] Contract test for the `agentcrew-code` CLI (composes graph with mocks; usage error exit `1`; failure exit `4`) — in `tests/contract/test_coder_cli.py`
^- [X] T013 Run full validation and confirm green: `uv run ruff check .` and `uv run pytest` (unit + contract) per `quickstart.md`
^- [X] T014 [P] Add `agentcrew-code` usage + pipeline description to `README.md` and document OpenRouter/OpenCode provider setup (reuse `.env.example` guidance); note the pipeline is language-agnostic
^- [X] T015 [P] Add an opt-in integration test (marker `integration`/`live`) exercising a real LLM coder→cleaner run (use a non-Python task to demonstrate language-agnostic behavior) in `tests/integration/test_coder_cleaner.py`, and ASSERT (with LangSmith enabled) that the trace surfaces the graph and the `coder`/`cleaner` nodes (closes FR-007/SC-004 coverage)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS US1
- **User Story 1 (Phase 3)**: Depends on Foundational (T003)
- **Polish (Final Phase)**: Depends on US1 complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational; no dependencies on other stories (only story)

### Within the User Story

- Tests (T004, T005, T006) MUST be written and FAIL before the corresponding
  implementation (TDD)
- Data model (T003) before US1 tests
- Coder impl (T007) and cleaner impl (T008) before the graph (T009); each after
  its failing unit test (T004 → T007, T005 → T008)

### Parallel Opportunities

- Setup: T002 [P]; tests: T004, T005, T006, T012 [P] can run in parallel
- Node implementations T007 and T008 are [P] (different files) once T003 exists
  and their unit tests fail/pass; T009 depends on both

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003 model, CRITICAL)
3. Write failing tests (T004, T005, T006) — verify they FAIL
4. Implement coder node (T007), cleaner node (T008), graph (T009) — verify tests PASS
5. **STOP and VALIDATE**: T013 — run `ruff` + `pytest` per quickstart
6. Polish: CLI (T010–T012), docs (T014), integration (T015)

### Incremental Delivery

Deliver the offline-testable graph (handoff with mocked node outputs) first and
independently validate it; add the LLM-backed coder and semantic-clean-code
cleaner as the opt-in layer behind the same graph interface.

---

## Notes

- [P] tasks = different files, no dependencies
- [US1] label maps tasks to the only user story for traceability
- Commit after each task or logical group
- Stop at the Phase 3 checkpoint to validate the MVP independently
- Avoid: vague tasks, cross-story dependencies, same-file conflicts
- Keep `.github/workflows/ci.yml.disabled` disabled unless explicitly asked
- LangSmith tracing is an existing opt-in surface (`LANGSMITH_*`), not reworked here
- Pipeline is **language-agnostic** (Session 2026-08-31 clarification): coder
  emits whatever language the task asks; cleaner applies generic clean-code
  heuristics; formatting stays only in the repo's Python Black/ruff tooling