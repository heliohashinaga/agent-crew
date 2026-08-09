"""Soft budget tracking (T069/T070, FR-019).

Budgets are SOFT: crossing a threshold raises a warning (and surfaces the
overspend flag for telemetry per FR-016) but NEVER stops the run
(FR-019). Hard-stop behaviour belongs to human/retry decisions, not budgets.
"""

from __future__ import annotations

from ai_factory.dev_workflow.models import Budget


class BudgetTracker:
    """Tracks spend against a soft :class:`Budget`; warns, never blocks."""

    def __init__(self, budget: Budget) -> None:
        self.budget = budget
        self.spent_cost = 0.0
        self.spent_tokens = 0
        self.spent_time = 0.0

    def charge(self, cost: float = 0.0, tokens: int = 0, time: float = 0.0) -> None:
        """Record spend. Crossing a limit warns; execution continues (FR-019)."""
        self.spent_cost += cost
        self.spent_tokens += int(tokens)
        self.spent_time += time

    def warning(self) -> bool:
        """True when any set budget dimension is exceeded (soft warning)."""
        b = self.budget
        return bool(
            (b.cost_usd is not None and self.spent_cost > b.cost_usd)
            or (b.tokens is not None and self.spent_tokens > b.tokens)
            or (b.time is not None and self.spent_time > b.time)
        )

    def overspent(self) -> bool:
        return self.warning()

    @property
    def overspend_flag(self) -> bool:
        """The boolean carried into telemetry as ``TelemetryRecord.overspend``."""
        return self.warning()


__all__ = ["BudgetTracker"]
