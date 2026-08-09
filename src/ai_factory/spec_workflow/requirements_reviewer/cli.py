"""requirements-reviewer library CLI (T019, contracts/library-cli-convention.md).

Reads a draft :class:`SpecVersion` (JSON) and emits a :class:`ReviewVerdict`
in JSON (default) or human form. Exit ``0`` on approve, ``2`` on reject
(``EXIT_REJECTED``), non-generic otherwise.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai_factory.shared.cli_util import (
    EXIT_ERROR,
    EXIT_REJECTED,
    add_output_format_arg,
    emit,
    run,
    write_stderr,
    write_stdout,
)
from ai_factory.shared.spec_store.models import SpecVersion
from ai_factory.spec_workflow.requirements_reviewer.reviewer import review


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="requirements-reviewer", description="Review a draft spec."
    )
    parser.add_argument(
        "--spec-file", required=True, help="Path to a SpecVersion JSON file"
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

    verdict = review(spec)
    write_stdout(emit(verdict, args.format))
    return 0 if verdict.approved else EXIT_REJECTED


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run(main))
