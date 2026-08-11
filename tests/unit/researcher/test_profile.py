"""Unit tests for the researcher mono-capacity execution profile (T030, US3).

``researcher`` is a mono-capacity, fixed, non-escalating role. It exposes a
constant execution profile inside the library and does **not** participate in
the ``capability_levels`` escalation system (no ``bump_level`` / ``FIXED_ROLES``).
"""

from __future__ import annotations

from ai_factory.capability_levels import FIXED_ROLES
from ai_factory.researcher.profile import RESEARCHER_PROFILE, ResearcherProfile


def test_researcher_exposes_constant_mono_capacity_profile() -> None:
    profile = ResearcherProfile.get_default()
    assert isinstance(profile, ResearcherProfile)
    # Non-escalating: a single fixed capacity level, not a range.
    assert profile.capacity == "mono"


def test_researcher_profile_is_a_public_constant_object() -> None:
    # Accessible as a module constant for callers that need the fixed object.
    assert RESEARCHER_PROFILE.capacity == "mono"


def test_researcher_is_not_in_capability_levels_fixed_roles() -> None:
    # `researcher` must not participate in the escalation system.
    assert "researcher" not in FIXED_ROLES


def test_profile_carries_logical_model_and_limits() -> None:
    p = ResearcherProfile.get_default()
    assert p.logical_model  # a usable logical model name
    assert p.max_tokens > 0  # finite token budget
    assert p.max_cost_usd >= 0  # finite, non-negative cost cap
    assert p.timeout_s > 0  # a sane timeout
    assert p.max_angles >= 2  # multi-angle expansion (Option D)


def test_profile_is_frozen_and_immutable() -> None:
    # The public constant is identical to the factory: a single, stable
    # instance for the mono-capacity role.
    assert RESEARCHER_PROFILE is ResearcherProfile.get_default()
    assert RESEARCHER_PROFILE.capacity == "mono"
