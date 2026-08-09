"""test-engineer library CLI (T053, FR-011)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai_factory.dev_workflow.technical_planner.planner import TechnicalPlan
from ai_factory.dev_workflow.test_engineer.engineer import build_test_suite
from ai_factory.shared.cli_util import (
    EXIT_ERROR,
    add_output_format_arg,
    emit,
    run,
    write_stderr,
    write_stdout,
)
from ai_factory.shared.telemetry.store import record_dev_invocation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="test-engineer", description="Produce a test suite."
    )
    parser.add_argument(
        "--plan-file", required=True, help="Path to a TechnicalPlan JSON"
    )
    parser.add_argument("--repo", required=True, help="Repo directory to write into")
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
        plan = TechnicalPlan.model_validate_json(
            Path(args.plan_file).read_text(encoding="utf-8")
        )
    except OSError, ValueError:
        write_stderr(f"error: cannot read plan from {args.plan_file}\n")
        return EXIT_ERROR

    product = build_test_suite(plan, Path(args.repo))
    write_stdout(emit(product, args.format))
    record_dev_invocation(
        "test_engineer", args.run_id or "test-engineer-auto", args.telemetry
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run(main))
