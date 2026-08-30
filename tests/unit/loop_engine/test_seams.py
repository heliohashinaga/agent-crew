"""Unit tests for ``loop_engine`` seams + CompositeGate (T020, T021)."""

from __future__ import annotations

import pytest

from ai_factory.loop_engine.gate import CompositeGate, LoopGateError, artifact_exists
from ai_factory.loop_engine.models import (
    ActorOutput,
    CheckStage,
    RepairContext,
)
from tests.unit.loop_engine.fakes import (
    FakeActor,
    FakeDeterministicCheck,
    FakeGate,
)


def test_fake_actor_roundtrip_success() -> None:
    actor = FakeActor()
    out = actor.invoke(RepairContext())
    assert out.status is True and out.artifact_refs == ["artifact"]


def test_fake_gate_never_pass_roundtrip() -> None:
    gate = FakeGate(never_pass=True)
    v = gate.verify(ActorOutput())
    assert v.passed is False and v.reasons() == ["gate rejected"]


def test_fake_gate_pass_on_first_call() -> None:
    gate = FakeGate(pass_calls=[0])
    assert gate.verify(ActorOutput()).passed is True


def test_actor_repair_context_via_check_repair() -> None:
    actor = FakeActor(check_repair=True)
    actor.invoke(RepairContext())
    out = actor.invoke(RepairContext(prior_failed=True, iteration=1))
    assert out.summary == "prev_failed=True"


def test_actor_raise_on_index() -> None:
    actor = FakeActor(raise_on=[0])
    with pytest.raises(RuntimeError, match="blew up"):
        actor.invoke(RepairContext())


def test_artifact_exists_default_check() -> None:
    r = artifact_exists(ActorOutput(artifact_refs=["a"]))
    assert r.passed is True and r.stage == CheckStage.DETERMINISTIC
    r2 = artifact_exists(ActorOutput())
    assert r2.passed is False


def test_composite_gate_deterministic_check_prevents_reviewer() -> None:
    # Q4=B: pluggable deterministic checks; failing deterministic -> reviewer NOT called
    reviewer_calls: list[ActorOutput] = []

    def reviewer(artifact: ActorOutput):  # noqa: ANN001
        reviewer_calls.append(artifact)
        return FakeDeterministicCheck("reviewer", True)(artifact)

    gate = CompositeGate(
        deterministic=[FakeDeterministicCheck("suite", False, "broke")],
        reviewer=reviewer,
    )
    v = gate.verify(ActorOutput(artifact_refs=["a"]))
    assert v.passed is False
    assert reviewer_calls == []  # deterministic failed -> reviewer skipped
    assert v.reasons() == ["broke"]


def test_composite_gate_reviewer_runs_after_deterministic_pass() -> None:
    reviewer_calls: list[ActorOutput] = []

    def reviewer(artifact: ActorOutput):  # noqa: ANN001
        reviewer_calls.append(artifact)
        return FakeDeterministicCheck("reviewer", True)(artifact)

    gate = CompositeGate(
        deterministic=[
            FakeDeterministicCheck("suite", True),
            FakeDeterministicCheck("contract", True),
        ],
        reviewer=reviewer,
    )
    v = gate.verify(ActorOutput(artifact_refs=["a"]))
    assert len(reviewer_calls) == 1
    assert v.passed is True  # all checks (deterministic + reviewer) pass


def test_composite_gate_aggregate_passed_requires_all() -> None:
    gate = CompositeGate(
        deterministic=[
            FakeDeterministicCheck("a", True),
            FakeDeterministicCheck("b", False, "b-fail"),
        ]
    )
    v = gate.verify(ActorOutput(artifact_refs=["a"]))
    assert v.passed is False


def test_composite_gate_gate_error_surfaces() -> None:
    def boom(artifact):  # noqa: ANN001, ARG001
        raise RuntimeError("network down")

    gate = CompositeGate(deterministic=[boom])
    with pytest.raises(LoopGateError, match="network down"):
        gate.verify(ActorOutput(artifact_refs=["a"]))