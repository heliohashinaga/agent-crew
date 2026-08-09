"""Core shared state models (T007).

Defines the shapes from `data-model.md` that every role/workflow shares:
- :class:`ApprovalStatus` — the spec lifecycle enum.
- :class:`Checkpoint` — resumability record at role/phase boundaries (FR-020).
- :class:`RunState` — the persisted top-level run envelope.
- :class:`FactoryState` — the LangGraph state envelope that flows between
  nodes while a run executes.

These carry no workflow logic; they are plain Pydantic data shapes that the
libraries and the two workflows compose (constitution Principle I).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

Workflow = Literal["spec", "dev"]
"""The two independent workflows (FR-024)."""

# Dev run lifecycle (data-model.md): ``planned → executing → (delivered |
# failed | stopped_human)``. ``stopped_human`` only when re-planning fails.
RunStatus = Literal["planned", "executing", "delivered", "failed", "stopped_human"]


class ApprovalStatus(StrEnum):
    """Spec lifecycle (data-model.md): the approval state machine."""

    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Checkpoint(BaseModel):
    """A completed phase boundary enabling resumability (FR-020)."""

    run_id: str
    workflow: Workflow
    phase: str
    state_ref: str = Field(
        description="Reference to persisted state (LangGraph checkpointer)"
    )
    completed: bool = False
    created_at: datetime = Field(default_factory=_utc_now)


class RunState(BaseModel):
    """Persisted top-level run envelope.

    Dev runs carry ``spec_version_id`` + ``spec_run_id`` so every dev run is
    traceable back to the spec run that produced it (FR-025, SC-017).
    """

    run_id: str
    workflow: Workflow
    spec_version_id: str | None = None
    spec_run_id: str | None = None
    status: RunStatus = "planned"
    checkpoints: list[Checkpoint] = Field(default_factory=list)
    # Role-invocation telemetry; refined to the typed invocation models in
    # later phases. Kept generic here to avoid coupling state to any role.
    telemetry: list[Any] = Field(default_factory=list)


class FactoryState(BaseModel):
    """The LangGraph state envelope flowing between workflow nodes.

    Carries the cross-cutting run context plus an opaque ``payload`` that each
    workflow populates with its own entity data (spec vs dev). Branching a
    new payload per workflow keeps this shared model tiny and decoupled.
    """

    run_id: str
    workflow: Workflow
    spec_version_id: str | None = None
    spec_run_id: str | None = None
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT
    checkpoints: list[Checkpoint] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=_utc_now)


__all__ = [
    "ApprovalStatus",
    "Checkpoint",
    "FactoryState",
    "RunState",
    "RunStatus",
    "Workflow",
]
