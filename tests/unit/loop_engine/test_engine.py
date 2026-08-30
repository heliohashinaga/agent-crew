"""Unit tests for the ``loop_engine`` core control loop (US1, T030-T032)."""

from __future__ import annotations

import pytest

from ai_factory.loop_engine.engine import run_loop
from ai_factory.loop_engine.models import LoopConfig, LoopStatus, RepairContext
from tests.unit.loop_engine.fakes import FakeActor, FakeGate


def _cfg(
    actor: object, gate: object, max_iterations: int, run_id: str = "run"
) -> LoopConfig:
    return LoopConfig(
        actor=actor, gate=gate, max_iterations=max_iterations, run_id=run_id
    )


def test_pass_on_first_iteration() -> None:
    actor = FakeActor()
    gate = FakeGate(pass_calls=[0])
    result = run_loop(_cfg(actor, gate, max_iterations=5))
    assert result.status == LoopStatus.PASSED
    assert result.iterations == 1  # US1 AS-1
    assert result.artifact_refs == ["artifact"]


def test_fail_k_then_pass_gives_k_plus_1_iterations() -> None:
    actor = FakeActor()
    gate = FakeGate(pass_calls=[3])  # fails calls 0..2, passes on 3
    result = run_loop(_cfg(actor, gate, max_iterations=10))
    assert result.status == LoopStatus.PASSED
    assert result.iterations == 4  # US1 AS-2: k=3 fails then pass


def test_failed_iterations_receive_previous_failure_context() -> None:
    actor = FakeActor(check_repair=True)
    gate = FakeGate(pass_calls=[2])  # fails 0,1 then passes 2
    run_loop(_cfg(actor, gate, max_iterations=10))

    # actor.calls[1] and [2] are repair calls after a prior failure
    for call in actor.calls[1:3]:
        assert call.prior_failed is True
        assert isinstance(call, RepairContext)


def test_never_pass_stops_at_max_iterations_exhausted() -> None:
    actor = FakeActor()
    gate = FakeGate(never_pass=True)
    result = run_loop(_cfg(actor, gate, max_iterations=5))
    assert result.status == LoopStatus.EXHAUSTED
    assert result.iterations <= 5  # US1 AS-3 / SC-002: never unbounded
    assert result.escalation is not None


def test_no_self_grading_actor_claim_ignored() -> None:
    # actor ALWAYS claims success, but the gate never passes -> NOT `passed`
    actor = FakeActor(always_success=True)
    gate = FakeGate(never_pass=True, reasons="gate says no")
    result = run_loop(_cfg(actor, gate, max_iterations=3))
    assert result.status == LoopStatus.EXHAUSTED  # US2 AS-1 / SC-003
    # held-back reason is the gate's, not the actor's
    assert result.escalation is not None
    assert "gate says no" in result.escalation.gate_verdicts[0].reasons()


def test_gate_unavailable_raises_never_silent_pass() -> None:
    from ai_factory.loop_engine.gate import LoopGateError

    actor = FakeActor()
    gate = FakeGate(raise_always=True)
    with pytest.raises(LoopGateError):
        run_loop(_cfg(actor, gate, max_iterations=3))  # US2 AS-3


def test_bounded_reasons_forwarded_to_next_actor() -> None:
    actor = FakeActor(check_repair=True)
    gate = FakeGate(pass_calls=[1], reasons="lint_fail;contract_fail")
    run_loop(_cfg(actor, gate, max_iterations=5))
    repair_call = actor.calls[1]
    assert repair_call.prior_failed is True
    reasons = repair_call.prior_verdict.reasons() if repair_call.prior_verdict else []
    assert "lint_fail;contract_fail" in reasons


def test_empty_config_raises() -> None:
    from ai_factory.loop_engine.engine import LoopConfigError

    with pytest.raises((LoopConfigError, ValueError)):
        run_loop(_cfg(None, None, max_iterations=3))