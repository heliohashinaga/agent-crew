"""Unit tests for tasks.md completion write-back (T016/T017, FR-010)."""

from ai_factory.shared.folder_adapter.mark_completed import mark_task_complete

CONTENT = """# X — Tasks

## Phase 1

1. [ ] T001 First.
   - File: `src/a.py`

2. [ ] T002 Second.
   - File: `src/b.py`
"""


def test_marks_task_done() -> None:
    out = mark_task_complete(CONTENT, "T001", done=True)
    assert out.changed is True
    assert out.matched is True
    assert "[x] T001" in out.content
    assert "[ ] T002" in out.content  # untouched sibling


def test_unmark_task() -> None:
    done = mark_task_complete(CONTENT, "T001", done=True).content
    out = mark_task_complete(done, "t001", done=False)  # case-insensitive
    assert out.matched is True
    assert "[ ] T001" in out.content


def test_missing_task_reports_no_match() -> None:
    out = mark_task_complete(CONTENT, "T999", done=True)
    assert out.matched is False
    assert out.changed is False


def test_already_done_is_noop() -> None:
    done = mark_task_complete(CONTENT, "T001", done=True).content
    out = mark_task_complete(done, "T001", done=True)
    assert out.changed is False
