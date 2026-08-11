"""Unit tests for plan.md assessment import (T012/T013, T034, FR-004/SC-005)."""

from ai_factory.shared.folder_adapter.parse_plan import degrade_assessment, parse_plan

PLAN = """# User Session Timeout — Plan

## Tech Stack

- Python 3.14, Postgres, SQLAlchemy 2.0.

## Architecture Decisions

- AD-001: Background reaper scans for idle sessions.
- AD-002: Dedicated `sessions` table indexed on `last_activity_at`.

## Security

- Session tokens are stored hashed (SHA-256).

## Risks

- Expiry race between reaper and request refresh is acceptable.

## Test Strategy

- Unit tests for the reaper, integration for middleware.
"""


def test_imports_security_surface_from_plan() -> None:
    parsed = parse_plan(PLAN)
    assert (
        "token" in parsed.assessment.security_surface
        or "hash" in parsed.assessment.security_surface
    )


def test_detects_architecture_impact() -> None:
    parsed = parse_plan(PLAN)
    assert parsed.assessment.architecture_impact is True


def test_imports_test_scope() -> None:
    parsed = parse_plan(PLAN)
    assert any("reaper" in s for s in parsed.assessment.test_scope)


def test_missing_sections_degrade_with_inference_note() -> None:
    parsed = parse_plan("")
    assert parsed.assessment.complexity == "standard"
    assert parsed.assessment.test_scope == []
    assert parsed.inferred  # inference note present (SC-005)


def test_degrade_assignment() -> None:
    parsed = degrade_assessment()
    assert parsed.assessment.architecture_impact is False
    assert parsed.inferred
