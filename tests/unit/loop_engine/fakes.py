"""Deterministic test fakes for ``loop_engine`` seams (T020, actor-gate-seam.md).

These make every US1-US3 determinism test network-free via FakeActor +
FakeGate (SC-001/SC-002/SC-003).
"""

from __future__ import annotations

from ai_factory.loop_engine.actor import Gate
from ai_factory.loop_engine.models import (
    ActorOutput,
    BudgetDelta,
    CheckResult,
    CheckStage,
    GateVerdict,
    RepairContext,
)


class FakeActor:
    """A scripted ``Actor`` with configurable outputs per call."""

    def __init__(
        self,
        outputs: list[ActorOutput] | None = None,
        *,
        always_success: bool = False,
        artifact_refs: list[str] | None = None,
        check_repair: bool = False,
        raise_on: list[int] | None = None,
    ) -> None:
        self.outputs = outputs or []
        self.calls: list[RepairContext] = []
        self.always_success = always_success
        self.artifact_refs = artifact_refs or ["artifact"]
        self.check_repair = check_repair
        self.raise_on = raise_on or []

    def invoke(self, context: RepairContext) -> ActorOutput:
        idx = len(self.calls)
        self.calls.append(context)
        if idx in self.raise_on:
            raise RuntimeError(f"actor blew up on call {idx}")
        if self.outputs:
            out = self.outputs[min(idx, len(self.outputs) - 1)]
            if self.check_repair:
                out.summary = f"prev_failed={context.prior_failed}"
            return out
        # default: success claim + an artifact ref (never the loop's verdict)
        out = ActorOutput(
            status=self.always_success or True,
            artifact_refs=self.artifact_refs,
            description="fake actor output",
            summary="ok",
        )
        if self.check_repair:
            out.summary = f"prev_failed={context.prior_failed}"
        return out


class FakeGate(Gate):
    """A scripted ``Gate`` with a configurable verdict sequence."""

    def __init__(
        self,
        pass_calls: list[int] | None = None,
        *,
        never_pass: bool = False,
        fail_after: int | None = None,
        reasons: str = "gate rejected",
        raise_always: bool = False,
        raise_on: list[int] | None = None,
        consumed: BudgetDelta | None = None,
    ) -> None:
        self.pass_calls = pass_calls or []
        self.calls: list[ActorOutput] = []
        self.never_pass = never_pass
        self.fail_after = fail_after  # pass on cease after this many fails
        self.reasons = reasons
        self.raise_always = raise_always
        self.raise_on = raise_on or []
        self.consumed = consumed or BudgetDelta()

    def verify(self, artifact: ActorOutput) -> GateVerdict:
        idx = len(self.calls)
        self.calls.append(artifact)
        if self.raise_always or idx in self.raise_on:
            raise RuntimeError("gate unavailable")
        should_pass = idx in self.pass_calls
        if self.never_pass:
            should_pass = False
        if self.fail_after is not None and idx >= self.fail_after:
            should_pass = True
        check = CheckResult(
            name="gate",
            stage=CheckStage.DETERMINISTIC,
            passed=should_pass,
            reasons=[] if should_pass else [self.reasons],
        )
        return GateVerdict(checks=[check], consumed=self.consumed)


class FakeDeterministicCheck:
    """A pluggable deterministic check with a fixed pass/fail result."""

    def __init__(self, name: str, passed: bool, reason: str = "") -> None:
        self.name = name
        self.passed = passed
        self.reason = reason

    def __call__(self, artifact: ActorOutput) -> CheckResult:
        return CheckResult(
            name=self.name,
            stage=CheckStage.DETERMINISTIC,
            passed=self.passed,
            reasons=[] if self.passed else [self.reason],
        )


__all__ = ["FakeActor", "FakeDeterministicCheck", "FakeGate"]