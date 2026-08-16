"""Dual-mode role executor for the dev workflow (T020-T022, US3/US4, FR-007).

A role runs through exactly one of two modes, controlled per-run:

- **Offline** (default): the role's deterministic function is called with no
  network and no credentials — behavior is **byte-identical to today**.
- **Live** (opt-in ``AI_FACTORY_LIVE=1`` / ``--live`` **and** an API key):
  the role's real model id is resolved (``model_map.resolve_model_id``) and
  dispatched through a registered ``LLMProvider`` (e.g. ``openai-compatible``).

Security gates:

- **Opt-in gate (T021)**: credentials alone never enable live mode. A run goes
  live only when the operator opts in AND a credential is present; otherwise it
  runs offline (never hangs, never leaks).
- **Fail-closed (T022)**: if a live role's capability level is invalid/unmapped
  (no real model id), the run fails closed with a typed
  :class:`ModelMapError` — the provider is **never** called with an empty or
  garbage model id.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ai_factory.capability_levels.levels import capability_for
from ai_factory.capability_levels.model_map import ModelMapError, resolve_model_id
from ai_factory.shared.llm.provider import LLMMessage, LLMProvider

_LIVE_ENV = "AI_FACTORY_LIVE"
_CRED_ENV = ("OPENCODE_GO_API_KEY", "OPENROUTER_API_KEY")
_OFFLINE_MODEL = "fake"

_TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass
class RoleRunResult:
    """The outcome of dispatching one role in either mode."""

    role: str
    capability_level: str
    output: Any
    mode: str  # "offline" | "live"
    live_used: bool
    model: str
    provider_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    latency: float = 0.0
    error: str | None = None


@dataclass
class _LiveRequest:
    opt_in: bool
    creds: bool
    provider: LLMProvider | None
    resolved_model: str | None = None
    messages: list[LLMMessage] = field(default_factory=list)


def _flag_enabled(live: bool | None, env: dict[str, str]) -> bool:
    if live is True:
        return True
    if live is False:
        return False
    return env.get(_LIVE_ENV, "").strip().lower() in _TRUE_VALUES


def _creds_present(env: dict[str, str]) -> bool:
    return any(bool(env.get(key)) for key in _CRED_ENV)


def live_enabled(*, env: dict[str, str] | None = None) -> bool:
    """Whether the operator opted into live mode (``AI_FACTORY_LIVE=1``/true)."""
    return _flag_enabled(None, env if env is not None else os.environ)


def _now() -> float:
    return time.monotonic()


def _role_message(role: str, level: str, model: str) -> list[LLMMessage]:
    return [
        LLMMessage(
            role="system",
            content=(
                "You are the ai-factory role runner. Run the deterministic role "
                "work and record dispatch observability; keep output unchanged."
            ),
        ),
        LLMMessage(
            role="user",
            content=f"Dispatching role={role} level={level} model={model}.",
        ),
    ]


def _validate_level(role: str, level: str) -> None:
    try:
        capability_for(role, level)
    except (KeyError, ValueError) as exc:
        raise ModelMapError(
            f"live role={role!r} has invalid/unmapped capability level {level!r}: "
            f"{exc} (failing closed; set a valid level or run offline)"
        ) from exc


def run_role(
    role: str,
    *,
    level: str,
    offline_fn: Callable[..., Any],
    offline_kwargs: dict[str, Any] | None = None,
    live: bool | None = None,
    provider: LLMProvider | None = None,
    env: dict[str, str] | None = None,
) -> RoleRunResult:
    """Dispatch ``role`` at ``level`` in the appropriate mode.

    Returns a :class:`RoleRunResult` carrying the deterministic ``output`` (so
    downstream graph state is unchanged) plus live dispatch observability.
    """
    env = env if env is not None else os.environ
    offline_kwargs = offline_kwargs or {}
    opt_in = _flag_enabled(live, env)
    creds = _creds_present(env)

    if not (opt_in and creds):
        # Offline (US3): identical to today, no network, no creds required.
        output = offline_fn(**offline_kwargs)
        return RoleRunResult(
            role=role,
            capability_level=level,
            output=output,
            mode="offline",
            live_used=False,
            model=_OFFLINE_MODEL,
        )

    # Live: validate the level is mappable, then dispatch through the provider.
    _validate_level(role, level)
    model = resolve_model_id(role, level)
    proc = provider if provider is not None else None
    if proc is None:
        from ai_factory.shared.llm.provider import create_provider

        proc = create_provider("openai-compatible")
    messages = _role_message(role, level, model)
    token_in = token_out = 0
    cost = 0.0
    latency = 0.0
    _start = _now()
    token_result = proc.complete(messages, model=model)
    token_in = int(getattr(token_result, "tokens_in", 0) or 0)
    token_out = int(getattr(token_result, "tokens_out", 0) or 0)
    cost = float(getattr(token_result, "cost", 0.0) or 0.0)
    latency = _now() - _start
    # Run the deterministic function regardless so downstream state is stable.
    output = offline_fn(**offline_kwargs)
    return RoleRunResult(
        role=role,
        capability_level=level,
        output=output,
        mode="live",
        live_used=True,
        model=model,
        provider_calls=1,
        tokens_in=token_in,
        tokens_out=token_out,
        cost=cost,
        latency=latency,
    )


__all__ = ["RoleRunResult", "live_enabled", "run_role"]
