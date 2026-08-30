"""Independent reviewer gate (T081, Q2=C, FR-011) — integration-gated.

The second-stage gate runs only after deterministic checks pass. It is
network/LLM-bound: a real implementation reviews the artifact via an
injectable provider. Used under ``-m integration``; when the network/LLM is
unavailable it surfaces a typed error (``LoopGateError``) — never a silent
pass.
"""

from __future__ import annotations

from collections.abc import Callable

from ai_factory.loop_engine.actor import Gate
from ai_factory.loop_engine.gate import CompositeGate, LoopGateError
from ai_factory.loop_engine.models import (
    ActorOutput,
    CheckResult,
    CheckStage,
    GateVerdict,
)


class ReviewerGate(Gate):
    """A gate wrapping an LLM/network-bound reviewer (Q2=C second stage)."""

    def __init__(self, reviewer: Callable[[ActorOutput], CheckResult]) -> None:
        self._reviewer = reviewer

    def verify(self, artifact: ActorOutput) -> GateVerdict:
        try:
            check = self._reviewer(artifact)
        except Exception as exc:  # noqa: BLE001
            raise LoopGateError(f"independent reviewer unavailable: {exc}") from exc
        return GateVerdict(checks=[check])


def build_composite_with_reviewer(
    deterministic: list[Callable[[ActorOutput], CheckResult]],
    reviewer: Callable[[ActorOutput], CheckResult],
) -> CompositeGate:
    """Compose the two-stage gate: deterministic first, then reviewer (FR-011)."""
    return CompositeGate(deterministic=deterministic, reviewer=reviewer)


def reviewer_check(
    name: str, passed: bool, reasons: list[str] | None = None
) -> CheckResult:
    """Build a reviewer-stage ``CheckResult``."""
    return CheckResult(
        name=name,
        stage=CheckStage.REVIEWER,
        passed=passed,
        reasons=list(reasons or []),
    )


__all__ = [
    "ReviewerGate",
    "build_composite_with_reviewer",
    "reviewer_check",
]