"""Integration tests for the independent-reviewer gate (T081, Q2=C, FR-011).

Network/LLM-bound path; gated ``-m integration``. Deterministic-core tests are
kept network-free in the unit suite; these exercise the reviewer seam and real
orchestration of the reviewer gate.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

from ai_factory.loop_engine.gate import LoopGateError  # noqa: E402
from ai_factory.loop_engine.models import ActorOutput  # noqa: E402
from ai_factory.loop_engine.reviewer_gate import (  # noqa: E402
    ReviewerGate,
    build_composite_with_reviewer,
    reviewer_check,
)


def test_reviewer_gate_verdict_backed_by_callable() -> None:
    gate = ReviewerGate(
        reviewer=lambda a: reviewer_check("reviewer", True)
    )
    verdict = gate.verify(ActorOutput(artifact_refs=["x"]))
    assert verdict.passed is True
    assert verdict.checks[0].stage.value == "reviewer"


def test_composite_reviewer_runs_only_after_deterministic_pass() -> None:
    from tests.unit.loop_engine.fakes import FakeDeterministicCheck

    called: list[bool] = []

    def reviewer(a: ActorOutput) -> None:  # noqa: ANN001
        called.append(True)
        return reviewer_check("reviewer", True)

    gate = build_composite_with_reviewer(
        deterministic=[FakeDeterministicCheck("suite", True)],
        reviewer=reviewer,
    )
    v = gate.verify(ActorOutput(artifact_refs=["x"]))
    assert v.passed is True
    assert called == [True]


def test_reviewer_unavailable_surfaces_not_silent_pass() -> None:
    def boom(a: ActorOutput) -> None:  # noqa: ANN001, ARG001
        raise RuntimeError("network down")

    gate = ReviewerGate(reviewer=boom)
    with pytest.raises(LoopGateError, match="network down"):
        gate.verify(ActorOutput(artifact_refs=["x"]))