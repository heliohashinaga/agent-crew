"""Capability levels per role (T036, FR-010, R9).

Two axes (FR-010):
- **task** roles (Code Worker, Test Engineer): ``simple → standard → complex``
- **review** roles (Code Reviewer, Security Reviewer): ``shallow → standard → deep``

Higher levels strictly increase depth, retro context, iterations, token
budget and tool access. :func:`bump_level` implements the FR-015 retry rule
(a retry raises the capability level at least one step, capped at max).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

TASK_AXIS = ("simple", "standard", "complex")
REVIEW_AXIS = ("shallow", "standard", "deep")

TASK_ROLES = ("code_worker", "test_engineer")
REVIEW_ROLES = ("code_reviewer", "security_reviewer")
FIXED_ROLES = ("technical_planner", "orchestrator", "test_runner")


class LevelConfig(BaseModel):
    """A named capability level's resource/depth profile (R9)."""

    level: str
    model: str
    max_tokens: int = 0
    max_cost: float = 0.0
    timeout_s: float = 0.0
    validation_depth: float = Field(ge=0, le=1)
    retro_context: int = 0
    max_iterations: int = 1
    tool_access: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> LevelConfig:
        if self.max_tokens < 0 or self.max_cost < 0 or self.timeout_s < 0:
            raise ValueError("budgets and timeouts must be non-negative")
        return self


def _cfg(
    level: str,
    model: str,
    max_tokens: int,
    max_cost: float,
    timeout_s: float,
    validation_depth: float,
    retro_context: int,
    max_iterations: int,
    tool_access: list[str],
) -> LevelConfig:
    return LevelConfig(
        level=level,
        model=model,
        max_tokens=max_tokens,
        max_cost=max_cost,
        timeout_s=timeout_s,
        validation_depth=validation_depth,
        retro_context=retro_context,
        max_iterations=max_iterations,
        tool_access=tool_access,
    )


def _task(
    level: str,
    model: str,
    tokens: int,
    cost: float,
    timeout: float,
    depth: float,
    retro: int,
    iters: int,
    tools: list[str],
) -> LevelConfig:
    return _cfg(level, model, tokens, cost, timeout, depth, retro, iters, tools)


_TASK_TOOLS: dict[str, list[str]] = {
    "simple": ["read", "write", "test"],
    "standard": ["read", "write", "test", "search"],
    "complex": ["read", "write", "test", "search", "refactor"],
}
_REVIEW_TOOLS: dict[str, list[str]] = {
    "shallow": ["read"],
    "standard": ["read", "search"],
    "deep": ["read", "search", "security-scan"],
}

CAPABILITIES: dict[str, dict[str, LevelConfig]] = {
    "code_worker": {
        "simple": _task(
            "simple", "fast-cheap", 2048, 0.05, 60, 0.3, 0, 1, _TASK_TOOLS["simple"]
        ),
        "standard": _task(
            "standard", "capable", 8192, 0.2, 180, 0.6, 1, 2, _TASK_TOOLS["standard"]
        ),
        "complex": _task(
            "complex", "deep", 16384, 0.6, 420, 0.9, 2, 3, _TASK_TOOLS["complex"]
        ),
    },
    "test_engineer": {
        "simple": _task(
            "simple", "fast-cheap", 2048, 0.05, 60, 0.3, 0, 1, _TASK_TOOLS["simple"]
        ),
        "standard": _task(
            "standard", "capable", 8192, 0.2, 180, 0.6, 1, 2, _TASK_TOOLS["standard"]
        ),
        "complex": _task(
            "complex", "deep", 16384, 0.6, 420, 0.9, 2, 3, _TASK_TOOLS["complex"]
        ),
    },
    "code_reviewer": {
        "shallow": _task(
            "shallow", "fast-cheap", 2048, 0.05, 60, 0.3, 0, 1, _REVIEW_TOOLS["shallow"]
        ),
        "standard": _task(
            "standard", "capable", 8192, 0.2, 180, 0.6, 1, 2, _REVIEW_TOOLS["standard"]
        ),
        "deep": _task(
            "deep", "deep", 16384, 0.6, 420, 0.9, 2, 3, _REVIEW_TOOLS["deep"]
        ),
    },
    "security_reviewer": {
        "shallow": _task(
            "shallow", "fast-cheap", 2048, 0.05, 60, 0.3, 0, 1, _REVIEW_TOOLS["shallow"]
        ),
        "standard": _task(
            "standard", "capable", 8192, 0.2, 180, 0.6, 1, 2, _REVIEW_TOOLS["standard"]
        ),
        "deep": _task(
            "deep", "deep", 16384, 0.6, 420, 0.9, 2, 3, _REVIEW_TOOLS["deep"]
        ),
    },
    # Fixed-capability roles: a single standard level.
    "technical_planner": {
        "standard": _task(
            "standard",
            "capable",
            8192,
            0.2,
            180,
            0.6,
            1,
            2,
            ["read", "search", "write"],
        )
    },
    "orchestrator": {
        "standard": _task(
            "standard", "fast-cheap", 4096, 0.1, 90, 0.5, 1, 1, ["manage", "read"]
        )
    },
    "test_runner": {
        "standard": _task(
            "standard", "fast-cheap", 4096, 0.1, 90, 0.5, 1, 1, ["test", "read"]
        )
    },
}


def level_order(role: str) -> list[str]:
    """The capability axis for a role (task or review); raises for unknown roles."""
    if role in TASK_ROLES:
        return list(TASK_AXIS)
    if role in REVIEW_ROLES:
        return list(REVIEW_AXIS)
    if role in FIXED_ROLES:
        return ["standard"]
    raise KeyError(f"unknown role {role!r}")


def capability_for(role: str, level: str) -> LevelConfig:
    """The :class:`LevelConfig` for ``role`` at ``level`` (FR-010, R9)."""
    axis = level_order(role)
    if level not in axis:
        raise ValueError(f"level {level!r} is not on the {role} axis {axis}")
    return CAPABILITIES[role][level]


def default_level(role: str) -> str:
    """The default starting level for ``role`` (middle of its axis)."""
    axis = level_order(role)
    return axis[len(axis) // 2]


def bump_level(role: str, level: str) -> LevelConfig:
    """Raise the capability level one step (FR-015); capped at the axis max.

    Raising a retry's level adds depth, context and budget through the
    :class:`LevelConfig` selected here.
    """
    axis = level_order(role)
    idx = axis.index(level)
    next_level = axis[min(idx + 1, len(axis) - 1)]
    return capability_for(role, next_level)


__all__ = [
    "CAPABILITIES",
    "FIXED_ROLES",
    "LevelConfig",
    "REVIEW_AXIS",
    "REVIEW_ROLES",
    "TASK_AXIS",
    "TASK_ROLES",
    "bump_level",
    "capability_for",
    "default_level",
    "level_order",
]
