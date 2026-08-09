"""Development-Workflow data shapes (data-model.md, FR-009/012/014/019)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(UTC)


class RetryAttempt(BaseModel):
    """One bounded retry of a failed step (FR-014)."""

    attempt: int
    outcome: Literal["failed", "retrying", "success"] = "retrying"
    note: str = ""
    timestamp: datetime = Field(default_factory=_utc_now)


class RePlanOutcome(BaseModel):
    """Result of an auto re-plan (FR-015)."""

    success: bool
    plan_version: int = 1
    plan_summary: str = ""
    error: str = ""


class Issue(BaseModel):
    """A classified runtime failure with its bounded handling state."""

    issue_id: str
    category: str = "logic_bug"
    severity: Literal["critical", "high", "medium", "low"] = "low"
    root_cause_class: str = ""
    message: str = ""
    retry_attempts: list[RetryAttempt] = Field(default_factory=list)
    escalation_target: str | None = None
    replan_outcome: RePlanOutcome | None = None


class Budget(BaseModel):
    """Per-role resource budget. Soft — never hard-stops a run (FR-019)."""

    tokens: int | None = None
    cost_usd: float | None = None
    time: float | None = None  # seconds


class RetryPolicy(BaseModel):
    """Bounded retry behaviour (FR-014)."""

    max_retries: int = 2
    backoff: Literal["exponential", "none"] = "exponential"
    on_limit_exceeded: Literal["escalate", "replan", "stop_human"] = "replan"  # FR-015


class RoleAssignment(BaseModel):
    """One row of the Execution Plan (FR-009)."""

    role: str
    model: str = ""
    capability_level: str = "standard"
    budget: Budget = Field(default_factory=Budget)
    timeout: float = 60.0  # seconds
    parallelization: Literal["serial", "parallel"] = "serial"
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)


class ExecutionPlan(BaseModel):
    """Orchestrator output: a per-role execution plan (FR-009)."""

    spec_version_id: str = ""
    complexity: str = "standard"
    roles: list[RoleAssignment] = Field(default_factory=list)
    budget_total: Budget = Field(default_factory=Budget)
    note: str = ""

    def for_role(self, role: str) -> RoleAssignment:
        for assignment in self.roles:
            if assignment.role == role:
                return assignment
        raise KeyError(f"no assignment for role {role!r}")


__all__ = ["Budget", "ExecutionPlan", "RetryPolicy", "RoleAssignment"]
