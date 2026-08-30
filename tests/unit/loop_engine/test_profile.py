"""Unit tests for the ``loop_engine`` constant execution profile (T009)."""

from __future__ import annotations

from ai_factory.capability_levels import levels
from ai_factory.loop_engine.profile import (
    LOOP_ENGINE_PROFILE,
    LOOP_ENGINE_ROLE,
    LoopEngineProfile,
)


def test_profile_exposes_constant_instance() -> None:
    p = LoopEngineProfile.get_default()
    assert p.role == LOOP_ENGINE_ROLE
    assert p is LOOP_ENGINE_PROFILE
    # Frozen constant.
    assert p.capacity == "loop"


def test_profile_not_in_capability_levels_fixed_roles() -> None:
    assert LOOP_ENGINE_ROLE not in levels.FIXED_ROLES
    # Not routed through escalation: loop_engine has no capability_for lookup.
    assert LOOP_ENGINE_ROLE not in levels.CAPABILITIES
    assert LOOP_ENGINE_ROLE not in levels.TASK_ROLES
    assert LOOP_ENGINE_ROLE not in levels.REVIEW_ROLES
    assert LOOP_ENGINE_ROLE not in levels.REVIEW_ROLES


def test_profile_is_frozen_constant() -> None:
    import contextlib

    with contextlib.suppress(ValueError):
        LOOP_ENGINE_PROFILE.concurrency = 4  # type: ignore[misc]
    assert LOOP_ENGINE_PROFILE.concurrency == 1