"""Typed telemetry records (T028, data-model.md, FR-016/FR-017).

A :class:`TelemetryRecord` captures observability for a single role
invocation: tokens, cost, latency, tool calls, retries, errors, escalations
and the result (FR-016). Role-specific wrappers (
:class:`SpecRoleInvocation`, :class:`DevRoleInvocation`) bind a record to a
role and carry capability/feedback context (FR-017).

All counts are zero-valued by default so deterministic tests and early
pipelines can emit a consistent record without an underlying model.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Result = Literal["pass", "fail", "rework"]

# Capability bands for the Dev workflow (US4 defines levels; kept here for the
# DevRoleInvocation wiring).
SpecRole = Literal["spec_agent", "requirements_reviewer"]
DevRole = Literal[
    "technical_planner",
    "orchestrator",
    "code_worker",
    "code_reviewer",
    "test_engineer",
    "test_runner",
    "security_reviewer",
    "researcher",
    "loop_engine",
]


class TelemetryRecord(BaseModel):
    """Per-invocation observability metrics (FR-016)."""

    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    latency: float = 0.0  # seconds
    tool_calls: int = 0
    retries: int = 0
    errors: int = 0
    escalations: int = 0
    result: Result = "pass"
    overspend: bool | None = Field(
        default=None, description="Budget warning raised (FR-019)"
    )


class SpecRoleInvocation(BaseModel):
    """A Specification-Workflow role invocation (FR-017)."""

    role: SpecRole
    attempt: int = 1
    outcome: Result = "pass"
    feedback: str | None = None
    telemetry: TelemetryRecord = Field(default_factory=TelemetryRecord)


class DevRoleInvocation(BaseModel):
    """A Development-Workflow role invocation (FR-017)."""

    role: DevRole
    model: str = ""
    capability_level: str = ""
    telemetry: TelemetryRecord = Field(default_factory=TelemetryRecord)


__all__ = [
    "DevRole",
    "DevRoleInvocation",
    "Result",
    "SpecRole",
    "SpecRoleInvocation",
    "TelemetryRecord",
]
