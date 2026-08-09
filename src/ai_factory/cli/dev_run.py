"""``dev-run`` workflow CLI (T066, contracts/dev-run-cli.md).

A thin CLI over the Development Workflow StateGraph. Consumes an approved
spec BY REFERENCE (``spec_version_id`` + ``spec_run_id``) and drives the
pipeline to a merge-ready PR.

Exit codes (per the contract):
- ``0`` — delivered (PR opened, never auto-merged, FR-012).
- ``4`` — failed delivery (review/tests/security failed bounded rework).
- ``5`` — stopped-human (reserved: re-planning failed; not reachable with
  the deterministic graph).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai_factory.dev_workflow.graph import build_dev_graph
from ai_factory.dev_workflow.models import Budget
from ai_factory.shared.cli_util import (
    EXIT_DEV_FAILED,
    EXIT_ERROR,
    EXIT_OK,
    EXIT_STOPPED_HUMAN,
    add_output_format_arg,
    emit,
    run,
    write_stderr,
    write_stdout,
)
from ai_factory.shared.git_host.client import create_git_host
from ai_factory.shared.sandbox.runner import create_sandbox
from ai_factory.shared.spec_store.store import FileSpecStore

DEFAULT_SPEC_STORE = ".factory/specs"
DEFAULT_REPO = ".factory/work"
DEFAULT_RUN_DIR = ".factory/runstate"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dev-run", description="Run the Development Workflow."
    )
    parser.add_argument(
        "--spec-version", required=True, help="The approved spec_version_id (FR-025)"
    )
    parser.add_argument(
        "--spec-store", default=DEFAULT_SPEC_STORE, help="Spec store directory"
    )
    parser.add_argument("--repo", default=DEFAULT_REPO, help="Work repo directory")
    parser.add_argument(
        "--run-dir", default=DEFAULT_RUN_DIR, help="Run state directory (checkpoints)"
    )
    parser.add_argument(
        "--sandbox",
        default="fake",
        choices=("fake", "fake-fail", "docker"),
        help="Sandbox provider",
    )
    parser.add_argument(
        "--git-host",
        default="fake",
        choices=("fake", "github"),
        help="Git host provider",
    )
    parser.add_argument(
        "--resume", action="store_true", help="Resume from completed phases (FR-020)"
    )
    parser.add_argument(
        "--run-id", default="", help="Stable run id (for resume across invocations)"
    )
    parser.add_argument(
        "--budget-cost",
        type=float,
        default=None,
        help="Soft cost budget in USD (FR-019)",
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
        git_host = create_git_host(args.git_host)
    except (ValueError, RuntimeError) as exc:
        write_stderr(f"error: {exc}\n")
        return EXIT_ERROR

    spec_store = FileSpecStore(Path(args.spec_store))
    app = build_dev_graph(
        spec_store,
        sandbox,
        git_host,
        repo_root=Path(args.repo),
        run_dir=Path(args.run_dir),
        budget=Budget(cost_usd=args.budget_cost, tokens=None, time=None)
        if args.budget_cost is not None
        else None,
        resume=args.resume,
    )
    initial: dict = {
        "run_id": args.run_id or f"dev-run-{id(args)}",
        "spec_version_id": args.spec_version,
        "spec_run_id": f"spec-run-{id(args)}",
        "repo": args.repo,
        "outcome": "planned",
        "dev_attempt": 0,
    }
    result = app.invoke(initial)
    outcome = result.get("outcome", "failed")

    summary = {
        "outcome": outcome,
        "spec_version_id": result.get("spec_version_id") or args.spec_version,
        "spec_run_id": result.get("spec_run_id"),
        "pr": result.get("pr"),
        "error": result.get("error"),
        "overspend": result.get("overspend"),
        "adr": getattr(result.get("plan"), "adr", None),
    }
    write_stdout(emit(summary, args.format))

    if outcome == "delivered":
        return EXIT_OK
    if outcome == "stopped_human":
        return EXIT_STOPPED_HUMAN
    return EXIT_DEV_FAILED


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run(main))
