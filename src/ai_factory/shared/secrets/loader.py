"""Secret-store credential loading and secret-value redaction (T009, FR-018).

FR-018 requires that credentials load only from the environment or a
dedicated secret store (never from committed config) and that secret-looking
values are auto-redacted from all logs/telemetry before emission.

This module provides:

- :class:`SecretSource` — the pluggable credential source protocol.
- :class:`EnvSecretSource` — the default source backed by ``os.environ``.
- :func:`load_credential` — read a credential from env, falling back to a
  secret source. Never reads committed config.
- :func:`redact` / :func:`redact_mapping` — replace known secret VALUES with
  a redaction marker (applied before any emission).
- :func:`redact_secret_like` — heuristic pass that catches secret-LOOKING
  values (e.g. ``Bearer <token>``, ``password=...`` assignments) even when
  the exact secret value is not on the known list.
"""

from __future__ import annotations

import os
import re
from typing import Any, Protocol

REDACTED = "[REDACTED]"

# Secret-looking patterns (FR-018 auto-redaction). Conservative, value-local
# so plain prose is left untouched. Substitution keeps the label ("Bearer",
# "pw=...") and redacts only the token material.
_SECRET_LIKE_RE = re.compile(
    r"(?i)(?:"
    r"(bearer)\s+([A-Za-z0-9._~+/=-]{8,})"
    r"|"
    r"((?:api[_-]?key|password|passwd|pw|pwd|secret|token|access[_-]?token|"
    r"credential|auth[_-]?token))[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9._~+/=-]{8,})"
    r")"
)


_REDACTED = "[REDACTED]"


def _redact_secret_like_match(match: re.Match[str]) -> str:
    bearer_label = match.group(1)
    if bearer_label:
        return f"{bearer_label} {_REDACTED}"
    key = match.group(3)
    return f"{key}={_REDACTED}"


class SecretSource(Protocol):
    """A credential source: the environment or a dedicated secret store."""

    def get(self, name: str) -> str | None:
        """Return the named credential, or ``None`` if absent."""
        ...


class EnvSecretSource:
    """Default credential source: ``os.environ`` (FR-018)."""

    def get(self, name: str) -> str | None:
        return os.environ.get(name)


def load_credential(
    name: str,
    *,
    source: SecretSource | None = None,
    required: bool = True,
) -> str | None:
    """Load a credential by ``name``.

    The environment is preferred; ``source`` (a secret store) is used as a
    fallback. Never reads committed configuration.

    Raises ``RuntimeError`` when ``required`` and the credential is absent.
    """
    value = os.environ.get(name)
    if value is None and source is not None:
        value = source.get(name)
    if value is None and required:
        raise RuntimeError(
            f"Required credential '{name}' not found in environment or secret store"
        )
    return value


def redact(text: str, secrets: list[str] | tuple[str, ...] | set[str]) -> str:
    """Replace every known secret value in ``text`` with ``[REDACTED]``."""
    out = text
    for secret in secrets:
        if not secret:
            continue
        out = out.replace(secret, REDACTED)
    return out


def redact_mapping(value: Any, secrets: list[str] | tuple[str, ...] | set[str]) -> Any:
    """Recursively redact known secret values inside dicts/lists.

    Returns a new structure; the input is not mutated.
    """
    if isinstance(value, dict):
        return {k: redact_mapping(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_mapping(v, secrets) for v in value]
    if isinstance(value, tuple):
        return tuple(redact_mapping(v, secrets) for v in value)
    if isinstance(value, str):
        return redact(value, list(secrets))
    return value


def redact_secret_like(text: str) -> str:
    """Redact secret-LOOKING substrings (``Bearer <tok>``, ``password=...``).

    Value-local by design (requires 8+ characters of token material) so
    ordinary prose is not mangled.
    """
    return _SECRET_LIKE_RE.sub(_redact_secret_like_match, text)


__all__ = [
    "EnvSecretSource",
    "REDACTED",
    "SecretSource",
    "load_credential",
    "redact",
    "redact_mapping",
    "redact_secret_like",
]
