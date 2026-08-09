"""spec-agent library CLI (T017, contracts/library-cli-convention.md).

Emits a draft :class:`SpecVersion` for a feature request in JSON (default)
or human form. Diagnostics go to stderr; the payload to stdout.
"""

from __future__ import annotations

import argparse
import sys

from ai_factory.shared.cli_util import (
    EXIT_ERROR,
    add_output_format_arg,
    emit,
    run,
    write_stdout,
)
from ai_factory.shared.spec_store.models import FeatureRequest
from ai_factory.spec_workflow.spec_agent.agent import draft_spec


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spec-agent", description="Draft a feature spec."
    )
    parser.add_argument(
        "--request", required=True, help="The natural-language feature request"
    )
    parser.add_argument(
        "--constraint",
        action="append",
        default=[],
        help="A scope constraint (repeatable)",
    )
    add_output_format_arg(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        # argparse exits 2 for usage errors; surface as EXIT_ERROR.
        return EXIT_ERROR if exc.code != 0 else 0

    request = FeatureRequest(raw_text=args.request, constraints=list(args.constraint))
    spec = draft_spec(request)
    write_stdout(emit(spec, args.format))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run(main))
