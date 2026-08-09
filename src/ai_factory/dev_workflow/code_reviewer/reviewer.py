"""Code Reviewer role library (T051, FR-011, FR-008).

Reviews the code worker's product in the repo: every planned implementation
module exists, the local validation passed, each module has an accompanying
unit-test module, and required artifacts — README (FR-011) and any linked
ADR (FR-008, T046) — are committed. Rejections carry specific, stable
reasons.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ai_factory.dev_workflow.code_worker.worker import CodeWorkProduct
from ai_factory.dev_workflow.technical_planner.planner import TechnicalPlan


class CodeReviewVerdict(BaseModel):
    """Approve/Reject result for the code worker's product."""

    approved: bool
    reasons: list[str] = Field(default_factory=list)
    feedback: str = ""


def _badge(code: str) -> str:
    return f"[{code}]"


def review(
    product: CodeWorkProduct, plan: TechnicalPlan, repo: Path
) -> CodeReviewVerdict:
    """Review ``product`` against ``plan`` inside ``repo``."""
    reasons: list[str] = []
    repo = Path(repo)

    if product.validation != "passed":
        reasons.append(
            f"{_badge('validation')} worker validation failed: {product.errors}"
        )

    impl_files = [
        f for f in product.files if f.endswith(".py") and not f.startswith("test_")
    ]
    test_files = [f for f in product.files if f.startswith("test_")]

    for rel in impl_files:
        if not (repo / rel).exists():
            reasons.append(
                f"{_badge('completeness')} missing implementation module {rel!r}"
            )

    for rel in test_files:
        if not (repo / rel).exists():
            reasons.append(f"{_badge('tests')} missing test module {rel!r}")

    if not test_files:
        reasons.append(f"{_badge('tests')} no unit-test modules were produced")

    if plan.assessment.documentation_required and not (repo / "README.md").exists():
        reasons.append(
            f"{_badge('docs')} documentation required (FR-011) but README.md missing"
        )

    if plan.adr is not None:
        adr_docs = (
            list((repo / "docs" / "adr").glob("*.md"))
            if (repo / "docs" / "adr").exists()
            else []
        )
        if not adr_docs:
            reasons.append(
                f"{_badge('adr')} plan records architecture decision "
                f"{plan.adr.title!r} but no docs/adr/*.md was committed (FR-008)"
            )

    approved = not reasons
    return CodeReviewVerdict(
        approved=approved, reasons=reasons, feedback="; ".join(reasons)
    )


__all__ = ["CodeReviewVerdict", "review"]
