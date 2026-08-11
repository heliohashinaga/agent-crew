"""``ai-factory-researcher`` command-line interface (researcher role).

Library-First CLI for the mono-capacity ``researcher`` role: query the
repository (``repo``, deterministic) or the web (``web``, Option D
multi-angle best-per-angle in v1) and print a concise, sourced
``ResearchResult`` to stdout (JSON by default or human-readable).
"""

from __future__ import annotations

import argparse

from ai_factory.researcher.agent import ResearcherWebError, lookup
from ai_factory.researcher.models import ResearchResult
from ai_factory.shared.cli_util import (
    EXIT_DEV_FAILED,
    EXIT_ERROR,
    EXIT_OK,
    CliError,
    add_output_format_arg,
    emit,
    run,
    write_stdout,
)
from ai_factory.shared.telemetry.store import record_dev_invocation


def build_parser() -> argparse.ArgumentParser:
    """Build the ``ai-factory-researcher`` argument parser."""
    parser = argparse.ArgumentParser(prog="ai-factory-researcher")
    parser.add_argument(
        "--scope",
        choices=["repo", "web"],
        default="repo",
        help="source to query: 'repo' (deterministic) or 'web' (v1).",
    )
    parser.add_argument(
        "--query", help="natural-language query (required, non-empty)."
    )
    parser.add_argument(
        "--run-id", default="", help="run id for telemetry (default auto)."
    )
    parser.add_argument(
        "--telemetry", action="store_true", help="record a telemetry record."
    )
    parser.add_argument(
        "--roots",
        nargs="*",
        default=[],
        help="repo root(s) to scan (required for repo scope).",
    )
    add_output_format_arg(parser)
    return parser


def cmd(args: argparse.Namespace) -> int:
    """Run one researcher lookup and print the ``ResearchResult`` (FR-007)."""
    if not args.query or not args.query.strip():
        raise CliError("--query is required and non-empty.", exit_code=EXIT_ERROR)

    if args.scope == "repo" and not args.roots:
        raise CliError("--roots is required for --scope repo.", exit_code=EXIT_ERROR)

    try:
        result: ResearchResult = lookup(
            args.query,
            roots=list(args.roots),
            scopes=[args.scope],
        )
    except ResearcherWebError as exc:
        raise CliError(str(exc), exit_code=EXIT_DEV_FAILED) from exc

    # FR-008: per-role telemetry (mono-capacity -> constant/empty capability).
    if args.telemetry:
        record_dev_invocation(
            role="researcher",
            run_id=args.run_id or f"researcher-{id(result)}",
            result="pass",
            capability_level="",  # mono-capacity; not a variable level (FR-006)
            model="",
        )

    payload = result.model_dump()
    write_stdout(emit(payload, args.format))
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: parse args, run one lookup, return exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return cmd(args)


if __name__ == "__main__":  # pragma: no cover
    import sys

    sys.exit(run(main))
