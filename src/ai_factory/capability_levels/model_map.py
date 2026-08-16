"""Per-role capability-level model id resolution (T010, US4, FR-010).

Resolves a ``(role, capability_level)`` pair to a **real, provider-prefixed
model id** (e.g. ``opencode-go/deepseek-v4-flash``) so the dual-mode live
executor can dispatch each role with the right model on the right provider.

Resolution precedence (low → high):

1. **code defaults** — a documented default id per model tier;
2. **model-map.json** — an optional, commit-safe nested ``role → level → id``
   mapping (API keys are **never** stored here; FR-018).
3. **env** — tier-flattened overrides ``MODEL_FAST_CHEAP`` /
   ``MODEL_CAPABLE`` / ``MODEL_DEEP``, with ``MODEL_DEFAULT`` as the global
   fallback.

Both role axes are covered via a level → tier mapping:

- task ``simple``/``shallow`` → ``fast-cheap``; ``standard`` → ``capable``;
  ``complex``/``deep`` → ``deep``.

And both providers (``opencode-go`` / ``openrouter``) are usable
**simultaneously** — each resolved id carries its provider prefix.

An empty/garbage resolved id fails closed (:class:`ModelMapError`) rather than
letting a role dispatch with a bad model id (fail-closed, never a silent empty).
"""

from __future__ import annotations

import json
import os
import pkgutil
from pathlib import Path
from typing import Any

from ai_factory.capability_levels.levels import (
    FIXED_ROLES,
    REVIEW_ROLES,
    TASK_ROLES,
)

KNOWN_ROLES = frozenset((*TASK_ROLES, *REVIEW_ROLES, *FIXED_ROLES))

# Provider prefix → API-key/base-url env pair (mirrors the provider module).
PROVIDER_PREFIXES = ("opencode-go", "openrouter")

# Documented default model id per tier (authoritative; operators override via
# model-map.json / env). Each is provider-prefixed (FR-010).
CODE_DEFAULTS: dict[str, str] = {
    "fast-cheap": "opencode-go/deepseek-v4-flash",
    "capable": "openrouter/qwen/qwen3.8-max",
    "deep": "opencode-go/kimi-k3",
}
_DEFAULT_ID = CODE_DEFAULTS["fast-cheap"]

# Level label → model tier (covers both task and review axes).
_LEVEL_TO_TIER = {
    "simple": "fast-cheap",
    "shallow": "fast-cheap",
    "standard": "capable",
    "complex": "deep",
    "deep": "deep",
}
# Tier → env override var.
_TIER_ENV = {
    "fast-cheap": "MODEL_FAST_CHEAP",
    "capable": "MODEL_CAPABLE",
    "deep": "MODEL_DEEP",
}
_ENV_DEFAULT = "MODEL_DEFAULT"

# Package-shipped default model-map (no secrets; commit-safe). Loaded lazily.
_DEFAULT_JSON_PATH = "model-map.json"


class ModelMapError(ValueError):
    """Raised when a resolved model id is empty/garbage (fail-closed, FR-010)."""


def code_default(tier: str) -> str:
    """The documented default model id for a model *tier*.

    ``tier`` is one of ``fast-cheap`` / ``capable`` / ``deep``.
    """
    return CODE_DEFAULTS[tier]


def default_model_id() -> str:
    """The global default (fallback for unknown roles/levels)."""
    return _DEFAULT_ID


def _is_valid_id(model_id: str) -> bool:
    if not model_id or not model_id.strip():
        return False
    prefix = model_id.strip().split("/", 1)[0]
    return prefix in PROVIDER_PREFIXES


def _load_pkg_default_map() -> dict[str, Any]:
    """Load the shipped ``model-map.json`` (or an empty map if the resource is gone)."""
    try:
        raw = pkgutil.get_data(__name__, _DEFAULT_JSON_PATH)
    except FileNotFoundError:
        return {}
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def resolve_model_id(
    role: str,
    level: str,
    *,
    model_map: dict[str, Any] | None = None,
) -> str:
    """Resolve a ``(role, level)`` to a provider-prefixed model id.

    Precedence: **code defaults < model-map.json < env**; ``MODEL_DEFAULT`` is
    the final fallback. Unknown roles/levels fall back to the global default.
    """
    resolved: str | None = None
    tier = _LEVEL_TO_TIER.get(level)
    role_known = role in KNOWN_ROLES

    table = model_map if model_map is not None else _load_pkg_default_map()
    roles = table.get("roles") or {}
    json_default = table.get("default")

    # 1. Env override, flattened by LEVEL tier (applies regardless of role).
    if tier is not None:
        env_var = _TIER_ENV[tier]
        env_val = os.environ.get(env_var)
        if env_val:
            resolved = env_val

    # 2. Known role + valid level: model-map.json cell, then code default.
    if resolved is None and role_known and tier is not None:
        cell = (roles.get(role) or {}).get(level)
        if cell is not None:
            # An explicitly-given cell must be a valid provider-prefixed id;
            # empty/garbage fails closed rather than dispatching a bad id.
            if not cell or not cell.strip():
                raise ModelMapError(
                    f"model-map.json gives an invalid (empty/garbage) id for "
                    f"role={role!r} level={level!r}: {cell!r}"
                )
            resolved = cell
        else:
            resolved = CODE_DEFAULTS[tier]

    # 3. Unknown role/level: MODEL_DEFAULT env, then JSON global default,
    #    then the code default.
    if resolved is None:
        if os.environ.get(_ENV_DEFAULT):
            resolved = os.environ[_ENV_DEFAULT]
        elif json_default and json_default.strip():
            resolved = json_default
        else:
            resolved = _DEFAULT_ID

    # Fail-closed: never dispatch with an empty/garbage id.
    if not _is_valid_id(resolved):
        raise ModelMapError(
            f"model-map resolved an invalid model id for role={role!r} level={level!r}: "  # noqa: E501
            f"{resolved!r} (expected a provider-prefixed id like "
            f"'opencode-go/<model>' or 'openrouter/<model>')"
        )
    return resolved.strip()


def export_default_model_map_json() -> dict[str, Any]:
    """Serialize the current default map for operators to copy & customize."""
    return {
        "roles": {
            role: {
                level: resolve_model_id(role, level)
                for level in _tiers_for_role(role)
            }
            for role in KNOWN_ROLES
        },
        "default": _DEFAULT_ID,
    }


def _tiers_for_role(role: str) -> list[str]:
    from ai_factory.capability_levels.levels import level_order

    return level_order(role)


def ensure_default_json_on_disk(target: Path) -> None:
    """Write a commit-safe ``model-map.json`` to ``target`` (no secrets)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(export_default_model_map_json(), indent=2) + "\n",
        encoding="utf-8",
    )
