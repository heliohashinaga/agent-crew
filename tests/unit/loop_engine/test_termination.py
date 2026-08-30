"""Unit tests for termination/budget/ratchet + escalation (US3, T050-T052, T053)."""

from __future__ import annotations

import pytest

from ai_factory.loop_engine.budget import BudgetTracker, StallRatchet
from ai_factory.loop_engine.engine import run_loop
from ai_factory.loop_engine.models import (
    ActorOutput,
    BudgetDelta,
    LoopBudget,
    LoopConfig,
    LoopStatus,
    RatchetConfig,
)
from tests.unit.loop_engine.fakes import FakeActor, FakeGate


def _cfg(actor, gate, max_iterations, run_id="run", budget=None, ratchet=None):
    return LoopConfig(
        actor=actor,
        gate=gate,
        max_iterations=max_iterations,
        run_id=run_id,
        budget=budget,
        ratchet=ratchet,
    )


def test_budget_exceeded_stops_exhausted() -> None:
    # low token budget + a gate that consumes tokens and keeps failing.
    actor = FakeActor()
    gate = FakeGate(never_pass=True, consumed=BudgetDelta(tokens=3))
    result = run_loop(
        _cfg(actor, gate, max_iterations=20, budget=LoopBudget(max_tokens=10))
    )
    assert result.status == LoopStatus.EXHAUSTED
    assert result.iterations < 20  # stopped early on budget (US3 AS-2)
    assert result.escalation is not None
    assert result.escalation.budget_consumed.tokens <= 13  # atomic: current may finish


def test_budget_tracker_accounting() -> None:
    t = BudgetTracker(LoopBudget(max_tokens=10, max_seconds=5.0, max_cost_usd=0.5))
    t.add(BudgetDelta(tokens=4, latency_s=1.0, cost_usd=0.1))
    assert t.exceeded() is False
    t.add(BudgetDelta(tokens=6))
    assert t.exceeded() is True


def test_no_budget_never_exceeds() -> None:
    t = BudgetTracker(None)
    t.add(BudgetDelta(tokens=9999))
    assert t.exceeded() is False


def test_stall_ratchet_terminates_stalled() -> None:
    # FakeActor yields the SAME artifact ref each time -> no progress -> stalled
    actor = FakeActor()
    gate = FakeGate(never_pass=True)
    result = run_loop(
        _cfg(actor, gate, max_iterations=10, ratchet=RatchetConfig(max_stall=3))
    )
    assert result.status == LoopStatus.STALLED  # Q5=A: distinct stalled
    assert result.escalation is not None
    assert result.iterations <= 10


def test_stall_ratchet_progress_resets() -> None:
    r = StallRatchet(RatchetConfig(max_stall=2))
    r.record(ActorOutput(artifact_refs=["a"]))
    r.record(ActorOutput(artifact_refs=["a"]))  # no progress (stall 1)
    assert r.stalled() is False
    r.record(ActorOutput(artifact_refs=["b"]))  # progress -> reset
    assert r.stalled() is False
    r.record(ActorOutput(artifact_refs=["b"]))  # stall 1
    r.record(ActorOutput(artifact_refs=["b"]))  # stall 2 -> stalled
    assert r.stalled() is True


def test_default_max_iterations_5_exact() -> None:
    actor = FakeActor()
    gate = FakeGate(never_pass=True)
    result = run_loop(_cfg(actor, gate, max_iterations=5))
    assert result.status == LoopStatus.EXHAUSTED
    assert result.iterations == 5  # never unbounded (US1 AS-3 / SC-002)


def test_escalation_has_field_names() -> None:
    actor = FakeActor()
    gate = FakeGate(never_pass=True)
    result = run_loop(_cfg(actor, gate, max_iterations=3))
    esc = result.escalation
    assert esc is not None
    assert esc.status == LoopStatus.EXHAUSTED
    assert esc.partial_artifacts == ["artifact"]


def test_actor_exception_is_budget_bounded_retry_not_crash() -> None:
    # T053/Q6=A: raising actor -> recorded failed, retried via budget, no crash,
    # and does NOT consume a max_iterations slot.
    actor = FakeActor(raise_on=[0, 1, 2], artifact_refs=["a"])
    gate = FakeGate(pass_calls=[0])
    result = run_loop(_cfg(actor, gate, max_iterations=5))
    # The first 3 calls raised; the 4th (index 3) succeeds and the gate passes.
    assert result.status == LoopStatus.PASSED
    assert len(actor.calls) >= 4


def test_actor_exception_exhaustion_when_budget_runs_out() -> None:
    actor = FakeActor(raise_on=list(range(100)), artifact_refs=["a"])
    gate = FakeGate(never_pass=True)
    result = run_loop(
        _cfg(actor, gate, max_iterations=50, budget=LoopBudget(max_tokens=5))
    )
    assert result.status == LoopStatus.EXHAUSTED
    # every retry burned 1 token; with max_tokens=5 it stops by 5 retries
    assert result.budget.tokens <= 5


def test_empty_config_raises_config_error() -> None:
    from ai_factory.loop_engine.engine import LoopConfigError

    with pytest.raises(LoopConfigError):
        run_loop(
            LoopConfig(actor=None, gate=object(), max_iterations=3, run_id="r")
        )