"""Assemble a TechnicalPlan from a resolved speckit folder (T014/T015).

Composes :mod:`parse_spec`, :mod:`parse_tasks`, and :mod:`parse_plan` into a
single factory :class:`TechnicalPlan`. The factory identity for traceability is
the folder feature name (not an issued ``spec_version_id``, which is left empty
per FR-011/012). Purely deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ai_factory.dev_workflow.technical_planner.planner import TechnicalPlan
from ai_factory.shared.folder_adapter.parse_plan import degrade_assessment, parse_plan
from ai_factory.shared.folder_adapter.parse_spec import parse_spec
from ai_factory.shared.folder_adapter.parse_tasks import (
    ParseTasksResult,
    SharedFileConflict,
    parse_tasks,
)


@dataclass(frozen=True)
class BuildPlanResult:
    """Plan plus non-fatal diagnostics gathered while building."""

    plan: TechnicalPlan
    conflicts: list[SharedFileConflict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    inferred: tuple[str, ...] = ()


def build_plan(folder: Path, *, repo_root: str = "") -> BuildPlanResult:
    """Build a TechnicalPlan from a resolved speckit folder path."""
    spec_text = (folder / "spec.md").read_text(encoding="utf-8")
    tasks_text = (folder / "tasks.md").read_text(encoding="utf-8")

    events = parse_spec(spec_text)
    tasks: ParseTasksResult = parse_tasks(tasks_text, repo_root=repo_root)

    plan_path = folder / "plan.md"
    if plan_path.is_file():
        plan_events = parse_plan(plan_path.read_text(encoding="utf-8"))
        assessment = plan_events.assessment
        inferred = list(plan_events.inferred)
    else:
        degraded = degrade_assessment()
        assessment = degraded.assessment
        inferred = list(degraded.inferred)

    # Traceability identity derives from the folder feature name (FR-011/012).
    plan = TechnicalPlan(
        spec_version_id=folder.name,
        goal=events.goal,
        assessment=assessment,
        subtasks=tasks.subtasks,
    )

    return BuildPlanResult(
        plan=plan,
        conflicts=list(tasks.conflicts),
        warnings=list(tasks.warnings) + list(inferred),
        inferred=tuple(inferred),
    )


__all__ = ["BuildPlanResult", "build_plan"]
