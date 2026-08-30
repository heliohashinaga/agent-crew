"""Actor and Gate seams for ``loop_engine`` (T020, contracts/actor-gate-seam.md).

The loop is a reusable harness over two injectable seams:
- ``Actor`` — produces work each iteration.
- ``Gate`` — verifies it (external, independent; the actor never self-grades).

Concrete bindings and test fakes plug into these same interfaces.
"""

from __future__ import annotations

from typing import Protocol

from ai_factory.loop_engine.models import (
    ActorOutput,
    GateVerdict,
    RepairContext,
)


class Actor(Protocol):
    """Produce work for one loop iteration.

    ``invoke`` receives the previous repair context; returns an
    :class:`ActorOutput`. The actor's ``status`` claim is NOT the loop's
    verdict (FR-002 no-self-grading).
    """

    def invoke(self, context: RepairContext) -> ActorOutput: ...


class Gate(Protocol):
    """Verify an actor's artifact externally (FR-002, Q2=C)."""

    def verify(self, artifact: ActorOutput) -> GateVerdict: ...


__all__ = ["Actor", "Gate"]