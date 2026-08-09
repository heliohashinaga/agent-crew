"""Tests for the soft budget tracker (T069, FR-019).

Budget is soft: exceeding thresholds raises a WARNING and sets overspend
telemetry — it never hard-stops execution (FR-019).
"""

from __future__ import annotations

from ai_factory.dev_workflow.models import Budget
from ai_factory.dev_workflow.orchestrator.budget import BudgetTracker


def test_under_budget_no_warning() -> None:
    tracker = BudgetTracker(Budget(cost_usd=1.0, tokens=1000, time=60))
    tracker.charge(cost=0.2, tokens=100)
    assert tracker.overspent() is False
    assert tracker.warning() is False


def test_over_cost_is_warning_not_hard_stop() -> None:
    """FR-019: exceeding the budget warns but never raises/aborts."""
    tracker = BudgetTracker(Budget(cost_usd=1.0))
    tracker.charge(cost=1.5, tokens=0)
    assert tracker.overspent() is True
    assert tracker.warning() is True
    # Still usable; the tracker never raises.
    tracker.charge(cost=0.1, tokens=10)


def test_accumulated_spend_tracks() -> None:
    tracker = BudgetTracker(Budget(cost_usd=2.0, tokens=2000))
    tracker.charge(cost=0.5, tokens=500)
    tracker.charge(cost=0.5, tokens=500)
    assert tracker.spent_cost == 1.0
    assert tracker.spent_tokens == 1000


def test_time_soft_warning() -> None:
    tracker = BudgetTracker(Budget(time=10))
    tracker.charge(cost=0.0, tokens=0, time=12)
    assert tracker.warning() is True
    assert tracker.overspent() is True


def test_no_limits_set_never_overspends() -> None:
    tracker = BudgetTracker(Budget())
    tracker.charge(cost=9999, tokens=99999)
    assert tracker.overspent() is False  # unlimited budget


def test_overspend_flag_for_telemetry() -> None:
    """FR-019 → FR-016: overspend is surfaced as a telemetry flag."""
    tracker = BudgetTracker(Budget(cost_usd=1.0))
    tracker.charge(cost=2.0, tokens=0)
    assert tracker.overspend_flag is True
