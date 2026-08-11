"""Unit tests: test-typed subtasks are NOT code-worker work (T036, FR-013/SC-010).
"""

from __future__ import annotations

from pathlib import Path

from ai_factory.dev_workflow.code_worker.worker import _impl_subtasks
from ai_factory.dev_workflow.technical_planner.planner import (
    TechnicalAssessment,
    TechnicalPlan,
    TechnicalSubtask,
)


def _plan() -> TechnicalPlan:
    return TechnicalPlan(
        spec_version_id="sessions",
        goal="Session timeout",
        assessment=TechnicalAssessment(complexity="standard"),
        subtasks=[
            TechnicalSubtask(
                title="Implement the reaper",
                description="core",
                files=["src/ai_factory/sessions/reaper.py"],
                source_task_id="T003",
                source_task_type="implement",
            ),
            TechnicalSubtask(
                title="Unit-test the reaper",
                description="test-only",
                files=["tests/unit/sessions/test_reaper.py"],
                source_task_id="T006",
                source_task_type="test",
            ),
        ],
    )


def test_code_worker_does_not_implement_test_typed_subtask(tmp_path: Path) -> None:
    # Routing gate: the code-worker only implements non-test subtasks.
    impl_subs = _impl_subtasks(_plan())
    ids = {s.source_task_id for s in impl_subs}
    assert "T006" not in ids  # test-typed subtask is NOT routed to the code-worker
    assert "T003" in ids  # implementation subtask is


def test_test_typed_subtask_is_carried(tmp_path: Path) -> None:
    plan = _plan()
    test_subtask = [t for t in plan.subtasks if t.source_task_type == "test"]
    assert test_subtask
    assert test_subtask[0].files == ["tests/unit/sessions/test_reaper.py"]
