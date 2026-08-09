"""technical-planner library CLI (T045, FR-007/008)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai_factory.dev_workflow.technical_planner.planner import produce_plan
from ai_factory.shared.cli_util import (
    EXIT_ERROR,
    add_output_format_arg,
    emit,
    run,
    write_stderr,
    write_stdout,
)
from ai_factory.shared.spec_store.models import SpecVersion
from ai_factory.shared.telemetry.store import record_dev_invocation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="technical-planner", description="Plan a feature technically."
    )
    parser.add_argument(
        "--spec-file", required=True, help="Path to an approved SpecVersion JSON"
    )
    parser.add_argument("--run-id", default="", help="run_id for telemetry recording")
    parser.add_argument(
        "--telemetry", default=".factory/telemetry", help="telemetry store directory"
    )
    add_output_format_arg(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return EXIT_ERROR if exc.code != 0 else 0

    try:
        spec = SpecVersion.model_validate_json(
            Path(args.spec_file).read_text(encoding="utf-8")
        )
    except OSError, ValueError:
        write_stderr(f"error: cannot read spec from {args.spec_file}\n")
        return EXIT_ERROR

    write_stdout(emit(produce_plan(spec), args.format))
    record_dev_invocation(
        "technical_planner", args.run_id or "technical-planner-auto", args.telemetry
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run(main))
