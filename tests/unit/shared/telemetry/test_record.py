"""Tests for telemetry records (T027, data-model.md, FR-016).

Every role invocation records a :class:`TelemetryRecord` (role, model,
capability level, tokens, cost, latency, retries, errors, escalations,
result) plus role-specific invocation wrappers. Defaults are zero-valued so
deterministic tests and early pipelines can emit a consistent record.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_factory.shared.telemetry.record import (
    DevRoleInvocation,
    SpecRoleInvocation,
    TelemetryRecord,
)


def test_telemetry_record_defaults() -> None:
    rec = TelemetryRecord(result="pass")
    assert rec.tokens_in == 0
    assert rec.tokens_out == 0
    assert rec.cost == 0.0
    assert rec.latency == 0.0
    assert rec.tool_calls == 0
    assert rec.retries == 0
    assert rec.errors == 0
    assert rec.escalations == 0
    assert rec.overspend is None


def test_telemetry_record_records_all_fr016_metrics() -> None:
    rec = TelemetryRecord(
        tokens_in=120,
        tokens_out=40,
        cost=0.003,
        latency=1.4,
        tool_calls=2,
        retries=1,
        errors=0,
        escalations=0,
        result="pass",
        overspend=False,
    )
    assert rec.latency == 1.4
    assert rec.overspend is False
    assert rec.result == "pass"


def test_result_literal() -> None:
    with pytest.raises(ValidationError):
        TelemetryRecord(result="catastrophic")


def test_spec_role_invocation() -> None:
    inv = SpecRoleInvocation(
        role="requirements_reviewer",
        attempt=2,
        outcome="rework",
        feedback="add edge cases",
        telemetry=TelemetryRecord(result="rework"),
    )
    assert inv.role == "requirements_reviewer"
    assert inv.outcome == "rework"
    assert inv.feedback == "add edge cases"
    assert inv.telemetry.result == "rework"


def test_spec_role_literal_validation() -> None:
    with pytest.raises(ValidationError):
        SpecRoleInvocation(role="code_worker", telemetry=TelemetryRecord(result="pass"))


def test_dev_role_invocation_carries_capability_level() -> None:
    inv = DevRoleInvocation(
        role="code_worker",
        model="some-model",
        capability_level="junior",
        telemetry=TelemetryRecord(result="pass"),
    )
    assert inv.capability_level == "junior"
    assert inv.model == "some-model"


def test_serialization_round_trip() -> None:
    rec = TelemetryRecord(tokens_in=5, result="fail")
    loaded = TelemetryRecord.model_validate_json(rec.model_dump_json())
    assert loaded == rec
