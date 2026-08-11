"""``dev-run`` workflow CLI (T066, contracts/dev-run-cli.md).

A thin CLI over the Development Workflow StateGraph. Enters directly from a
speckit spec folder (``dev-run <folder>``), builds a TechnicalPlan via the
folder adapter, and drives the pipeline to a merge-ready PR. It no longer
consumes a ``spec_version_id`` by reference (FR-006/009): folder identity is
the traceability key, and the standalone `spec-run`/`spec-workflow` entry was
removed.

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
from ai_factory.shared.telemetry.store import FileTelemetryStore

DEFAULT_SPEC_STORE = ".factory/specs"
DEFAULT_REPO = ".factory/work"
DEFAULT_RUN_DIR = ".factory/runstate"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dev-run", description="Run the Development Workflow."
    )
    parser.add_argument(
        "folder",
        help="Speckit spec folder (name, path:, or path) - US-1 folder-driven entry.",
    )
    parser.add_argument(
        "--spec-version",
        default=None,
        help="DEPRECATED/REJECTED: folder runs carry no spec_version_id (FR-009)."
        " Passing it is an error.",
    )
    parser.add_argument(
        "--selector",
        default=None,
        help="Optional task selector (T3, T3,T5, T3-T7, T3-, *). "
        "Skip already-complete by default (FR-014b).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run already-completed tasks (FR-014a override).",
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

    # FR-006/009: folder-driven is the only entry. The spec_version_id join
    # key is removed; passing --spec-version is rejected, not silently ignored.
    if args.spec_version is not None:
        write_stderr(
            "error: --spec-version is rejected; folder-driven runs carry no "
            "spec_version_id (FR-009). Use the <folder> argument.\n"
        )
        return EXIT_ERROR

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
        telemetry_store=FileTelemetryStore(
            Path(args.run_dir) / "telemetry" / (args.run_id or "run")
        ),
        resume=args.resume,
    )
    initial: dict = {
        "run_id": args.run_id or f"dev-run-{id(args)}",
        "spec_version_id": "",
        "spec_run_id": "",
        "repo": args.repo,
        "outcome": "planned",
        "dev_attempt": 0,
    }

    # US-1 folder-driven entry: build a TechnicalPlan from the speckit folder
    # and inject it so the graph skips load-spec + planner.
    from pathlib import Path as _Path

    from ai_factory.shared.folder_adapter.build_plan import build_plan
    from ai_factory.shared.folder_adapter.resolve import FolderResolutionError
    from ai_factory.shared.folder_adapter.spec_source import (
        SpecSource,
        resolve_path_for_source,
    )

    try:
        source = SpecSource.from_arg(args.folder)
        if source.origin == "git":
            # Git origin: validate as untrusted input and bind a GitSource for
            # write-back (T020/T021). A real clone needs an executable git
            # backend through the sandbox; without one, fail fast with a clear
            # message rather than silently falling back to a local folder.
            from ai_factory.shared.folder_adapter.git_source import (
                GitSourceUnavailable,
                clone,
            )

            # The clone validates/parses the source and binds a GitSource;
            # we surface the result for write-back but fail fast without a
            # git backend below.
            _git_src = clone(
                source,
                git_host=git_host,
                sandbox=sandbox,
                workdir=_Path(args.run_dir) / "git-src",
                run_id=args.run_id or "dev-run",
            )
            del _git_src
            raise GitSourceUnavailable(
                f"configured git source '{source.url}' requires a git backend; "
                "a local folder path is required for offline/deterministic runs "
                "(git write-back via PR is available with a provisioned backend)."
            )
        # A bare path (existing dir, possibly with slashes) resolves directly.
        candidate = _Path(args.folder)
        if candidate.is_dir() and source.origin == "local":
            folder_path = candidate
        else:
            folder_path = resolve_path_for_source(
                source, specs_root=_Path.cwd() / "specs"
            )
        built = build_plan(folder_path)
    except FolderResolutionError:
        raise
    except FileNotFoundError as exc:
        write_stderr(f"error: {exc}\n")
        return EXIT_DEV_FAILED
    initial["plan"] = built.plan
    initial["spec_version_id"] = built.plan.spec_version_id
    if built.warnings:
        write_stderr(f"warn: {built.warnings[:1][0]}\n")

    # FR-014a/b: completed-task skip, selector & no-op short-circuit.
    from ai_factory.shared.folder_adapter.selector import (
        SelectorError,
        resolve_selector,
    )
    from ai_factory.shared.folder_adapter.task_filter import filter_subtasks

    sel = None
    if args.selector:
        from ai_factory.shared.cli_util import CliError

        try:
            ids = [s.source_task_id for s in built.plan.subtasks]
            sel = resolve_selector(args.selector, ids)
        except SelectorError as exc:
            raise CliError(str(exc), exit_code=EXIT_DEV_FAILED) from exc

    # FR-014a/b/d: always apply completed-skip + selector filter so the default
    # idempotent skip is applied and its non-blocking skip warnings are surfaced.
    filtered = filter_subtasks(built.plan.subtasks, selector=sel, force=args.force)
    initial["plan"] = built.plan.model_copy(update={"subtasks": filtered.subtasks})

    for w in filtered.prerequisite_warnings:
        write_stderr(
            f"warn: prerequisite {w.task_id} depends on "
            f"uncompleted {w.prerequisite_id}\n"
        )
    for w in filtered.skip_warnings:
        write_stderr(f"warn: skipping {w.task_id} ({w.reason})\n")

    if filtered.noop:
        payload = {
            "outcome": "noop",
            "spec_version_id": built.plan.spec_version_id,
            "pruned_completed": filtered.pruned_completed,
            "skip_warnings": [
                {"task_id": w.task_id, "reason": w.reason}
                for w in filtered.skip_warnings
            ],
            "error": None,
            "overspend": False,
        }
        sys.stdout.write(emit(payload, args.format))
        sys.stdout.write("\n")
        return EXIT_OK

    result = app.invoke(initial)
    outcome = result.get("outcome", "failed")

    summary = {
        "outcome": outcome,
        "spec_version_id": result.get("spec_version_id"),
        "pr": result.get("pr"),
        "error": result.get("error"),
        "overspend": result.get("overspend"),
        "adr": getattr(result.get("plan"), "adr", None),
        "skip_warnings": [
            {"task_id": w.task_id, "reason": w.reason}
            for w in filtered.skip_warnings
        ],
        "prerequisite_warnings": [
            {"task_id": w.task_id, "prerequisite_id": w.prerequisite_id}
            for w in filtered.prerequisite_warnings
        ],
    }
    write_stdout(emit(summary, args.format))

    if outcome == "delivered":
        return EXIT_OK
    if outcome == "stopped_human":
        return EXIT_STOPPED_HUMAN
    return EXIT_DEV_FAILED


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run(main))
