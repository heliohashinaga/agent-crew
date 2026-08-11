"""Unit tests for tasks.md parsing & path normalization (T008–T011, FR-008/SC-003)."""

from pathlib import Path

import pytest

from ai_factory.shared.folder_adapter.parse_tasks import parse_tasks

FULL_TASKS = """# User Session Timeout — Tasks

## Phase 1: Setup

1. [ ] T001 Create the session table migration.
   - File: `src/ai_factory/sessions/migrations/1_session_table.py`

2. [ ] T002 Add the session model.
   - File: `src/ai_factory/sessions/models.py`

## Phase 2: Core

3. [ ] T003 Implement the expiry reaper job.
   - File: `src/ai_factory/sessions/reaper.py`

4. [ ] T004 Add the session refresh middleware. [P]
   - File: `src/ai_factory/web/session_middleware.py`

5. [ ] T005 Add the admin active-sessions view. [P]
   - File: `src/ai_factory/admin/sessions_view.py`
"""


@pytest.fixture
def fixtures() -> Path:
    return Path(__file__).resolve().parents[3] / "fixtures" / "specs"


def test_preserves_order(fixtures: Path) -> None:
    content = (fixtures / "full" / "tasks.md").read_text()
    result = parse_tasks(content)
    ids = [t.source_task_id for t in result.subtasks]
    assert ids == ["T001", "T002", "T003", "T004", "T005", "T006", "T007"]
    assert [t.source_task_id for t in result.subtasks] == ids


def test_maps_files_to_subtasks(fixtures: Path) -> None:
    result = parse_tasks((fixtures / "full" / "tasks.md").read_text())
    t003 = next(t for t in result.subtasks if t.source_task_id == "T003")
    assert t003.files == ["src/ai_factory/sessions/reaper.py"]


def test_classifies_impl_versus_test(fixtures: Path) -> None:
    result = parse_tasks(FULL_TASKS)
    by_id = {t.source_task_id: t for t in result.subtasks}
    assert by_id["T001"].source_task_type == "implement"
    assert by_id["T002"].source_task_type == "implement"


def test_absolute_path_dropped_with_warning(fixtures: Path) -> None:
    content = (fixtures / "absolute" / "tasks.md").read_text()
    result = parse_tasks(content)
    warnings = result.warnings
    assert any("Absolute/host path" in w for w in warnings)
    # Out-of-repo absolute Windows path also dropped.
    assert any("Absolute/host path" in w and "C:" in w for w in warnings)
    # Remaining in-repo paths are preserved.
    kept = [f for sub in result.subtasks for f in sub.files]
    assert any(f.endswith("json_formatter.py") for f in kept)


SHARED_TASKS = """# X — Tasks

1. [ ] T001 First impl.
   - File: `src/a.py`

2. [ ] T002 Second impl touching the same file. [P]
   - File: `src/a.py`
"""


TEST_TASKS = """# T — Tasks

1. [ ] T001 Write unit tests for the reaper.
   - File: `tests/unit/reaper_test.py`
"""


def test_test_typed_subtask_classified() -> None:
    # FR-013/SC-010: a test-typed task is carried with source_task_type "test"
    # and is handled by the test capability, not the code-worker.
    result = parse_tasks(TEST_TASKS)
    assert result.subtasks[0].source_task_type == "test"


def test_shared_file_conflict_detected() -> None:
    result = parse_tasks(SHARED_TASKS)
    assert result.conflicts
    c = result.conflicts[0]
    assert c.source_task_id_a == "T001"
    assert c.source_task_id_b == "T002"

