"""security-reviewer library CLI (T057, FR-020)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai_factory.dev_workflow.security_reviewer.reviewer import review
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
        prog="security-reviewer", description="Scan produced files."
    )
    parser.add_argument("--repo", required=True, help="Repo directory to scan")
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

    repo = Path(args.repo)
    if not repo.exists():
        write_stderr(f"error: repo {repo} does not exist\n")
        return EXIT_ERROR

    verdict = review(repo)
    write_stdout(emit(verdict, args.format))
    record_dev_invocation(
        "security_reviewer",
        args.run_id or "security-reviewer-auto",
        args.telemetry,
        result="pass" if verdict.approved else "fail",
    )
    return 0 if verdict.approved else EXIT_REJECTED


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run(main))
