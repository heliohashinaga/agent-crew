"""Tests for telemetry emission + redaction (T029/T030, FR-018, SC-010).

FR-018: secret-looking values are auto-redacted from telemetry BEFORE any
emission. SC-010: no secrets may leak. The emitter sanitizes a record to a
redacted dict and renders machine (json) or human forms.
"""

from __future__ import annotations

import json

from ai_factory.shared.telemetry.emitter import (
    has_secret_like,
    render_record,
    sanitize,
)
from ai_factory.shared.telemetry.record import (
    DevRoleInvocation,
    SpecRoleInvocation,
    TelemetryRecord,
)


def test_sanitize_telemetry_record_round_trips() -> None:
    rec = TelemetryRecord(tokens_in=10, result="pass")
    data = sanitize(rec)
    assert data["tokens_in"] == 10
    assert data["result"] == "pass"


def test_sanitize_spec_invocation_keeps_role_and_feedback() -> None:
    inv = SpecRoleInvocation(
        role="requirements_reviewer",
        outcome="rework",
        feedback="add edge cases",
        telemetry=TelemetryRecord(result="rework"),
    )
    data = sanitize(inv)
    assert data["role"] == "requirements_reviewer"
    assert data["feedback"] == "add edge cases"


def test_sanitize_dev_invocation_keeps_capability() -> None:
    inv = DevRoleInvocation(
        role="code_worker", capability_level="junior", telemetry=TelemetryRecord()
    )
    data = sanitize(inv)
    assert data["capability_level"] == "junior"


def test_emission_redacts_secret_like_values() -> None:
    """FR-018: secret-looking tokens never reach output."""
    inv = SpecRoleInvocation(
        role="spec_agent",
        feedback="Authorization: Bearer abc123token",
        telemetry=TelemetryRecord(),
    )
    out = render_record(inv, fmt="json")
    assert "abc123token" not in out
    assert "[REDACTED]" in out


def test_render_json_is_parseable() -> None:
    out = render_record(TelemetryRecord(tokens_in=3, result="pass"), fmt="json")
    data = json.loads(out)
    assert data["tokens_in"] == 3


def test_render_human_is_not_json() -> None:
    out = render_record(TelemetryRecord(tokens_in=3, result="fail"), fmt="human")
    assert not out.lstrip().startswith("{")


def test_has_secret_like_detects_tokens() -> None:
    inv = SpecRoleInvocation(
        role="spec_agent", feedback="api_key=supersecret99", telemetry=TelemetryRecord()
    )
    assert has_secret_like(inv) is True


def test_has_secret_like_false_for_clean() -> None:
    inv = SpecRoleInvocation(
        role="spec_agent", feedback="all clear", telemetry=TelemetryRecord()
    )
    assert has_secret_like(inv) is False
