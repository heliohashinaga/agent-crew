"""Constant execution profile for the ``loop_engine`` role (T009, FR-003).

Like ``researcher``, ``loop_engine`` carries a **constant, non-escalating**
execution profile in its own library. It is deliberately **not** routed
through :mod:`capability_levels`/``FIXED_ROLES`` — there is no ``bump_level``;
termination/escalation is driven by runtime ``LoopConfig`` (``max_iterations``,
``budget``, ``ratchet``), not by capability-level escalation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

LOOP_ENGINE_ROLE = "loop_engine"


class LoopEngineProfile(BaseModel):
    """Constant, non-escalating execution profile (Q5/Q7 aware)."""

    model_config = {"frozen": True}

    role: str = LOOP_ENGINE_ROLE
    capacity: str = "loop"  # orchestrator-like control loop, plain library
    logical_model: str = "standard"
    max_tokens: int = Field(default=2048, ge=1)
    max_cost_usd: float = Field(default=0.05, ge=0.0)
    timeout_s: float = Field(default=60.0, gt=0)
    concurrency: int = Field(default=1, ge=1)
    escalated: bool = False

    @classmethod
    def get_default(cls) -> LoopEngineProfile:
        """Return the single constant profile instance."""
        return LOOP_ENGINE_PROFILE


LOOP_ENGINE_PROFILE = LoopEngineProfile()

__all__ = [
    "LOOP_ENGINE_PROFILE",
    "LOOP_ENGINE_ROLE",
    "LoopEngineProfile",
]