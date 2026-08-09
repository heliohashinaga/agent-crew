"""code-reviewer library CLI (T051, FR-011)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai_factory.dev_workflow.code_reviewer.reviewer import review
from ai_factory.dev_workflow.code_worker.worker import CodeWorkProduct
from ai_factory.dev_workflow.technical_planner.planner import TechnicalPlan
from ai_factory.shared.cli_util import (
    EXIT_ERROR,
    EXIT_REJECTED,
    add_output_format_arg,
    emit,
    run,
    write_stderr,
    write_stdout,
)
from ai_factory.shared.telemetry.store import record_dev_invocation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="code-reviewer", description="Review code-worker output."
    )
    parser.add_argument(
        "--plan-file", required=True, help="Path to a TechnicalPlan JSON"
    )
    parser.add_argument(
        "--product-file", required=True, help="Path to a CodeWorkProduct JSON"
    )
    parser.add_argument("--repo", required=True, help="Repo directory to inspect")
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
        product = CodeWorkProduct.model_validate_json(
            Path(args.product_file).read_text(encoding="utf-8")
        )
    except OSError, ValueError:
        write_stderr("error: cannot read plan/product input files\n")
        return EXIT_ERROR

    verdict = review(product, plan, Path(args.repo))
    write_stdout(emit(verdict, args.format))
    record_dev_invocation(
        "code_reviewer",
        args.run_id or "code-reviewer-auto",
        args.telemetry,
        result="pass" if verdict.approved else "fail",
    )
    return 0 if verdict.approved else EXIT_REJECTED


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run(main))
