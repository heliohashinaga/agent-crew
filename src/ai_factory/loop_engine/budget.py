"""Budget tracker + stall ratchet for ``loop_engine`` (T050-T051, FR-003).

- Tracks tokens/cost/latency across iterations (``BudgetDelta``) and stops
  (``exhausted``) when a configured ``LoopBudget`` dimension is exceeded —
  a **hard stop within ``loop_engine``** (Q7=A, scoped divergence from the
  parent factory's soft-budget).
- Optional stall ratchet: N consecutive no-progress iterations terminate with
  ``stalled`` (Q5=A).
"""

from __future__ import annotations

from ai_factory.loop_engine.models import (
    ActorOutput,
    BudgetDelta,
    LoopBudget,
    RatchetConfig,
)


class BudgetTracker:
    """Accumulates consumed budget and decides termination (FR-003, Q7=A)."""

    def __init__(self, budget: LoopBudget | None = None) -> None:
        self.budget = budget
        self.consumed: BudgetDelta = BudgetDelta()

    def add(self, delta: BudgetDelta) -> None:
        self.consumed.tokens += delta.tokens
        self.consumed.cost_usd += delta.cost_usd
        self.consumed.latency_s += delta.latency_s

    def exceeded(self) -> bool:
        """True when any configured budget dimension is over its ceiling."""
        if self.budget is None:
            return False
        over_tokens = (
            self.budget.max_tokens is not None
            and self.consumed.tokens >= self.budget.max_tokens
        )
        over_cost = (
            self.budget.max_cost_usd is not None
            and self.consumed.cost_usd >= self.budget.max_cost_usd
        )
        over_time = (
            self.budget.max_seconds is not None
            and self.consumed.latency_s >= self.budget.max_seconds
        )
        return over_tokens or over_cost or over_time

    def budget_summary(self) -> BudgetDelta:
        return self.consumed


class StallRatchet:
    """Tracks consecutive no-progress iterations (Q5=A, FR-003)."""

    def __init__(self, config: RatchetConfig | None = None) -> None:
        self.config = config
        self._stall = 0
        self._last_progress: tuple | None = None

    def record(self, actor_out: ActorOutput) -> None:
        if self.config is None:
            return
        key = tuple(getattr(actor_out, self.config.progress_key, ()) or ())
        if key == self._last_progress or key == ():
            self._stall += 1
        else:
            self._stall = 0
            self._last_progress = key

    def stalled(self) -> bool:
        return self.config is not None and self._stall >= self.config.max_stall


__all__ = ["BudgetTracker", "StallRatchet"]