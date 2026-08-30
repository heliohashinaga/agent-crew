"""Data models for the ``loop_engine`` control-loop library.

The ``loop_engine`` runs an autonomous control loop:
**actor → external gate → repair → repeat**, until the gate passes or
termination conditions are met, persisting a durable ledger/spine so a run
can be paused/resumed. The deterministic core is network-free; review/LLM
work sits behind injectable seams and is integration-gated.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class BudgetDelta(BaseModel):
    """Tokens/cost/latency consumed by one iteration or check."""

    tokens: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0


class LoopBudget(BaseModel):
    """Optional termination budget (FR-003). At least one consumable dimension.

    Within ``loop_engine`` a consumed dimension exceeding its ceiling is a
    **hard stop → ``exhausted``** (Q7=A), a scoped divergence from the parent
    factory's soft-budget convention.
    """

    max_tokens: int | None = None
    max_seconds: float | None = None
    max_cost_usd: float | None = None


class RatchetConfig(BaseModel):
    """Stall/progress detector (FR-003, Q5)."""

    max_stall: int = Field(gt=0)
    progress_key: str = "artifact_refs"


class CheckStage(StrEnum):
    """Which gate stage a check belongs to (Q2=C two-stage gate)."""

    DETERMINISTIC = "deterministic"
    REVIEWER = "reviewer"


class CheckResult(BaseModel):
    """One deterministic or reviewer check inside a gate."""

    name: str
    stage: CheckStage = CheckStage.DETERMINISTIC
    passed: bool = False
    reasons: list[str] = Field(default_factory=list)
    consumed: BudgetDelta = Field(default_factory=BudgetDelta)


class GateVerdict(BaseModel):
    """The aggregate result of one verification pass (FR-002, Q2=C).

    ``passed`` is ``true`` **only if all** configured checks pass, with a
    per-check breakdown feeding both the outcome and the repair path.
    """

    passed: bool = False
    checks: list[CheckResult] = Field(default_factory=list)
    consumed: BudgetDelta = Field(default_factory=BudgetDelta)

    @model_validator(mode="after")
    def _aggregate_passed(self) -> GateVerdict:
        # Aggregate gate: passed only when every configured check passes (Q2=C).
        if self.checks:
            self.passed = all(c.passed for c in self.checks)
        return self

    def reasons(self) -> list[str]:
        """Bounded, flat list of failed-check reasons for repair context."""
        out: list[str] = []
        for check in self.checks:
            if not check.passed:
                out.extend(check.reasons)
        return out


class ActorOutput(BaseModel):
    """The result of one actor invocation.

    ``status`` is only the actor's *reported* success (never the loop's
    verdict — FR-002 no-self-grading). Artifacts are referenced, never
    duplicated into the ledger.
    """

    status: bool = False
    artifact_refs: list[str] = Field(default_factory=list)
    description: str = ""
    summary: str = ""


class RepairContext(BaseModel):
    """Context fed to the next actor invocation on repair (FR-006, Q6).

    Carries the previous gate failure verdict (bounded, concise).
    """

    prior_verdict: GateVerdict | None = None
    prior_failed: bool = False
    iteration: int = 0
    message: str = ""


class LoopStatus(StrEnum):
    """Final outcome of a loop run (Q5=A, FR-003/FR-004)."""

    PASSED = "passed"
    EXHAUSTED = "exhausted"
    STALLED = "stalled"
    ERROR = "error"


class EscalationSummary(BaseModel):
    """Concise human escalation (FR-004, Q3=A)."""

    status: LoopStatus
    iterations: int = 0
    gate_verdicts: list[GateVerdict] = Field(default_factory=list)
    budget_consumed: BudgetDelta = Field(default_factory=BudgetDelta)
    partial_artifacts: list[str] = Field(default_factory=list)


class LoopResult(BaseModel):
    """The final outcome returned by ``run_loop`` and by the CLI."""

    run_id: str = ""
    status: LoopStatus = LoopStatus.PASSED
    iterations: int = 0
    gates: list[GateVerdict] = Field(default_factory=list)
    budget: BudgetDelta = Field(default_factory=BudgetDelta)
    artifact_refs: list[str] = Field(default_factory=list)
    escalation: EscalationSummary | None = None


class LoopConfig(BaseModel):
    """Immutable configuration validated before the loop starts (FR-009)."""

    actor: object | None = None
    gate: object | None = None
    max_iterations: int = Field(gt=0)
    budget: LoopBudget | None = None
    ratchet: RatchetConfig | None = None
    ledger_dir: Path | None = None
    run_id: str = ""

    def validate_config(self) -> None:
        """Fail-fast validation (FR-009): actor, gate, max_iterations required."""
        if self.actor is None:
            raise ValueError("actor is required (FR-009)")
        if self.gate is None:
            raise ValueError("gate is required (FR-009)")
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be > 0 (FR-009)")


# Ledger record types (contracts/ledger-format.md)
class LedgerRecordType(StrEnum):
    CONFIG = "config"
    ITERATION = "iteration"
    FINAL = "final"


class ConfigRecord(BaseModel):
    type: LedgerRecordType = LedgerRecordType.CONFIG
    run_id: str = ""
    config: dict = Field(default_factory=dict)


class IterationRecord(BaseModel):
    type: LedgerRecordType = LedgerRecordType.ITERATION
    run_id: str = ""
    iteration: int = 0
    actor_out: ActorOutput = Field(default_factory=ActorOutput)
    gate: GateVerdict = Field(default_factory=GateVerdict)
    budget_delta: BudgetDelta = Field(default_factory=BudgetDelta)
    repair_context: str = ""


class FinalRecord(BaseModel):
    type: LedgerRecordType = LedgerRecordType.FINAL
    run_id: str = ""
    status: LoopStatus = LoopStatus.PASSED
    iterations: int = 0
    budget_consumed: BudgetDelta = Field(default_factory=BudgetDelta)
    escalation: EscalationSummary | None = None


__all__ = [
    "ActorOutput",
    "BudgetDelta",
    "CheckResult",
    "CheckStage",
    "ConfigRecord",
    "EscalationSummary",
    "FinalRecord",
    "GateVerdict",
    "IterationRecord",
    "LedgerRecordType",
    "LoopBudget",
    "LoopConfig",
    "LoopResult",
    "LoopStatus",
    "RatchetConfig",
    "RepairContext",
]