"""Cross-workflow spec entities (T011, part of FR-025).

The :class:`SpecVersion` is the stable, versioned artifact the Specification
Workflow emits and a Development run consumes *by reference*. Its shape is
fixed by `data-model.md`; this module is the single source of truth so the
store (this package) and later the spec-agent / hand-off can share it.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from pydantic import BaseModel, Field, model_validator

from ai_factory.shared.state.factory_state import ApprovalStatus

# Re-export for convenience/back-compat: all spec-workflow approval strings
# flow through the shared enum.
Approval = ApprovalStatus


class FeatureRequest(BaseModel):
    """User-supplied input describing the feature (data-model.md)."""

    raw_text: str
    target_scope: str | None = None
    constraints: list[str] = Field(default_factory=list)
    linked_materials: list[str] = Field(default_factory=list)


class AcceptanceCriterion(BaseModel):
    """Testable, unambiguous acceptance criterion (FR-003)."""

    statement: str
    verified_by: str = Field(
        default="", description="How it will be checked (test/inspection)"
    )


class EdgeCase(BaseModel):
    """An identified boundary condition."""

    description: str
    expected_behavior: str


class Clarification(BaseModel):
    """Scope-critical Q&A (FR-006). Bounded options."""

    question: str
    suggested_options: list[str] = Field(default_factory=list)
    chosen_answer: str | None = None
    affects_section: str = ""


class Assumption(BaseModel):
    """Non-critical documented default (FR-006)."""

    assumption: str
    rationale: str = ""
    affects_section: str = ""


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SpecVersion(BaseModel):
    """The stable, versioned spec artifact (FR-025). The dev-run join key."""

    spec_version_id: str = Field(default="", description="Stable, unique; the join key")
    spec_run_id: str = Field(
        default="", description="The spec run that produced this version"
    )
    version: int = 1
    intent: str
    rationale: str = ""
    acceptance_criteria: list[AcceptanceCriterion] = Field(default_factory=list)
    definition_of_done: str = ""
    edge_cases: list[EdgeCase] = Field(default_factory=list)
    clarifications: list[Clarification] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT
    human_approved: bool = False
    supersedes: str | None = None
    created_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def _approved_requires_human_approval(self) -> SpecVersion:
        """FR-005: ``human_approved`` must be true before ``approved``."""
        if self.approval_status == ApprovalStatus.APPROVED and not self.human_approved:
            raise ValueError(
                "SpecVersion.approval_status=='approved' requires "
                "human_approved=True (FR-005)"
            )
        return self

    @property
    def feature_slug(self) -> str:
        """A stable kebab-case slug of ``intent`` used to group versions.

        Deterministic (lowercased alphanumeric words joined by ``-``) so a
        given intent always maps to the same feature folder in the store.
        """
        words = re.findall(r"[a-z0-9]+", self.intent.lower())
        return "-".join(words) if words else "feature"


__all__ = [
    "AcceptanceCriterion",
    "Approval",
    "Assumption",
    "Clarification",
    "EdgeCase",
    "FeatureRequest",
    "SpecVersion",
]
