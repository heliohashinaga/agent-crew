"""Technical Planner role library (T045, FR-007/008).

From an approved spec, produces a :class:`TechnicalPlan` + :class:`TechnicalAssessment`
(complexity, technical risk, architecture impact, test scope, security
surface, documentation required) by mapping the spec to components,
identifying risks, and planning the test strategy (FR-007). Produces an
:class:`ArchitectureDecisionRecord` ONLY when architecture impact is real
(FR-008). Purely deterministic, network-free.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ai_factory.dev_workflow.technical_planner.adr import (
    ArchitectureDecisionRecord,
    should_create_adr,
)
from ai_factory.shared.spec_store.models import SpecVersion

ARCHITECTURE_KEYWORDS = (
    "database",
    "migrat",
    "microservice",
    "service split",
    "event bus",
    "queue",
    "worker",
    "cache",
    "legacy",
    "monolith",
    "shard",
    "replica",
    "architecture",
    "api gateway",
    "postgres",
    "message broker",
)
SECURITY_KEYWORDS = (
    "auth",
    "password",
    "token",
    "payment",
    "credit",
    "security",
    "pii",
    "account lock",
    "permission",
    "secret",
)
DOCUMENTATION_KEYWORDS = ("readme", "runbook", "documentation", "api docs", "operator")


class TechnicalAssessment(BaseModel):
    """The planner's assessment of the spec (FR-007)."""

    complexity: str = "standard"
    risk: Literal["low", "medium", "high"] = "low"
    architecture_impact: bool = False
    test_scope: list[str] = Field(default_factory=list)
    security_surface: list[str] = Field(default_factory=list)
    documentation_required: bool = False
    plan_summary: str = ""


class TechnicalSubtask(BaseModel):
    """A unit of implementation work derived from the spec."""

    title: str
    description: str
    files: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)


class TechnicalPlan(BaseModel):
    """The planner output: subtasks + assessment (+ conditional ADR)."""

    spec_version_id: str = ""
    goal: str = ""
    assessment: TechnicalAssessment = Field(default_factory=TechnicalAssessment)
    subtasks: list[TechnicalSubtask] = Field(default_factory=list)
    adr: ArchitectureDecisionRecord | None = None


def _corpus(spec: SpecVersion) -> str:
    parts = [spec.intent, spec.definition_of_done]
    parts.extend(c.statement for c in spec.acceptance_criteria)
    parts.extend(e.description for e in spec.edge_cases)
    return " ".join(parts).lower()


def _complexity(spec: SpecVersion) -> str:
    score = len(spec.acceptance_criteria) + len(spec.edge_cases)
    if score <= 2:
        return "simple"
    if score <= 4:
        return "standard"
    return "complex"


def assess(spec: SpecVersion) -> TechnicalAssessment:
    """Assess complexity, risk, architecture impact, test/security surface."""
    corpus = _corpus(spec)
    arch = any(k in corpus for k in ARCHITECTURE_KEYWORDS)
    security_hits = [k for k in SECURITY_KEYWORDS if k in corpus]

    n_edges = len(spec.edge_cases)
    risk: Literal["low", "medium", "high"]
    if security_hits or n_edges >= 3:
        risk = "high"
    elif n_edges >= 1:
        risk = "medium"
    else:
        risk = "low"

    documentation_required = (
        risk == "high" or arch or any(k in corpus for k in DOCUMENTATION_KEYWORDS)
    )

    plan_summary = (
        f"{_complexity(spec)} complexity; risk={risk}; "
        f"architecture_impact={arch}; docs={'yes' if documentation_required else 'no'}"
    )
    return TechnicalAssessment(
        complexity=_complexity(spec),
        risk=risk,
        architecture_impact=arch,
        test_scope=["unit", "integration"]
        if _complexity(spec) != "simple"
        else ["unit"],
        security_surface=security_hits,
        documentation_required=documentation_required,
        plan_summary=plan_summary,
    )


def _slug(text: str, n: int = 4) -> str:
    words = [w for w in text.lower().split() if w.isalnum()][:n]
    return "-".join(words) if words else "feature"


def produce_plan(spec: SpecVersion) -> TechnicalPlan:
    """Build the TechnicalPlan (subtasks + conditional ADR) for ``spec``."""
    assessment = assess(spec)
    subtasks: list[TechnicalSubtask] = []
    for i, ac in enumerate(spec.acceptance_criteria, start=1):
        base = _slug(ac.statement)
        subtasks.append(
            TechnicalSubtask(
                title=f"Implement: {ac.statement}",
                description=f"Satisfy acceptance criterion #{i}.",
                files=[f"{base}.py", f"test_{base}.py"],
                acceptance_criteria=[ac.statement],
            )
        )
    subtasks.append(
        TechnicalSubtask(
            title="Add unit and integration tests",
            description=_assessment_test_scope(assessment),
            files=["test_suite.py"],
            acceptance_criteria=[ac.statement for ac in spec.acceptance_criteria],
        )
    )
    if assessment.documentation_required:
        subtasks.append(
            TechnicalSubtask(
                title="Write documentation",
                description="README/API notes per the assessment.",
                files=["README.md"],
                acceptance_criteria=[],
            )
        )

    adr: ArchitectureDecisionRecord | None = None
    if should_create_adr(assessment.architecture_impact):
        adr = ArchitectureDecisionRecord(
            title=f"Architecture decision for: {spec.intent}",
            context=(
                f"Spec '{spec.intent}' requires a significant architectural choice."
            ),
            decision=f"Adopt the architecture implied by: {spec.intent}",
            rationale="Significant trade-off detected by planner assessment.",
            trade_offs=["Operational complexity", "Migration cost", "Team learning"],
            alternatives=["Keep current approach", "Outsource component"],
        )

    return TechnicalPlan(
        spec_version_id=spec.spec_version_id,
        goal=_slug(spec.intent, 6),
        assessment=assessment,
        subtasks=subtasks,
        adr=adr,
    )


def _assessment_test_scope(assessment: TechnicalAssessment) -> str:
    return "Tests: " + ", ".join(assessment.test_scope)


__all__ = [
    "TechnicalAssessment",
    "TechnicalPlan",
    "TechnicalSubtask",
    "assess",
    "produce_plan",
]
