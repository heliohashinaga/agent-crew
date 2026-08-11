"""CLI for the folder_adapter library (002-folder-dev-run).

Library-first CLIs emit machine-readable JSON by default, a ``--format human``
form, diagnostics to stderr, and meaningful exit codes (see ``cli_util``).

Commands:

* ``folder-adapter parse <folder> [--selector <sel>]``
    Resolve a ``<folder>`` (local, ``path:``, or ``git:url#branch``), build a
    ``TechnicalPlan``, apply selector/completed filtering, and emit the
    executable subtask list.
* ``folder-adapter mark-done <folder> <T###> [--done|--undone]``
    Mark a task complete in ``tasks.md`` and report whether anything changed.
"""

from __future__ import annotations

import argparse
import sys

from ai_factory.shared.cli_util import (
    EXIT_OK,
    add_output_format_arg,
    emit,
    run,
)
from ai_factory.shared.folder_adapter.build_plan import build_plan
from ai_factory.shared.folder_adapter.mark_completed import mark_task_complete
from ai_factory.shared.folder_adapter.selector import SelectorError, resolve_selector
from ai_factory.shared.folder_adapter.spec_source import (
    SpecSource,
    resolve_path_for_source,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="folder-adapter")
    parser.add_argument(
        "command",
        choices=["parse", "mark-done"],
        help="Operation to run.",
    )
    add_output_format_arg(parser)
    parser.add_argument(
        "folder", nargs="?", help="Spec folder (name, path:, or git:url#branch)."
    )
    parser.add_argument("task_id", nargs="?", help="Task id for mark-done (e.g. T003).")
    parser.add_argument(
        "--selector", default=None, help="Optional task selector (T3,T5 etc.)."
    )
    parser.add_argument(
        "--repo", default=None, help="Local working copy repo root for the folder."
    )
    parser.add_argument(
        "--force", action="store_true", help="Include already-completed tasks."
    )
    parser.add_argument("--done", dest="done", action="store_true", default=True)
    parser.add_argument("--undone", dest="done", action="store_false")
    return parser


def _resolve(path: str, repo: str | None):

    source = SpecSource.from_arg(path)
    if source.origin == "git":
        raise SelectorError(
            "git SpecSource requires clone via the dev-run CLI; not available here."
        )
    folder = resolve_path_for_source(source, specs_root=None)
    return source, folder


def cmd_parse(args: argparse.Namespace) -> int:
    try:
        source, folder = _resolve(args.folder, args.repo)
    except Exception as exc:  # noqa: BLE001
        from ai_factory.shared.cli_util import EXIT_DEV_FAILED, CliError

        raise CliError(f"resolve failed: {exc}", exit_code=EXIT_DEV_FAILED) from exc

    if args.selector:
        ids = sorted(
            {s.source_task_id for s in build_plan(folder).plan.subtasks},
        )
        selector = resolve_selector(args.selector, ids)
    else:
        selector = None

    try:
        result = build_plan(folder)
    except FileNotFoundError as exc:  # noqa: PERF203
        from ai_factory.shared.cli_util import EXIT_DEV_FAILED, CliError

        raise CliError(
            f"Missing artifact while building plan: {exc}",
            exit_code=EXIT_DEV_FAILED,
        ) from exc
    filtered = filter_plan(result.plan.subtasks, selector=selector, force=args.force)

    payload = {
        "folder": source.name,
        "origin": source.origin,
        "goal": result.plan.goal,
        "spec_version_id": result.plan.spec_version_id,
        "subtasks": [
            {"source_task_id": s.source_task_id, "title": s.title, "files": s.files}
            for s in filtered.subtasks
        ],
        "noop": filtered.noop,
        "pruned_completed": filtered.pruned_completed,
        "warnings": result.warnings,
        "conflicts": [
            {"a": c.source_task_id_a, "b": c.source_task_id_b, "file": c.file}
            for c in result.conflicts
        ],
    }
    sys.stdout.write(emit(payload, args.format))
    sys.stdout.write("\n")
    return EXIT_OK


def filter_plan(subtasks, *, selector=None, force=False):
    from ai_factory.shared.folder_adapter.task_filter import filter_subtasks

    return filter_subtasks(subtasks, selector=selector, force=force)


def cmd_mark_done(args: argparse.Namespace) -> int:


    source, folder = _resolve(args.folder, args.repo)
    tasks_path = folder / "tasks.md"
    content = tasks_path.read_text(encoding="utf-8")
    out = mark_task_complete(content, args.task_id, done=args.done)
    if out.changed:
        tasks_path.write_text(out.content, encoding="utf-8")
    payload = {
        "task_id": out.task_id,
        "matched": out.matched,
        "changed": out.changed,
        "folder": source.name,
    }
    sys.stdout.write(emit(payload, args.format))
    sys.stdout.write("\n")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help(sys.stderr)
        return 2
    try:
        if args.command == "parse":
            return cmd_parse(args)
        if args.command == "mark-done":
            return cmd_mark_done(args)
        raise ValueError(f"Unknown command {args.command}")
    except SelectorError as exc:
        from ai_factory.shared.cli_util import CliError

        raise CliError(str(exc)) from exc


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run(main))
