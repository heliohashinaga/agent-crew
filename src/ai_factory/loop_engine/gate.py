"""Gate implementations for ``loop_engine`` (T021, contracts/actor-gate-seam.md).

- ``CompositeGate`` — two-stage gate (Q2=C): deterministic checks first
  (network-free, pluggable), then an independent reviewer (integration-gated).
- ``CallableGate`` — wraps a plain callable returning a :class:`GateVerdict`,
  convenient for tests/scripts.
"""

from __future__ import annotations

from collections.abc import Callable

from ai_factory.loop_engine.actor import Gate
from ai_factory.loop_engine.models import (
    ActorOutput,
    CheckResult,
    CheckStage,
    GateVerdict,
)


class LoopGateError(RuntimeError):
    """Raised when a gate errors or is unavailable (US2 AS-3, FR-011)."""


class CompositeGate(Gate):
    """Two-stage external gate (Q2=C, FR-011).

    Stage 1 runs the configured **deterministic** checks (network-free,
    pluggable — Q4=B); stage 2 runs an independent reviewer **only after**
    all deterministic checks pass. The aggregate ``passed`` requires all
    checks (deterministic + reviewer).
    """

    def __init__(
        self,
        deterministic: list[Callable[[ActorOutput], CheckResult]] | None = None,
        reviewer: Callable[[ActorOutput], CheckResult] | None = None,
    ) -> None:
        self._deterministic = deterministic or [artifact_exists]
        self._reviewer = reviewer

    def verify(self, artifact: ActorOutput) -> GateVerdict:
        checks: list[CheckResult] = []
        for check in self._deterministic:
            try:
                checks.append(check(artifact))
            except Exception as exc:  # noqa: BLE001
                raise LoopGateError(f"deterministic check failed: {exc}") from exc

        deterministic_ok = all(c.passed for c in checks)

        if deterministic_ok and self._reviewer is not None:
            try:
                checks.append(self._reviewer(artifact))
            except Exception as exc:  # noqa: BLE001
                raise LoopGateError(f"reviewer gate failed: {exc}") from exc

        return GateVerdict(checks=checks)


class CallableGate(Gate):
    """Wraps a plain ``callable(artifact) -> GateVerdict`` into a ``Gate``."""

    def __init__(self, fn: Callable[[ActorOutput], GateVerdict]) -> None:
        self._fn = fn

    def verify(self, artifact: ActorOutput) -> GateVerdict:
        return self._fn(artifact)


def artifact_exists(artifact: ActorOutput) -> CheckResult:
    """Default pluggable deterministic check (Q4=B): at least one artifact ref."""
    passed = bool(artifact.artifact_refs)
    return CheckResult(
        name="artifact_exists",
        stage=CheckStage.DETERMINISTIC,
        passed=passed,
        reasons=[] if passed else ["no artifact refs produced"],
    )


__all__ = [
    "CallableGate",
    "CompositeGate",
    "LoopGateError",
    "artifact_exists",
]