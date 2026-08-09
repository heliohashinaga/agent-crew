"""test-runner library CLI (T055, FR-011, FR-021, SC-013)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai_factory.dev_workflow.test_runner.runner import run_tests
from ai_factory.shared.cli_util import (
    EXIT_ERROR,
    add_output_format_arg,
    emit,
    run,
    write_stderr,
    write_stdout,
)
from ai_factory.shared.sandbox.runner import SandboxError, create_sandbox
from ai_factory.shared.telemetry.store import record_dev_invocation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="test-runner", description="Run tests in the sandbox."
    )
    parser.add_argument("--repo", required=True, help="Repo directory to test")
    parser.add_argument(
        "--sandbox", default="fake", choices=("fake", "docker"), help="sandbox provider"
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
        sandbox = create_sandbox(args.sandbox)
    except ValueError as exc:
        write_stderr(f"error: {exc}\n")
        return EXIT_ERROR

    try:
        result = run_tests(Path(args.repo), sandbox)
    except SandboxError as exc:
        write_stderr(f"error: {exc}\n")  # fail early: no runtime (SC-013)
        return EXIT_ERROR

    write_stdout(emit(result, args.format))
    record_dev_invocation(
        "test_runner",
        args.run_id or "test-runner-auto",
        args.telemetry,
        result="pass" if result.passed else "fail",
    )
    return 0 if result.passed else 4  # EXIT_DEV_FAILED


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run(main))
