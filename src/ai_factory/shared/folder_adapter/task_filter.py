"""Completed-task filtering & no-op detection (002-folder-dev-run, T055–T059).

By default completed tasks (``- [x] T###``) are skipped (FR-014a). ``--force``
overrides the skip and re-runs them. When nothing remains to run, the run is a
**no-op**: no pipeline executes and delivery exits 0 (idempotent re-run).
Purely deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ai_factory.shared.folder_adapter.selector import TaskSelector


@dataclass(frozen=True)
class PrerequisiteWarning:
    """A selected task depends on an earlier, uncompleted task."""

    task_id: str
    prerequisite_id: str


@dataclass(frozen=True)
class SkipWarning:
    """A task skipped/pruned because it is already complete (FR-014d)."""

    task_id: str
    reason: str


@dataclass(frozen=True)
class FilterResult:
    """Tasks that will execute after filtering."""

    subtasks: list  # noqa: ANN001 - TechnicalSubtask
    pruned_completed: list[str] = field(default_factory=list)
    prerequisite_warnings: list[PrerequisiteWarning] = field(default_factory=list)
    skip_warnings: list[SkipWarning] = field(default_factory=list)
    noop: bool = False


def _order_index(subtasks) -> dict[str, int]:  # noqa: ANN001
    return {s.source_task_id: i for i, s in enumerate(subtasks)}


def filter_subtasks(
    subtasks,
    *,
    selector: TaskSelector | None = None,
    force: bool = False,
) -> FilterResult:
    """Apply selector + completed-skip filtering.

    Default behavior (no selector, no ``force``): run only the uncompleted
    tasks. ``force=True`` runs everything (including already-completed). When a
    selector is given, only selected IDs are candidates (post completed-skip
    unless forced). When a selector omits an earlier uncompleted task, that task
    is surfaced as a non-blocking prerequisite warning (FR-014c). Completed
    tasks that are skipped/pruned are surfaced as non-blocking skip warnings
    (FR-014d) unless ``--force`` is given.
    """
    pruned_completed = [s.source_task_id for s in subtasks if s.completed]
    # FR-014d: emit a non-blocking skip warning for every completed task that
    # will NOT run (default skip / selector prune), but never under --force.
    skip_warnings: list[SkipWarning] = []

    # Determine the pool: default excludes completed; force includes all.
    pool = subtasks if force else [s for s in subtasks if not s.completed]

    if selector is not None:
        pool = [s for s in pool if selector.includes(s.source_task_id)]

        if not force:
            pruned = [
                s.source_task_id
                for s in subtasks
                if selector.includes(s.source_task_id) and s.completed
            ]
            pruned_completed = sorted(set(pruned_completed) | set(pruned))
            warnings = _prerequisite_warnings(subtasks, pool)
            skip_warnings = [
                SkipWarning(task_id=t, reason="already complete")
                for t in pruned or _default_skipped(subtasks)
            ]
        else:
            warnings: list[PrerequisiteWarning] = []
    else:
        warnings = []
        if not force:
            skip_warnings = [
                SkipWarning(task_id=t, reason="already complete")
                for t in _default_skipped(subtasks)
            ]

    noop = not pool
    return FilterResult(
        subtasks=pool,
        pruned_completed=pruned_completed,
        prerequisite_warnings=warnings,
        skip_warnings=skip_warnings,
        noop=noop,
    )


def _prerequisite_warnings(
    subtasks,
    selected_subtasks,
) -> list[PrerequisiteWarning]:
    """Non-blocking warnings for uncompleted tasks before a selected scope (FR-014c)."""
    order = _order_index(subtasks)
    selected_ids = {s.source_task_id for s in selected_subtasks}
    warnings: list[PrerequisiteWarning] = []
    for task in subtasks:
        if task.completed or task.source_task_id in selected_ids:
            continue
        # Is this uncompleted task a dependency of a selected task (earlier in order)?
        for sel in selected_subtasks:
            if order[task.source_task_id] < order[sel.source_task_id]:
                warnings.append(
                    PrerequisiteWarning(
                        task_id=sel.source_task_id,
                        prerequisite_id=task.source_task_id,
                    )
                )
    # Deduplicate (a,b) pairs.
    unique: list[PrerequisiteWarning] = []
    seen: set[tuple[str, str]] = set()
    for w in warnings:
        key = (w.task_id, w.prerequisite_id)
        if key not in seen:
            seen.add(key)
            unique.append(w)
    return unique


def _default_skipped(subtasks) -> list[str]:  # noqa: ANN001
    """All already-completed task ids dropped by the default idempotent skip."""
    return [s.source_task_id for s in subtasks if s.completed]


__all__ = [
    "FilterResult",
    "PrerequisiteWarning",
    "SkipWarning",
    "filter_subtasks",
]
