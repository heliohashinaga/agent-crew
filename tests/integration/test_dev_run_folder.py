"""Integration test for the folder-driven ``dev-run`` entry (US-1, T024/T025).

``dev-run <folder>`` resolves a speckit folder, builds a TechnicalPlan via the
folder adapter (skipping load-spec + planner), and drives the pipeline to a PR
(FR-001/002, FR-011/012). Exit ``0`` = delivered.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_factory.cli.dev_run import main
from ai_factory.shared.cli_util import EXIT_DEV_FAILED, EXIT_OK, run

pytestmark = pytest.mark.integration

FULL = Path(__file__).resolve().parents[1] / "fixtures" / "specs" / "full"


def test_folder_driven_delivered(tmp_path, capsys) -> None:
    code = run(
        main,
        [
            str(FULL),
            "--repo",
            str(tmp_path / "repo"),
            "--run-dir",
            str(tmp_path / "runstate"),
            "--spec-store",
            str(tmp_path / "specs"),
            "--sandbox",
            "fake",
            "--git-host",
            "fake",
        ],
    )
    assert code == EXIT_OK
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["outcome"] == "delivered"
    assert data["pr"]["number"] >= 1
    # Identity derives from the folder feature name (FR-011/012), not a version.
    assert data["spec_version_id"] == "full"


def test_missing_folder_exit_four(tmp_path, capsys) -> None:
    code = run(
        main,
        [
            "does-not-exist",
            "--repo",
            str(tmp_path / "repo"),
            "--sandbox",
            "fake",
            "--git-host",
            "fake",
        ],
    )
    assert code == EXIT_DEV_FAILED


def test_selects_folder_by_short_name(tmp_path, capsys) -> None:
    # When run from repo root, full fixture is under tests/fixtures/specs/full.
    code = run(
        main,
        [
            str(FULL),
            "--repo",
            str(tmp_path / "repo"),
            "--run-dir",
            str(tmp_path / "runstate"),
            "--sandbox",
            "fake",
            "--git-host",
            "fake",
        ],
    )
    assert code == EXIT_OK


def test_selector_limits_scope(tmp_path, capsys) -> None:
    code = run(
        main,
        [
            str(FULL),
            "--selector",
            "T001",
            "--repo",
            str(tmp_path / "repo"),
            "--run-dir",
            str(tmp_path / "runstate"),
            "--sandbox",
            "fake",
            "--git-host",
            "fake",
        ],
    )
    assert code == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["outcome"] == "delivered"


def test_unknown_selector_fails(tmp_path, capsys) -> None:
    code = run(
        main,
        [
            str(FULL),
            "--selector",
            "T999",
            "--repo",
            str(tmp_path / "repo"),
            "--sandbox",
            "fake",
            "--git-host",
            "fake",
        ],
    )
    assert code == EXIT_DEV_FAILED


def test_noop_when_selecting_only_completed(tmp_path, capsys) -> None:
    import shutil

    folder = tmp_path / "fold"
    shutil.copytree(FULL, folder)
    from ai_factory.shared.folder_adapter.mark_completed import mark_task_complete

    tasks = folder / "tasks.md"
    content = mark_task_complete(
        tasks.read_text(), "T001", done=True
    ).content
    tasks.write_text(content)
    code = run(
        main,
        [
            str(folder),
            "--selector",
            "T001",
            "--repo",
            str(tmp_path / "repo"),
            "--run-dir",
            str(tmp_path / "runstate"),
            "--sandbox",
            "fake",
            "--git-host",
            "fake",
        ],
    )
    assert code == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["outcome"] == "noop"


def test_spec_version_flag_rejected(tmp_path, capsys) -> None:
    """T064/FR-009: --spec-version is rejected, not silently accepted."""
    from ai_factory.shared.cli_util import EXIT_ERROR

    code = run(
        main,
        [
            str(FULL),
            "--spec-version",
            "some-version",
            "--repo",
            str(tmp_path / "repo"),
            "--sandbox",
            "fake",
            "--git-host",
            "fake",
        ],
    )
    assert code == EXIT_ERROR
    err = capsys.readouterr().err
    assert "--spec-version" in err and "rejected" in err


def test_run_carries_no_factory_spec_version(tmp_path, capsys) -> None:
    """T064: a folder-driven run's identity is the folder name, not a join key."""
    code = run(
        main,
        [
            str(FULL),
            "--repo",
            str(tmp_path / "repo"),
            "--run-dir",
            str(tmp_path / "runstate"),
            "--sandbox",
            "fake",
            "--git-host",
            "fake",
        ],
    )
    assert code == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    # Identity = folder feature name (FR-011/012); no separate spec_run_id.
    assert data["spec_version_id"] == "full"
    assert data["spec_version_id"] != ""
    assert not data["spec_version_id"].startswith("f-v")


