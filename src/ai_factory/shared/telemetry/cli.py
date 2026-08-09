"""``telemetry`` query CLI (T032, SC-003, FR-016/018).

Queries telemetry for a run and emits it — redacted — as JSON (default) or
human form. The query is a local store read, well within SC-003's seconds
budget. Exit ``0`` when records exist; ``1`` (``EXIT_ERROR``) for an unknown
run with a diagnostic on stderr.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai_factory.shared.cli_util import (
    EXIT_ERROR,
    add_output_format_arg,
    emit,
    run,
    write_stderr,
    write_stdout,
)
from ai_factory.shared.telemetry.store import FileTelemetryStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="telemetry", description="Query run telemetry."
    )
    parser.add_argument("--run", required=True, help="run_id to query")
    parser.add_argument(
        "--store", default=".factory/telemetry", help="telemetry store directory"
    )
    add_output_format_arg(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return EXIT_ERROR if exc.code != 0 else 0

    store = FileTelemetryStore(Path(args.store))
    records = store.get(args.run)
    if not records:
        write_stderr(f"error: no telemetry for run '{args.run}'\n")
        return EXIT_ERROR

    if args.format == "human":
        parts = []
        for rec in records:
            lines = emit(rec, "human").splitlines()
            parts.extend(f"[{args.run}] {line}" for line in lines)
        write_stdout("\n".join(parts) + "\n")
    else:
        write_stdout(emit(records, "json"))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run(main))
