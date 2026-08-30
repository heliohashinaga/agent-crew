"""Concise human escalation summary for ``loop_engine`` (T052, FR-004)."""

from __future__ import annotations

from ai_factory.loop_engine.models import (
    BudgetDelta,
    EscalationSummary,
    GateVerdict,
    LoopStatus,
)


def build_escalation(
    status: LoopStatus,
    iterations: int,
    verdicts: list[GateVerdict],
    budget: BudgetDelta,
    partial_artifacts: list[str] | None = None,
) -> EscalationSummary:
    """Build a concise, bounded escalation (FR-004, Q3=A)."""
    return EscalationSummary(
        status=status,
        iterations=iterations,
        gate_verdicts=list(verdicts),
        budget_consumed=budget,
        partial_artifacts=list(partial_artifacts or []),
    )


__all__ = ["build_escalation"]