def test_resume_replays_delivered(tmp_path, capsys) -> None:
    """T046: a stable run-id resumes from completed checkpoints (FR-020)."""
    first = run(
        main,
        [
            str(FULL),
            "--run-id",
            "resume-1",
            "--repo",
            str(tmp_path / "repo"),
            "--run-dir",
            str(tmp_path / "runstate"),
            "--sandbox",
            "fake",
            "--git-host",
            "fake",
        ],
    )
    assert first == EXIT_OK
    capsys.readouterr()
    second = run(
        main,
        [
            str(FULL),
            "--run-id",
            "resume-1",
            "--resume",
            "--repo",
            str(tmp_path / "repo"),
            "--run-dir",
            str(tmp_path / "runstate"),
            "--sandbox",
            "fake",
            "--git-host",
            "fake",
        ],
    )
    assert second == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["outcome"] == "delivered"


def test_scenario10_idempotent_noop_force_selector(tmp_path, capsys) -> None:
    """T062/SC-007a/b: all-complete = no-op exit 0; ``--force`` re-runs."""
    import shutil

    from ai_factory.shared.folder_adapter.mark_completed import mark_task_complete

    folder = tmp_path / "s10"
    shutil.copytree(FULL, folder)
    tasks = folder / "tasks.md"
    content = tasks.read_text()
    for tid in ("T001", "T002", "T003"):
        content = mark_task_complete(content, tid, done=True).content
    tasks.write_text(content)

    def _run(folder_arg, *extra):
        return run(
            main,
            [
                folder_arg,
                "--repo",
                str(tmp_path / "repo"),
                "--run-dir",
                str(tmp_path / "runstate"),
                "--sandbox",
                "fake",
                "--git-host",
                "fake",
                *extra,
            ],
        )

    code = _run(str(folder))
    assert code == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["outcome"] == "delivered"

    code = _run(str(folder), "--selector", "T1-T3")
    assert code == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["outcome"] == "noop"

    code = _run(str(folder), "--selector", "T1-T3", "--force")
    assert code == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["outcome"] == "delivered"


def test_folder_run_emits_role_telemetry(tmp_path, capsys) -> None:
    """T048/FR-015: the folder-driven run emits per-role telemetry records."""
    import glob

    run_data_dir = tmp_path / "runstate"
    code = run(
        main,
        [
            str(FULL),
            "--run-id",
            "t048",
            "--repo",
            str(tmp_path / "repo"),
            "--run-dir",
            str(run_data_dir),
            "--sandbox",
            "fake",
            "--git-host",
            "fake",
        ],
    )
    assert code == EXIT_OK
    capsys.readouterr()
    records = glob.glob(str(run_data_dir / "telemetry" / "t048" / "*.jsonl"))
    assert records, "expected telemetry records for the folder-driven run"
    # Per-role records must carry a valid role label and no secret-looking values.
    seen_roles: set[str] = set()
    for path in records:
        for line in Path(path).read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if "role" in rec:
                seen_roles.add(rec["role"])
            raw = json.dumps(rec).lower()
            # FR-018: emitted telemetry never leaks secret-looking values.
            assert "api_key" not in raw
            assert "password" not in raw
    assert "code_worker" in seen_roles and "test_runner" in seen_roles


def test_folder_run_overspend_is_soft(tmp_path, capsys) -> None:
    """T048/FR-019: a soft budget overspend flags but does not block delivery."""
    code = run(
        main,
        [
            str(FULL),
            "--repo",
            str(tmp_path / "repo"),
            "--run-dir",
            str(tmp_path / "runstate"),
            "--sandbox",
            "fake",
            "--git-host",
            "fake",
            "--budget-cost",
            "0.0000001",
        ],
    )
    assert code == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["outcome"] == "delivered"
    assert data["overspend"] is True
