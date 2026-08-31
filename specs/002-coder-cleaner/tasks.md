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

- [ ] T001 Add explicit `langgraph>=1.2.10` (and `langgraph-checkpoint>=4.2.0` for InMemorySaver in dev/tests) to `pyproject.toml` deps; `uv lock`/`uv sync` resolves cleanly (FR-009)
- [ ] T002 [P] Create `src/agentcrew/agents/__init__.py` and `src/agentcrew/graphs/__init__.py` package inits

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared state that MUST exist before US1

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Add `TaskState`, `CoderOutput`, `CleanerOutput` to `src/agentcrew/nodes/models.py` (per `data-model.md`), with blank-`task` validation

**Checkpoint**: Foundation ready — US1 implementation can begin.

---

## Phase 3: User Story 1 - Run the coder→cleaner pipeline (Priority: P1) 🎯 MVP

**Goal**: A developer can run a two-agent pipeline (coder→cleaner) for a task and
see both handoffs, with the graph and the semantic-clean-code cleaner verified
offline (formatting is deferred to Black/ruff, outside the cleaner — FR-005).

**Independent Test**: `uv run pytest` passes offline (mocked node outputs verify
coder-before-cleaner ordering); real LLM calls opt-in via `integration`/`live`.

### Tests for User Story 1 (TDD — write FIRST, ensure they FAIL before implementation) ⚠️

- [ ] T005 [P] [US1] Contract test (offline; mark `@pytest.mark.contract`): the graph runs `coder` before `cleaner` and produces `coder_output` then `cleaner_output` (mocked nodes, no network; also assert blank-task rejection) — in `tests/contract/test_coder_cleaner_graph.py`

### Implementation for User Story 1

- [ ] T006 [P] [US1] Implement `build_coder_node()` returning a LangGraph node (LLM-backed via `build_llm_node`/provider infra → produces `coder_output`) — in `src/agentcrew/agents/coder.py`
- [ ] T007 [US1] Implement `build_cleaner_node()` applying **semantic clean code standards** via LLM (opt-in; produces `cleaner_output`; fails gracefully to `coder_output` on model error). Formatting is **out of scope** here — verify `ruff format`/Black is NOT invoked by the cleaner — in `src/agentcrew/agents/cleaner.py`
- [ ] T008 [US1] Implement `build_coder_cleaner_graph()` (`StateGraph`: START → coder → cleaner → END) composing T006+T007 — in `src/agentcrew/graphs/coder_cleaner.py`

**Checkpoint**: US1 fully functional and testable independently — the MVP.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: CLI, docs, validation

- [ ] T009 [US1] Implement CLI `main()` composing the built graph (text/JSON output, exit codes `0`/`1`/`4`, clear missing-key hint) — in `src/agentcrew/coder_cli.py`
- [ ] T010 [P] Add console-script entry point `agentcrew-code = "agentcrew.coder_cli:main"` under `[project.scripts]` in `pyproject.toml`; `uv sync`/`uv build` succeed (constitution Principle II)
- [ ] T011 [P] [US1] Contract test for the `agentcrew-code` CLI (composes graph with mocks; usage error exit `1`; failure exit `4`) — in `tests/contract/test_coder_cli.py`
- [ ] T012 Run full validation and confirm green: `uv run ruff check .` and `uv run pytest` (unit + contract) per `quickstart.md`
- [ ] T013 [P] Add `agentcrew-code` usage + pipeline description to `README.md` and document OpenRouter/OpenCode provider setup (reuse `.env.example` guidance)
- [ ] T014 [P] Add an opt-in integration test (marker `integration`/`live`) exercising a real LLM coder→cleaner run in `tests/integration/test_coder_cleaner.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS US1
- **User Story 1 (Phase 3)**: Depends on Foundational (T003, T004)
- **Polish (Final Phase)**: Depends on US1 complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational; no dependencies on other stories (only story)

### Within the User Story

- Contract test (T005) MUST be written and FAIL before implementation (TDD)
- Data model (T003) before US1 tests
- Test before the node implementations (T006–T007)
- Cleaner node (T007) and coder node (T006) before the graph (T008)

### Parallel Opportunities

- T002, T005, T006, T011, T012, T014, T015 marked [P] can run in parallel
- T007 and T008 are parallelizable once the model (T003) and core (T004) exist

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003 model, CRITICAL)
3. Write failing tests (T005–T006) — verify they FAIL
4. Implement coder node (T006), cleaner node (T007), graph (T008) — verify tests PASS
5. **STOP and VALIDATE**: T013 — run `ruff` + `pytest` per quickstart
6. Polish: CLI (T009–T011), docs (T013), integration (T014)

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
- LangSmith tracing is an existing opt-in surface (`LANGSMITH_*`), not reworked here.