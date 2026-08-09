"""Orchestrator role library (T038, FR-009/010/015).

A PURE decision layer: from a Technical Planner's assessment it produces an
:class:`ExecutionPlan` — per role: model, capability level, budget, timeout,
parallelization and retry policy. It performs no specialized work (FR-009).

Complexity is scored from the approved spec (acceptance criteria, edge
cases, clarifications, DoD breadth) and mapped onto the capability axes
(FR-010). :func:`bump_for_retry` raises a failing role's capability level
one step per FR-015.
"""

from __future__ import annotations

from ai_factory.capability_levels.levels import (
    REVIEW_ROLES,
    TASK_ROLES,
    bump_level,
    capability_for,
    default_level,
)
from ai_factory.dev_workflow.models import (
    Budget,
    ExecutionPlan,
    RetryPolicy,
    RoleAssignment,
)
from ai_factory.shared.spec_store.models import SpecVersion

ALL_DEV_ROLES = (
    "technical_planner",
    "orchestrator",
    "code_worker",
    "code_reviewer",
    "test_engineer",
    "test_runner",
    "security_reviewer",
)


def assess(spec: SpecVersion) -> str:
    """Score ``spec`` complexity: ``simple`` / ``standard`` / ``complex``."""
    score = (
        len(spec.acceptance_criteria)
        + len(spec.edge_cases)
        + len(spec.clarifications)
        + max(0, len(spec.definition_of_done.split()) // 10)
    )
    if score <= 3:
        return "simple"
    if score <= 6:
        return "standard"
    return "complex"


def _initial_level(role: str, complexity: str) -> str:
    if role in TASK_ROLES:
        return {"simple": "simple", "standard": "standard", "complex": "complex"}[
            complexity
        ]
    if role in REVIEW_ROLES:
        return {"simple": "shallow", "standard": "standard", "complex": "deep"}[
            complexity
        ]
    return default_level(role)


def plan(spec: SpecVersion, budget: Budget | None = None) -> ExecutionPlan:
    """Build the per-role execution plan for ``spec`` (FR-009, FR-010)."""
    complexity = assess(spec)
    roles: list[RoleAssignment] = []
    total_tokens = 0
    for role in ALL_DEV_ROLES:
        level = _initial_level(role, complexity)
        cfg = capability_for(role, level)
        total_tokens += cfg.max_tokens
        roles.append(
            RoleAssignment(
                role=role,
                model=cfg.model,
                capability_level=level,
                budget=Budget(
                    tokens=cfg.max_tokens,
                    cost_usd=cfg.max_cost,
                    time=cfg.timeout_s,
                ),
                timeout=cfg.timeout_s,
                parallelization="parallel"
                if role in ("test_engineer", "test_runner")
                else "serial",
                retry_policy=RetryPolicy(),  # replan on limit exceeded (FR-015)
            )
        )
    return ExecutionPlan(
        spec_version_id=spec.spec_version_id,
        complexity=complexity,
        roles=roles,
        budget_total=budget
        or Budget(
            tokens=total_tokens, cost_usd=sum(r.budget.cost_usd or 0 for r in roles)
        ),
        note=f"assessed complexity={complexity}",
    )


def bump_for_retry(plan: ExecutionPlan, role: str, step: int = 1) -> ExecutionPlan:
    """Raise ``role``'s capability level ``step`` times (FR-015).

    Used when a role fails and retries: higher level = deeper validation,
    more context and budget. Returns a NEW plan; the original is untouched.
    """
    prev = plan.for_role(role)
    level = prev.capability_level
    for _ in range(max(1, step)):
        cfg = bump_level(role, level)
        level = cfg.level

    bumped = prev.model_copy(
        update={
            "capability_level": level,
            "model": cfg.model,
            "budget": Budget(
                tokens=cfg.max_tokens,
                cost_usd=cfg.max_cost,
                time=cfg.timeout_s,
            ),
            "timeout": cfg.timeout_s,
        }
    )
    roles = [bumped if r.role == role else r for r in plan.roles]
    return plan.model_copy(
        update={"roles": roles, "note": f"{plan.note}; bumped {role}→{level}"}
    )


__all__ = ["ALL_DEV_ROLES", "assess", "bump_for_retry", "plan"]
