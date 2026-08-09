"""orchestrator library CLI (T038, FR-009).

Reads an approved spec (JSON) and emits its :class:`ExecutionPlan` in JSON
(default) or human form. Pure decision layer — no specialized work.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai_factory.dev_workflow.orchestrator.orchestrator import plan
from ai_factory.shared.cli_util import (
    EXIT_ERROR,
    add_output_format_arg,
    emit,
    run,
    write_stderr,
    write_stdout,
)
from ai_factory.shared.spec_store.models import SpecVersion


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orchestrator", description="Plan execution per role."
    )
    parser.add_argument(
        "--spec-file", required=True, help="Path to an approved SpecVersion JSON"
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

    write_stdout(emit(plan(spec), args.format))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run(main))
