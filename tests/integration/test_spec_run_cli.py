"""Integration test for the ``spec-run`` workflow CLI (T023).

Validates the CLI's exit codes against quickstart Scenario 1
(contracts/spec-run-cli.md):
- ``0`` spec approved and published (x-approve).
- ``2`` spec rejected after bounded review.
- ``3`` needs clarification / human deferred.
Uses a tmp store and the deterministic, network-free graph.
"""

from __future__ import annotations

import json

import pytest

from ai_factory.cli.spec_run import main
from ai_factory.shared.cli_util import (
    EXIT_CLARIFICATION,
    EXIT_REJECTED,
    run,
)
from ai_factory.shared.spec_store.store import FileSpecStore

pytestmark = pytest.mark.integration

APPROVABLE = "Sessions must expire after 30 minutes to end stale sessions"
REJECTED = "Add a feature to improve the dashboard"


def test_approved_exit_zero_and_publishes(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run(
        main,
        [
            "--request",
            APPROVABLE,
            "--auto-approve",
            "--format",
            "json",
            "--store",
            str(tmp_path),
        ],
    )
    assert code == 0
    spec = json.loads(capsys.readouterr().out)
    assert spec["approval_status"] == "approved"
    assert spec["human_approved"] is True
    assert spec["spec_version_id"]
    # Persisted and loadable by reference.
    store = FileSpecStore(tmp_path)
    assert store.load(spec["spec_version_id"]) is not None


def test_rejected_exit_two(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    code = run(
        main, ["--request", REJECTED, "--auto-approve", "--store", str(tmp_path)]
    )
    assert code == EXIT_REJECTED


def test_deferred_exit_three_without_approval(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No ``--auto-approve`` and a non-TTY stdin → the gate defers (exit 3)."""
    code = run(main, ["--request", APPROVABLE, "--store", str(tmp_path)])
    assert code == EXIT_CLARIFICATION


def test_missing_request_is_error(tmp_path) -> None:
    from ai_factory.shared.cli_util import EXIT_ERROR

    assert run(main, ["--store", str(tmp_path)]) == EXIT_ERROR


def test_stdin_input(tmp_path, capsys: pytest.CaptureFixture[str], monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.stdin", _Stdin("Sessions must expire after 30 minutes; read via stdin")
    )
    code = run(
        main,
        ["--stdin", "--auto-approve", "--store", str(tmp_path), "--format", "json"],
    )
    assert code == 0
    spec = json.loads(capsys.readouterr().out)
    assert "expire" in spec["intent"]
    assert spec["approval_status"] == "approved"


class _Stdin:
    def __init__(self, text: str) -> None:
        self._text = text

    def read(self) -> str:
        return self._text
