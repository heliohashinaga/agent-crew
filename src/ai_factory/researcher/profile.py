"""Mono-capacity execution profile for the ``researcher`` role (T030, US3).

``researcher`` is a **mono-capacity, fixed, non-escalating** role. Its execution
profile is defined here as a constant object inside the researcher library. It
is deliberately **not** routed through :mod:`capability_levels`/``FIXED_ROLES``
— researcher does not participate in the escalation system that serves
coder/tester/security (there is no ``bump_level``).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Role identifier (also the telemetry ``role`` and the CLI's ``role`` field).
RESEARCHER_ROLE = "researcher"

# Multi-angle web expansion bounds (Option D).
MIN_ANGLES = 2
MAX_ANGLES = 4


class ResearcherProfile(BaseModel):
    """Constant, non-escalating capacity profile carried in the library."""

    model_config = {"frozen": True}

    role: str = RESEARCHER_ROLE
    capacity: Literal["mono"] = "mono"
    logical_model: str = "standard"
    max_tokens: int = Field(default=4000, ge=1)
    max_cost_usd: float = Field(default=0.005, ge=0.0)
    timeout_s: float = Field(default=20.0, gt=0)
    max_angles: int = Field(default=MAX_ANGLES, ge=MIN_ANGLES)
    concurrency: int = Field(default=1, ge=1)
    escalated: bool = False

    @classmethod
    def get_default(cls) -> ResearcherProfile:
        """Return the single constant mono-capacity profile instance."""
        return RESEARCHER_PROFILE


# The single, immutable constant instance (frozen at import time).
RESEARCHER_PROFILE = ResearcherProfile()

__all__ = [
    "MIN_ANGLES",
    "MAX_ANGLES",
    "RESEARCHER_PROFILE",
    "RESEARCHER_ROLE",
    "ResearcherProfile",
]
