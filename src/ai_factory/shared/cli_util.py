"""Shared CLI helpers (T015, contracts/library-cli-convention.md).

Every role/capability library CLI composes these helpers so the whole
factory follows one convention (constitution Principle II, FR-017, FR-018):

- Machine-readable JSON on stdout by default; ``--format human`` otherwise.
- Diagnostics on stderr.
- Meaningful, non-generic exit codes (``0`` success, others per workflow).
- Redaction of secret values *before* anything is emitted (FR-018).

An not-yet-wired telemetry hook is reserved here so later phases (US5) can
emit a ``TelemetryRecord`` per invocation through a single seam.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Iterable, Sequence
from typing import Any

from pydantic import BaseModel

from ai_factory.shared.secrets.loader import redact_mapping, redact_secret_like

# Meaningful exit codes shared by library CLIs and the workflow CLIs.
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_REJECTED = 2  # spec: review failed
EXIT_CLARIFICATION = 3  # spec: waiting on user
EXIT_DEV_FAILED = 4  # dev: implementation/review failed
EXIT_STOPPED_HUMAN = 5  # dev: re-planning failed, stop for a human


class CliError(RuntimeError):
    """An actionable CLI failure carrying a specific exit code."""

    def __init__(self, message: str, exit_code: int = EXIT_ERROR) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def add_output_format_arg(parser: argparse.ArgumentParser) -> None:
    """Add the standard ``--format {json,human}`` argument (default ``json``)."""
    parser.add_argument(
        "--format",
        choices=("json", "human"),
        default="json",
        help="Output format (default: json)",
    )


def _to_mapping(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return {k: _to_mapping(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_mapping(v) for v in value]
    return value


def emit(
    value: Any,
    fmt: str = "json",
    *,
    secrets: Sequence[str] | set[str] | None = None,
) -> str:
    """Render ``value`` for stdout, redacting secrets before ANY output.

    Returns a trailing-newline string. ``json`` yields pretty JSON; ``human``
    yields a compact key/value form. Unknown ``fmt`` raises :class:`ValueError`.
    """
    data = _to_mapping(value)
    if secrets:
        data = redact_mapping(data, list(secrets))
    # Always strip secret-LOOKING substrings from string leaves regardless of
    # the known-secret list (FR-018 auto-redaction).
    data = _scrub_secret_like(data)

    if fmt == "human":
        return _human_render(data) + "\n"
    if fmt == "json":
        if isinstance(data, BaseModel):
            return data.model_dump_json(indent=2) + "\n"
        return json.dumps(data, indent=2, default=_json_default) + "\n"
    raise ValueError(f"Unknown output format: {fmt!r}")


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "isoformat"):  # datetime / date / time
        return obj.isoformat()
    return str(obj)


def _scrub_secret_like(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _scrub_secret_like(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_secret_like(v) for v in value]
    if isinstance(value, str):
        return redact_secret_like(value)
    return value


def _human_render(value: Any, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{pad}{k}:")
                lines.append(_human_render(v, indent + 1))
            else:
                lines.append(f"{pad}{k}: {v}")
        return "\n".join(lines)
    if isinstance(value, list):
        if not value:
            return f"{pad}(empty)"
        parts = [_human_render(item, indent + 1) for item in value]
        return "\n".join(
            f"{pad}- {line.lstrip()}" if i == 0 else line
            for i, line in enumerate(parts)
        )
    return f"{pad}{value}"


def write_stdout(text: str, file: Any = None) -> None:
    """Write to stdout (the machine/human payload channel)."""
    print(text, end="", file=file if file is not None else sys.stdout)


def write_stderr(text: str, file: Any = None) -> None:
    """Write a diagnostic to stderr (never the payload channel)."""
    print(text, end="", file=file if file is not None else sys.stderr)


def run(
    cli_main: Callable[[list[str] | None], int], argv: list[str] | None = None
) -> int:
    """Execute a library ``cli_main`` and map handled failures to exit codes.

    ``cli_main`` receives ``argv`` (or ``None`` to let argparse read
    ``sys.argv``) and returns an exit code. Catches :class:`CliError` to
    report a specific code; unanticipated exceptions surface as exit ``1``.
    """
    try:
        code = cli_main(argv)
        return code if code is not None else EXIT_OK
    except CliError as exc:
        write_stderr(f"error: {exc}\n")
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        write_stderr(f"error: {exc}\n")
        return EXIT_ERROR


def redact_secrets(value: Any, secrets: Iterable[str]) -> Any:
    """Public alias for redacting known secret values from nested data."""
    return redact_mapping(value, list(secrets))


__all__ = [
    "CliError",
    "EXIT_CLARIFICATION",
    "EXIT_DEV_FAILED",
    "EXIT_ERROR",
    "EXIT_OK",
    "EXIT_REJECTED",
    "EXIT_STOPPED_HUMAN",
    "add_output_format_arg",
    "emit",
    "redact_secrets",
    "run",
    "write_stderr",
    "write_stdout",
]