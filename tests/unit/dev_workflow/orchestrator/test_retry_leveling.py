"""Tests for orchestrator retry level-bumping (T039/T040, FR-015).

When a role fails and retries, the retry raises its capability level at
least one step and adds validation depth/budget. The default
``on_limit_exceeded`` is ``replan`` (FR-015). Bumping returns a NEW plan
and never mutates the original.
"""

from __future__ import annotations

from ai_factory.capability_levels.levels import capability_for
from ai_factory.dev_workflow.models import RetryPolicy
from ai_factory.dev_workflow.orchestrator.orchestrator import bump_for_retry, plan
from ai_factory.shared.spec_store.models import AcceptanceCriterion, SpecVersion


def _spec() -> SpecVersion:
    return SpecVersion(
        spec_version_id="f-v1-abc",
        intent="Deliver the capability.",
        acceptance_criteria=[
            AcceptanceCriterion(statement="Criterion", verified_by="test")
        ],
        definition_of_done="done",
        edge_cases=[],
    )


def test_bump_raises_task_role_one_step() -> None:
    ep = plan(_spec())  # simple spec → code_worker at "simple"
    assert ep.for_role("code_worker").capability_level == "simple"
    bumped = bump_for_retry(ep, "code_worker")
    assert bumped.for_role("code_worker").capability_level == "standard"


def test_bump_raises_review_role_one_step() -> None:
    ep = plan(_spec())
    assert ep.for_role("code_reviewer").capability_level == "shallow"
    bumped = bump_for_retry(ep, "code_reviewer")
    assert bumped.for_role("code_reviewer").capability_level == "standard"


def test_bump_step_twice_reaches_max() -> None:
    ep = plan(_spec())
    once = bump_for_retry(ep, "code_worker", step=2)
    assert once.for_role("code_worker").capability_level == "complex"


def test_bump_at_max_stays_max() -> None:
    ep = plan(_spec())
    maxed = bump_for_retry(ep, "code_worker", step=3)  # simple→standard→complex→complex
    assert maxed.for_role("code_worker").capability_level == "complex"


def test_bump_adds_budget_and_tools() -> None:
    """FR-015 + FR-010: higher level ⇒ more tokens/budget/depth."""
    ep = plan(_spec())
    before = ep.for_role("code_worker")
    after = bump_for_retry(ep, "code_worker").for_role("code_worker")
    assert after.budget.tokens > before.budget.tokens
    assert after.timeout > before.timeout
    assert (
        capability_for("code_worker", after.capability_level).retro_context
        > capability_for("code_worker", before.capability_level).retro_context
    )


def test_original_plan_is_not_mutated() -> None:
    ep = plan(_spec())
    original = ep.model_dump()
    bump_for_retry(ep, "code_worker")
    assert ep.model_dump() == original


def test_default_retry_policy_is_replan() -> None:
    """FR-015: on_limit_exceeded defaults to replan."""
    ep = plan(_spec())
    assert ep.for_role("code_worker").retry_policy.on_limit_exceeded == "replan"
    assert RetryPolicy().on_limit_exceeded == "replan"
