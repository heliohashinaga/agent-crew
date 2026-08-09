"""Telemetry emission + redaction (T030, FR-018, SC-010).

The emitter turns a telemetry record (see :mod:`record`) into a redacted,
serializable form. **Redaction happens before any emission** (FR-018): known
secret values and secret-LOOKING substrings are stripped so no secret ever
reaches a log, stream, or store (SC-010).
"""

from __future__ import annotations

import json
from typing import Any

from ai_factory.shared.secrets.loader import redact_mapping, redact_secret_like
from ai_factory.shared.telemetry.record import (
    DevRoleInvocation,
    SpecRoleInvocation,
    TelemetryRecord,
)

TelemetryCapable = TelemetryRecord | SpecRoleInvocation | DevRoleInvocation


def _to_dict(record: TelemetryCapable) -> dict[str, Any]:
    return record.model_dump()


def _scrub(value: Any, secrets: tuple[str, ...] = ()) -> Any:
    value = redact_mapping(value, list(secrets))
    if isinstance(value, dict):
        return {k: _scrub(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v, secrets) for v in value]
    if isinstance(value, str):
        return redact_secret_like(value)
    return value


def sanitize(record: TelemetryCapable, secrets: tuple[str, ...] = ()) -> dict[str, Any]:
    """Return a redacted dict for ``record`` (the emission-safe form)."""
    return _scrub(_to_dict(record), secrets)  # type: ignore[return-value]


def has_secret_like(record: TelemetryCapable) -> bool:
    """True if any string leaf contains a secret-LOOKING substring (SC-010)."""
    return _contains_secret(_to_dict(record))


def _contains_secret(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_secret(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_secret(v) for v in value)
    if isinstance(value, str):
        return redact_secret_like(value) != value
    return False


def render_record(
    record: TelemetryCapable,
    fmt: str = "json",
    *,
    secrets: tuple[str, ...] = (),
) -> str:
    """Render a redacted ``record`` as ``json`` (default) or ``human``.

    Secret values are removed before formatting, so the returned string is
    safe to write to any sink.
    """
    data = sanitize(record, secrets)
    if fmt == "human":
        return _human(data) + "\n"
    if fmt == "json":
        return json.dumps(data, indent=2, default=str) + "\n"
    raise ValueError(f"Unknown format: {fmt!r}")


def _human(value: Any, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{pad}{k}:")
                lines.append(_human(v, indent + 1))
            else:
                lines.append(f"{pad}{k}: {v}")
        return "\n".join(lines)
    if isinstance(value, list):
        parts = [_human(v, indent + 1) for v in value]
        out = []
        for part in parts:
            first, *rest = part.split("\n")
            out.append(f"{pad}- {first.lstrip()}")
            out.extend(rest)
        return "\n".join(out)
    return f"{pad}{value}"


__all__ = [
    "TelemetryCapable",
    "has_secret_like",
    "render_record",
    "sanitize",
]
