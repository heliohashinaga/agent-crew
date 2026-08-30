"""Unit tests for ``loop_engine`` data models (Phase 1, T003-T008)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_factory.loop_engine.models import (
    ActorOutput,
    BudgetDelta,
    CheckResult,
    CheckStage,
    EscalationSummary,
    GateVerdict,
    LoopBudget,
    LoopConfig,
    LoopResult,
    LoopStatus,
    RatchetConfig,
    RepairContext,
)


def test_budget_delta_zero_defaults_and_roundtrip() -> None:
    d = BudgetDelta()
    assert d.tokens == 0 and d.cost_usd == 0.0 and d.latency_s == 0.0
    assert BudgetDelta.model_validate_json(d.model_dump_json()) == d


def test_loop_budget_roundtrip() -> None:
    b = LoopBudget(max_tokens=100, max_seconds=5.0, max_cost_usd=0.1)
    assert LoopBudget.model_validate_json(b.model_dump_json()) == b
    assert LoopBudget().max_tokens is None


def test_check_result_defaults_and_roundtrip() -> None:
    c = CheckResult(name="suite_pass")
    assert c.stage == CheckStage.DETERMINISTIC
    assert c.passed is False and c.reasons == [] and c.consumed.tokens == 0
    assert CheckResult.model_validate_json(c.model_dump_json()) == c


def test_check_result_reviewer_stage() -> None:
    c = CheckResult(name="reviewer", stage=CheckStage.REVIEWER, passed=True)
    assert c.stage == CheckStage.REVIEWER


def test_gate_verdict_passed_only_when_all_checks_pass() -> None:
    # all pass -> passed True
    ok = GateVerdict(
        checks=[
            CheckResult(name="a", passed=True),
            CheckResult(name="b", passed=True),
        ]
    )
    assert ok.passed is True
    # one fails -> aggregate passed False (Q2=C)
    mixed = GateVerdict(
        checks=[
            CheckResult(name="a", passed=True),
            CheckResult(name="b", passed=False, reasons=["broke"]),
        ]
    )
    assert mixed.passed is False
    assert GateVerdict.model_validate_json(ok.model_dump_json()) == ok


def test_gate_verdict_reasons_flat_bounded() -> None:
    v = GateVerdict(
        checks=[
            CheckResult(name="a", passed=False, reasons=["r1"]),
            CheckResult(name="b", passed=False, reasons=["r2"]),
            CheckResult(name="c", passed=True),
        ]
    )
    assert v.reasons() == ["r1", "r2"]


def test_actor_output_roundtrip() -> None:
    a = ActorOutput(status=True, artifact_refs=["spec.md"], summary="done")
    assert ActorOutput.model_validate_json(a.model_dump_json()) == a
    assert ActorOutput().status is False


def test_repair_context_holds_bounded_prior_verdict() -> None:
    verdict = GateVerdict(passed=False, checks=[CheckResult(name="x", passed=False)])
    ctx = RepairContext(prior_verdict=verdict, prior_failed=True, iteration=2)
    assert ctx.prior_failed is True and ctx.iteration == 2
    assert ctx.prior_verdict is not None and ctx.prior_verdict.passed is False


def test_ratchet_config_roundtrip_and_positive() -> None:
    r = RatchetConfig(max_stall=3)
    assert r.progress_key == "artifact_refs"
    assert RatchetConfig.model_validate_json(r.model_dump_json()) == r
    with pytest.raises(ValidationError):
        RatchetConfig(max_stall=0)


def test_loop_result_passed_has_no_escalation() -> None:
    r = LoopResult(run_id="x", status=LoopStatus.PASSED, iterations=1)
    assert r.escalation is None


def test_loop_result_non_passed_has_escalation() -> None:
    e = EscalationSummary(status=LoopStatus.EXHAUSTED, iterations=3)
    r = LoopResult(run_id="x", status=LoopStatus.EXHAUSTED, iterations=3, escalation=e)
    assert r.escalation is not None
    assert r.escalation.status == LoopStatus.EXHAUSTED
    assert LoopResult.model_validate_json(r.model_dump_json()) == r


def test_loop_config_roundtrip() -> None:
    # actor/gate are injectable seams; use string markers for JSON roundtrip.
    c = LoopConfig(actor="actor", gate="gate", max_iterations=5, run_id="x")
    assert LoopConfig.model_validate_json(c.model_dump_json()).max_iterations == 5


def test_loop_config_validates_actor_gate() -> None:
    # missing actor -> error (FR-009)
    with pytest.raises(ValueError):
        LoopConfig(gate=object(), max_iterations=5).validate_config()
    with pytest.raises(ValueError):
        LoopConfig(actor=object(), max_iterations=5).validate_config()


def test_loop_config_validates_max_iterations_gt_zero() -> None:
    # Pydantic field constraint (gt=0) rejects <= 0 at construction.
    for bad in (0, -1):
        with pytest.raises(ValidationError):
            LoopConfig(actor=object(), gate=object(), max_iterations=bad)
    # validate_config remains a fail-fast guard for defensively-typed values.
    c = LoopConfig(actor=object(), gate=object(), max_iterations=5)
    c.max_iterations = -2  # bypass pydantic to exercise the guard
    with pytest.raises(ValueError):
        c.validate_config()