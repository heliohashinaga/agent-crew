"""Integration test for the folder-driven ``dev-run`` workflow CLI (US1/US3).

``dev-run <folder>`` resolves a speckit spec folder (no ``--spec-version`` join
key, FR-006/009) and drives the pipeline to a PR. Exit codes per the contract:
``0`` delivered, ``4`` failed delivery, ``5`` stopped-human.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_factory.cli.dev_run import main
from ai_factory.shared.cli_util import EXIT_DEV_FAILED, EXIT_OK, EXIT_STOPPED_HUMAN, run

pytestmark = pytest.mark.integration

FULL = Path(__file__).resolve().parents[1] / "fixtures" / "specs" / "full"


def _args(tmp_path, **extra) -> list[str]:
    base = [
        str(FULL),
        "--repo",
        str(tmp_path / "repo"),
        "--run-dir",
        str(tmp_path / "runstate"),
        "--sandbox",
        "fake",
        "--git-host",
        "fake",
    ]
    for k, v in extra.items():
        base += [f"--{k}", v]
    return base


def test_delivered_exit_zero(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    code = run(main, _args(tmp_path))
    assert code == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["outcome"] == "delivered"
    assert data["pr"]["number"] >= 1
    # Identity derives from the folder feature name, not a factory version (FR-011).
    assert data["spec_version_id"] == "full"


def test_stopped_human_after_retries(tmp_path, capsys) -> None:
    """A folder whose tests never pass eventually hands to a human ⇒ exit 5 (FR-015)."""
    code = run(main, _args(tmp_path, sandbox="fake-fail"))
    assert code == EXIT_STOPPED_HUMAN


def test_unknown_folder_exit_four(tmp_path, capsys) -> None:
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
