"""Unit tests for completed-task filtering & no-op (T055–T059, FR-014a)."""

from ai_factory.dev_workflow.technical_planner.planner import TechnicalSubtask
from ai_factory.shared.folder_adapter.selector import resolve_selector
from ai_factory.shared.folder_adapter.task_filter import filter_subtasks


def _subs() -> list[TechnicalSubtask]:
    return [
        TechnicalSubtask(
            title=f"t{i}",
            description="",
            source_task_id=tid,
            files=[f"f{i}.py"],
            completed=done,
        )
        for i, (tid, done) in enumerate(
            [("T001", True), ("T002", False), ("T003", False)]
        )
    ]


def test_skips_completed_by_default() -> None:
    result = filter_subtasks(_subs())
    ids = [s.source_task_id for s in result.subtasks]
    assert ids == ["T002", "T003"]
    assert result.pruned_completed == ["T001"]


def test_force_runs_everything() -> None:
    result = filter_subtasks(_subs(), force=True)
    assert len(result.subtasks) == 3


def test_noop_when_all_complete() -> None:
    all_done = [
        TechnicalSubtask(
            title="t", description="", source_task_id="T001", completed=True
        )
    ]
    result = filter_subtasks(all_done)
    assert result.noop is True
    assert result.subtasks == []


def test_selector_filters() -> None:
    sel = resolve_selector("T003", ["T001", "T002", "T003"])
    result = filter_subtasks(_subs(), selector=sel)
    assert [s.source_task_id for s in result.subtasks] == ["T003"]


def test_prerequisite_warning_nonblocking() -> None:
    # T002 is pending and ordered before the selected T003.
    sel = resolve_selector("T003", ["T001", "T002", "T003"])
    result = filter_subtasks(_subs(), selector=sel)
    assert any(
        w.prerequisite_id == "T002" and w.task_id == "T003"
        for w in result.prerequisite_warnings
    )
    # Non-blocking: the selected scope is still returned.
    assert [s.source_task_id for s in result.subtasks] == ["T003"]


def test_skip_warning_for_already_complete_default() -> None:
    # T001 is completed; the default idempotent skip emits a warning (FR-014d).
    result = filter_subtasks(_subs())
    assert any(
        w.task_id == "T001" and w.reason == "already complete"
        for w in result.skip_warnings
    )


def test_skip_warning_for_selector_prune() -> None:
    # Selecting an already-complete task prunes it with a warning.
    sel = resolve_selector("T001", ["T001", "T002", "T003"])
    result = filter_subtasks(_subs(), selector=sel)
    assert any(w.task_id == "T001" for w in result.skip_warnings)


def test_force_suppresses_skip_warning() -> None:
    # --force re-runs completed tasks; no skip warning (FR-014d).
    result = filter_subtasks(_subs(), force=True)
    assert result.skip_warnings == []
    assert len(result.subtasks) == 3
