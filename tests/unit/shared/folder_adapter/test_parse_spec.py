"""Unit tests for spec.md parsing (T006/T007, FR-003/005)."""

from ai_factory.shared.folder_adapter.parse_spec import parse_spec

SPEC = """# User Session Timeout

## Functional Requirements

- FR-001: Idle sessions must expire after 30 minutes. (MUST)
- FR-002: Expired sessions must force re-authentication.

## Acceptance Criteria

- [x] A-1: A session does not exceed 30 minutes of idle time.
- [ ] A-2: Session expiry is enforced.
"""


def test_parses_goal() -> None:
    parsed = parse_spec(SPEC)
    assert parsed.goal == "User Session Timeout"


def test_derives_functional_requirements() -> None:
    parsed = parse_spec(SPEC)
    assert (
        "FR-001: Idle sessions must expire after 30 minutes. (MUST)"
        in parsed.functional_requirements
    )
    assert (
        "FR-002: Expired sessions must force re-authentication."
        in parsed.functional_requirements
    )


def test_carries_acceptance_criteria() -> None:
    parsed = parse_spec(SPEC)
    assert parsed.acceptance_criteria


def test_no_re_derivation_keeps_original_text() -> None:
    parsed = parse_spec(SPEC)
    # 1:1 carry — original requirement text is preserved verbatim (FR-005).
    assert parsed.functional_requirements[0].startswith("FR-001:")
