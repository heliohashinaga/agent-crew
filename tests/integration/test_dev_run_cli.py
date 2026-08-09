"""Integration test for the ``dev-run`` workflow CLI (T065/T066, dev-run-cli.md).

Accepts a ``spec_version_id`` (dev consumes the spec by reference, SC-017)
and drives the pipeline to a PR. Exit codes per the contract:
``0`` delivered, ``4`` failed delivery, ``5`` stopped-human.
"""

from __future__ import annotations

import json

import pytest

from ai_factory.cli.dev_run import main
from ai_factory.shared.cli_util import EXIT_DEV_FAILED, EXIT_STOPPED_HUMAN, run
from ai_factory.shared.spec_store.handoff import publish_approved
from ai_factory.shared.spec_store.models import AcceptanceCriterion, SpecVersion
from ai_factory.shared.spec_store.store import FileSpecStore

pytestmark = pytest.mark.integration


def _published_spec(tmp_path) -> str:
    spec = SpecVersion(
        spec_run_id="spec-run-9",
        version=1,
        intent="Add a binary search helper",
        acceptance_criteria=[
            AcceptanceCriterion(
                statement="Search returns the index", verified_by="test"
            )
        ],
        definition_of_done="done",
        edge_cases=[],
        approval_status="approved",
        human_approved=True,
    )
    store = FileSpecStore(tmp_path / "specs")
    return publish_approved(spec, store).spec_version_id


def test_delivered_exit_zero(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    version_id = _published_spec(tmp_path)
    code = run(
        main,
        [
            "--spec-version",
            version_id,
            "--spec-store",
            str(tmp_path / "specs"),
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
    assert code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["outcome"] == "delivered"
    assert data["pr"]["number"] >= 1
    assert data["spec_version_id"] == version_id


def test_stopped_human_after_retries(tmp_path, capsys) -> None:
    """A spec that never passes eventually hands to a human ⇒ exit 5 (FR-015)."""
    version_id = _published_spec(tmp_path)
    code = run(
        main,
        [
            "--spec-version",
            version_id,
            "--spec-store",
            str(tmp_path / "specs"),
            "--repo",
            str(tmp_path / "repo"),
            "--run-dir",
            str(tmp_path / "runstate"),
            "--sandbox",
            "fake-fail",  # sandbox that always fails tests
            "--git-host",
            "fake",
        ],
    )
    assert code == EXIT_STOPPED_HUMAN


def test_unknown_spec_version_exit_four(tmp_path, capsys) -> None:
    code = run(
        main,
        [
            "--spec-version",
            "nope-v1-deadbeef",
            "--spec-store",
            str(tmp_path / "specs"),
            "--repo",
            str(tmp_path / "repo"),
            "--sandbox",
            "fake",
            "--git-host",
            "fake",
        ],
    )
    assert code == EXIT_DEV_FAILED
