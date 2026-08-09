"""Requirements-reviewer role library (T019, FR-004).

Deterministically validates a draft :class:`SpecVersion` against five
dimensions — clarity, completeness, consistency, testability, and edge-case
coverage — returning an Approve/Reject :class:`ReviewVerdict` with explicit,
stable reasons. Network-free so the contract tests and the spec graph run
without an LLM.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ai_factory.shared.spec_store.models import SpecVersion


class ReviewVerdict(BaseModel):
    """The outcome of a requirements review (Approve/Reject + reasons)."""

    approved: bool
    reasons: list[str] = Field(default_factory=list)
    feedback: str = Field(
        default="", description="Specific feedback for the amend loop"
    )


def _badge(code: str) -> str:
    return f"[{code}]"


def review(spec: SpecVersion) -> ReviewVerdict:
    """Validate ``spec`` and return a verdict with per-dimension reasons."""
    reasons: list[str] = []

    # Completeness / clarity
    if not spec.intent.strip():
        reasons.append(f"{_badge('completeness')} spec has no intent")
    if not spec.acceptance_criteria:
        reasons.append(
            f"{_badge('completeness')} spec has no acceptance criteria (FR-003)"
        )
    if not spec.definition_of_done.strip():
        reasons.append(f"{_badge('completeness')} spec has no definition of done")

    # Clarity / consistency: AC statements must be non-empty and unique.
    statements = [c.statement.strip() for c in spec.acceptance_criteria]
    for i, s in enumerate(statements, start=1):
        if not s:
            reasons.append(f"{_badge('clarity')} acceptance criterion #{i} is empty")
    if len(statements) != len(set(statements)):
        reasons.append(f"{_badge('consistency')} acceptance criteria are duplicated")

    # Testability
    for i, c in enumerate(spec.acceptance_criteria, start=1):
        if not c.verified_by.strip():
            reasons.append(
                f"{_badge('testability')} acceptance criterion #{i} is not testable "
                f"(no verification method)"
            )

    # Edge-case coverage
    if not spec.edge_cases:
        reasons.append(f"{_badge('edge_cases')} no edge cases defined")

    approved = not reasons
    feedback = "; ".join(reasons) if reasons else ""
    return ReviewVerdict(approved=approved, reasons=reasons, feedback=feedback)


__all__ = ["ReviewVerdict", "review"]
