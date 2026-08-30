---

description: "Task list template for feature implementation"
---

# Tasks: LangChain Foundation — Hello-World Node

**Input**: Design documents from `/specs/001-langchain-hello-node/`

**Prerequisites**: plan.md, spec.md (US1), research.md, data-model.md, contracts/hello-world-node-cli.md

**Tests**: The project constitution (`.specify/memory/constitution.md`; runtime guidance in `AGENTS.md`) mandates **TDD (non-negotiable)**, including automated tests for the library↔CLI contract seam (Principle IV) — so test tasks are required here and MUST be written to fail before implementing.

**Organization**: Grouped by user story. This feature has one user story (US1, P1, MVP).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1)
- Include exact file paths in descriptions

## Path Conventions

Single Python project: `src/`, `tests/` at repository root (package `agentcrew`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Verify `langchain-core>=1.0` is declared in `pyproject.toml` and that `uv lock`/`uv sync` resolves cleanly
- [X] T002 [P] Create `src/agentcrew/nodes/__init__.py` package init for the nodes library
- [X] T003 [P] Create empty test package inits if missing: `tests/unit/__init__.py`, `tests/contract/__init__.py`, and `tests/integration/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before US1 implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create the `HelloWorldNodeResult` data model (Pydantic; fields `input: str`, `greeting: str`, with empty-input validation) in `src/agentcrew/nodes/models.py`

**Checkpoint**: Foundation ready — US1 implementation can begin.

---

## Phase 3: User Story 1 - Run the base and see a hello-world output (Priority: P1) 🎯 MVP

**Goal**: A developer can install, run a single offline/deterministic hello-world node, and see a greeting (proving the LangChain base works end-to-end).

**Independent Test**: `uv run python -m agentcrew.cli hello "world"` prints `Hello, world!` (JSON variant returns `{"input": "world", "greeting": "Hello, world!"}`), and `uv run pytest` passes **without network or credentials**.

### Tests for User Story 1 (TDD — write FIRST, ensure they FAIL before implementation) ⚠️

- [X] T005 [P] [US1] Unit test: node returns deterministic `{"input": "<text>", "greeting": "Hello, <text>!"}` for identical input, strips surrounding whitespace, and the `HelloWorldNodeResult` model rejects empty and whitespace-only input (model-level validation) — in `tests/unit/test_hello_world.py`
- [X] T006 [P] [US1] Contract test (offline; mark `@pytest.mark.contract` so it runs under plain `uv run pytest` and is not excluded by the default `-m 'not integration'` filter): CLI returns `Hello, world!` on stdout with exit code `0`; returns exit code `1` on empty/missing/whitespace-only arg; returns exit code `4` on a forced invocation failure — in `tests/contract/test_hello_world_cli.py`

### Implementation for User Story 1

- [X] T007 [P] [US1] Implement `build_hello_world_node()` returning a `langchain_core` `Runnable` (via `RunnableLambda`) that validates input against `HelloWorldNodeResult` — in `src/agentcrew/nodes/hello_world.py` (depends on T004)
- [X] T008 [US1] Implement CLI `main()` composing the library node: human-readable default output, `--format json` output, input validation, and exit codes `0`/`1`/`4` — in `src/agentcrew/cli.py` (depends on T007)

**Checkpoint**: US1 fully functional and testable independently — this is the MVP.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting the whole base

- [X] T009 Run full validation and confirm green: `uv run ruff check .` (no issues) and `uv run pytest` (all pass, including the T006 contract test which is not excluded by the default `-m 'not integration'` filter) per `specs/001-langchain-hello-node/quickstart.md`
- [X] T010 [P] Add the run/verify commands and repo short description reference to `README.md` (keep the CI badge; CI stays disabled as `.github/workflows/ci.yml.disabled` during bootstrap)
- [X] T011 [P] Add the console-script entry point `agentcrew-hello = "agentcrew.cli:main"` under `[project.scripts]` in `pyproject.toml` and verify `uv sync`/`uv build` succeed with it

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS US1
- **User Story 1 (Phase 3)**: Depends on Foundational (T004)
- **Polish (Final Phase)**: Depends on US1 complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational; no dependencies on other stories (only story)

### Within the User Story

- Tests (T005–T006) MUST be written and FAIL before implementation (TDD)
- Foundation/data model (T004) before tests
- Tests before the node implementation (T007)
- Node library (T007) before CLI (T008)

### Parallel Opportunities

- Setup tasks T002, T003 marked [P] can run in parallel
- Tests T005, T006 marked [P] can run in parallel
- T007 is parallelizable with the tests once the model exists; T008 depends on T007

---

## Parallel Example: User Story 1

```bash
# Write both tests in parallel (TDD — they must fail first):
Task: "Unit test for hello-world node in tests/unit/test_hello_world.py"                  # T005
Task: "Contract test for hello-world CLI in tests/contract/test_hello_world_cli.py" # T006

# After tests fail and model (T004) exists, implement node + CLI:
Task: "Implement build_hello_world_node() in src/agentcrew/nodes/hello_world.py"      # T007
Task: "Implement CLI main() in src/agentcrew/cli.py"                                  # T008
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational — data model (T004, CRITICAL)
3. Write failing tests (T005–T006) — verify they FAIL
4. Implement node (T007) then CLI (T008) — verify tests PASS
5. **STOP and VALIDATE**: T009 — run `ruff` + `pytest` per quickstart
6. Polish: T010 (README)

### Incremental Delivery

This is a single-story base slice. After US1, future user stories (real multi-node agents, LLM providers) can be added independently as new phases.

---

## Notes

- [P] tasks = different files, no dependencies
- [US1] label maps tasks to the only user story for traceability
- Commit after each task or logical group
- Stop at the Phase 3 checkpoint to validate the MVP independently
- Avoid: vague tasks, cross-story dependencies, same-file conflicts
- CI workflow remains disabled (`.github/workflows/ci.yml.disabled`) until a real test suite is in place — do not re-enable in this feature.
- SC-001 (fresh checkout → output < 2 min) is covered by: `uv sync` in `quickstart.md` (US1-A1) + T009 validation + T010 docs.