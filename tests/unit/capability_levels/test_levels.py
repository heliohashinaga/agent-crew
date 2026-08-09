"""Tests for capability levels (T035, FR-010, R9).

Code Worker / Test Engineer use the simple/standard/complex axis; Code
Reviewer / Security Reviewer use shallow/standard/deep. Higher levels MUST
correspond to greater depth, context, iterations and tool access (FR-010).
Retry level-bumping (T039/FR-015) lives in the orchestrator but uses
:func:`bump_level` from this library.
"""

from __future__ import annotations

import pytest

from ai_factory.capability_levels.levels import (
    REVIEW_AXIS,
    TASK_AXIS,
    LevelConfig,
    bump_level,
    capability_for,
    default_level,
    level_order,
)


def test_task_axis_roles_have_three_levels() -> None:
    assert TASK_AXIS == ("simple", "standard", "complex")
    for role in ("code_worker", "test_engineer"):
        assert level_order(role) == ["simple", "standard", "complex"]


def test_review_axis_roles_have_three_levels() -> None:
    assert REVIEW_AXIS == ("shallow", "standard", "deep")
    for role in ("code_reviewer", "security_reviewer"):
        assert level_order(role) == ["shallow", "standard", "deep"]


def test_higher_levels_are_monotonically_stronger() -> None:
    """FR-010: more depth, context, iterations, tokens, tool access."""
    simple = capability_for("code_worker", "simple")
    standard = capability_for("code_worker", "standard")
    complex = capability_for("code_worker", "complex")

    assert (
        simple.validation_depth < standard.validation_depth < complex.validation_depth
    )
    assert simple.retro_context < standard.retro_context < complex.retro_context
    assert simple.max_iterations < standard.max_iterations < complex.max_iterations
    assert simple.max_tokens < standard.max_tokens < complex.max_tokens
    assert (
        len(simple.tool_access) <= len(standard.tool_access) <= len(complex.tool_access)
    )


def test_review_axis_monotonic() -> None:
    shallow = capability_for("code_reviewer", "shallow")
    deep = capability_for("code_reviewer", "deep")
    assert shallow.validation_depth < deep.validation_depth
    assert shallow.retro_context < deep.retro_context


def test_default_level_is_middle_for_both_axes() -> None:
    assert default_level("code_worker") == "standard"
    assert default_level("code_reviewer") == "standard"


def test_bump_level_task_axis() -> None:
    """FR-015: retries raise the capability level at least one step."""
    assert bump_level("code_worker", "simple").level == "standard"
    assert bump_level("code_worker", "standard").level == "complex"


def test_bump_level_review_axis() -> None:
    assert bump_level("security_reviewer", "shallow").level == "standard"
    assert bump_level("security_reviewer", "standard").level == "deep"


def test_bump_at_max_stays_at_max() -> None:
    assert bump_level("code_worker", "complex").level == "complex"
    assert bump_level("code_reviewer", "deep").level == "deep"


def test_level_config_shape() -> None:
    cfg = capability_for("test_engineer", "standard")
    assert isinstance(cfg, LevelConfig)
    assert cfg.model
    assert cfg.timeout_s > 0
    assert 0 <= cfg.validation_depth <= 1


def test_unknown_level_raises() -> None:
    with pytest.raises(ValueError):
        capability_for("code_worker", "deep")  # wrong axis


def test_unknown_role_raises() -> None:
    with pytest.raises(KeyError):
        capability_for("nobody_role", "standard")
