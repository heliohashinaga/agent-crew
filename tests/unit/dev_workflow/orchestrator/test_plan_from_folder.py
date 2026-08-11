"""Unit tests for folder-driven execution planning (US-1, T024/T025)."""

from ai_factory.dev_workflow.orchestrator.orchestrator import plan_from_technical_plan
from ai_factory.dev_workflow.technical_planner.planner import (
    TechnicalAssessment,
    TechnicalPlan,
)


def _plan() -> TechnicalPlan:
    return TechnicalPlan(
        spec_version_id="sessions",
        goal="Session timeout",
        assessment=TechnicalAssessment(
            complexity="standard", security_surface=["token"]
        ),
    )


def test_plans_from_technical_plan() -> None:
    ep = plan_from_technical_plan(_plan())
    assert ep.spec_version_id == "sessions"
    assert ep.complexity == "standard"
    assert (
        any(
            r.role == "security_reviewer" and r.capability_level == "standard"
            for r in ep.roles
        )
    )


def test_budget_from_roles() -> None:
    ep = plan_from_technical_plan(_plan())
    assert ep.budget_total is not None
    assert ep.budget_total.tokens > 0
