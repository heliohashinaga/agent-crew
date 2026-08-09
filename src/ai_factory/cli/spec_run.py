"""``spec-run`` workflow CLI (T022, contracts/spec-run-cli.md).

A thin CLI over the spec workflow StateGraph. Composes the role libraries,
the graph, and the local spec store — it contains no domain logic of its own.

Exit codes (per the contract):
- ``0`` — spec approved and published.
- ``2`` — spec rejected after bounded review (``EXIT_REJECTED``).
- ``3`` — needs clarification / human deferred (``EXIT_CLARIFICATION``).

The human-approval gate (FR-005) is interactive by default: the CLI resumes
the ``interrupt`` with the user's answer. ``--auto-approve`` disables the
prompt for automation/testing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from langgraph.types import Command

from ai_factory.shared.cli_util import (
    EXIT_CLARIFICATION,
    EXIT_ERROR,
    EXIT_REJECTED,
    add_output_format_arg,
    emit,
    run,
    write_stderr,
    write_stdout,
)
from ai_factory.shared.spec_store.models import FeatureRequest
from ai_factory.shared.spec_store.store import FileSpecStore
from ai_factory.spec_workflow.graph import build_spec_graph

DEFAULT_STORE = ".factory/specs"
PROMPT = "Approve this spec version? (continue to publish)"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spec-run", description="Run the Specification Workflow."
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--request", help="The natural-language feature request")
    src.add_argument("--stdin", action="store_true", help="Read the request from stdin")
    parser.add_argument("--scope", default="", help="Optional target scope")
    parser.add_argument(
        "--constraint",
        action="append",
        default=[],
        help="Scope constraint (repeatable)",
    )
    parser.add_argument("--store", default=DEFAULT_STORE, help="Spec store directory")
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Approve without prompting (automation)",
    )
    add_output_format_arg(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return EXIT_ERROR if exc.code != 0 else 0

    request_text = args.request
    if args.stdin:
        request_text = sys.stdin.read().strip()
    if not request_text:
        write_stderr("error: --request is empty or no input on stdin\n")
        return EXIT_ERROR

    request = FeatureRequest(raw_text=request_text, constraints=list(args.constraint))
    store = FileSpecStore(Path(args.store))
    app = build_spec_graph(store)
    config = {"configurable": {"thread_id": f"spec-run-{id(request)}"}}

    state: dict = {
        "request": request,
        "review_rounds": 0,
        "feedback": "",
        "spec_run_id": f"spec-run-{id(request)}",
        "outcome": "drafting",
        "spec": None,
    }

    result = app.invoke(state, config)
    outcome = result["outcome"]

    # Human-approval gate: pause/resume the interrupt (FR-005).
    if outcome == "drafting" and "__interrupt__" in result:
        approved = args.auto_approve or _prompt_human()
        result = app.invoke(Command(resume=bool(approved)), config)
        outcome = result["outcome"]

    spec = result.get("spec")
    write_stdout(
        emit(spec, args.format) if spec else emit({"outcome": outcome}, args.format)
    )

    if outcome == "approved":
        return 0
    if outcome == "rejected":
        return EXIT_REJECTED
    return EXIT_CLARIFICATION


def _prompt_human() -> bool:
    """Prompt for approval on the terminal; non-TTY defaults to no."""
    try:
        if not sys.stdin.isatty():
            return False
        answer = input(f"{PROMPT} [y/N] ").strip().lower()
    except EOFError, OSError, RuntimeError:
        return False
    return answer in ("y", "yes")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run(main))
