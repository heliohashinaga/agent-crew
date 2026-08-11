"""Contract test for the folder_adapter library CLI (library-first, FR-017/018)."""

import io
import json
import sys
from pathlib import Path

import pytest

from ai_factory.shared.cli_util import EXIT_DEV_FAILED, EXIT_OK
from ai_factory.shared.cli_util import run as cli_run
from ai_factory.shared.folder_adapter import cli

pytestmark = pytest.mark.contract

FULL = Path(__file__).resolve().parents[3] / "fixtures" / "specs" / "full"
NO_TASKS = Path(__file__).resolve().parents[3] / "fixtures" / "specs" / "no-tasks"


def _run(argv: list[str]) -> tuple[int, str]:
    buff = io.StringIO()
    old = sys.stdout
    try:
        sys.stdout = buff
        code = cli_run(cli.main, argv)
    finally:
        sys.stdout = old
    return code, buff.getvalue()


def test_parse_emits_json() -> None:
    code, out = _run(["parse", f"path:{FULL}"])
    assert code == EXIT_OK
    data = json.loads(out)
    assert data["folder"] == str(FULL)
    assert data["spec_version_id"] == "full"
    assert len(data["subtasks"]) == 7
    assert data["subtasks"][0]["source_task_id"] == "T001"


def test_parse_with_selector() -> None:
    code, out = _run(["parse", f"path:{FULL}", "--selector", "T3"])
    data = json.loads(out)
    ids = [s["source_task_id"] for s in data["subtasks"]]
    assert ids == ["T003"]


def test_parse_human_format() -> None:
    code, out = _run(["parse", f"path:{FULL}", "--format", "human"])
    assert code == EXIT_OK
    assert not out.lstrip().startswith("{")


def test_parse_missing_tasks_emits_error_code() -> None:
    code, _ = _run(["parse", f"path:{NO_TASKS}"])
    assert code == EXIT_DEV_FAILED


def test_mark_done_roundtrip(tmp_path: Path) -> None:
    import shutil

    work = tmp_path / "full"
    shutil.copytree(FULL, work)
    code, out = _run(["mark-done", f"path:{work}", "T001"])
    assert code == EXIT_OK
    data = json.loads(out)
    assert data["matched"] is True
    assert data["changed"] is True
    assert '[x] T001' in (work / "tasks.md").read_text()


def test_mark_done_unknown() -> None:
    import shutil

    work = Path("/tmp/fa_mark_unknown")
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(FULL, work)
    try:
        code, out = _run(["mark-done", f"path:{work}", "T999"])
        assert code == EXIT_OK
        assert json.loads(out)["matched"] is False
    finally:
        shutil.rmtree(work, ignore_errors=True)
