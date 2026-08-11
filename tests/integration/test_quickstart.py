"""Full quickstart suite (T090): Scenarios 2-7 as integration tests.

Exercises the documented end-to-end paths of `specs/.../quickstart.md` using
the real folder-driven entry point (``dev-run``) with fake sandbox + git host,
plus the telemetry query and the dev graph for budget/ADR scenarios. Network
and container-free and deterministic.

Note: quickstart Scenarios 1/1b covered the `spec-run` CLI and its production
graph entry, which the folder-driven feature hard-removes (FR-006/009); the
spec-production behavior they asserted is covered by the spec role libraries
tested in `tests/contract/spec_workflow/` and the handoff path in `test_handoff.py`.
"""

from __future__ import annotations

import json

import pytest

from ai_factory.cli.dev_run import main as dev_main
from ai_factory.dev_workflow.graph import build_dev_graph
from ai_factory.shared.cli_util import (
    EXIT_STOPPED_HUMAN,
    run,
)
from ai_factory.shared.git_host.client import FakeGitHost
from ai_factory.shared.sandbox.runner import FakeSandbox, SandboxResult
from ai_factory.shared.spec_store.handoff import publish_approved
from ai_factory.shared.spec_store.models import AcceptanceCriterion, SpecVersion
from ai_factory.shared.spec_store.store import FileSpecStore
from ai_factory.shared.telemetry.cli import main as telemetry_main
from ai_factory.shared.telemetry.record import SpecRoleInvocation, TelemetryRecord
from ai_factory.shared.telemetry.store import FileTelemetryStore

pytestmark = pytest.mark.integration

APPROVABLE = "Sessions must expire after 30 minutes to end stale sessions"

# A folder fixture used for the folder-driven ``dev-run`` scenarios (US3).
FOLDER = "tests/fixtures/specs/full"


def _dev_args(tmp_path, folder=FOLDER, **extra) -> list:
    args = [
        folder,
        "--repo",
        str(tmp_path / "repo"),
        "--run-dir",
        str(tmp_path / "runstate"),
        "--sandbox",
        extra.pop("sandbox", "fake"),
        "--git-host",
        extra.pop("git_host", "fake"),
        "--format",
        "json",
    ]
    flags = ("resume",)
    for k, v in extra.items():
        args.append(
            f"--{k.replace('_', '-')}" if k in flags else f"--{k.replace('_', '-')}={v}"
        )
    return args


def _published(tmp_path, intent=APPROVABLE) -> str:
    spec = SpecVersion(
        spec_run_id="spec-run-q",
        version=1,
        intent=intent,
        acceptance_criteria=[
            AcceptanceCriterion(statement="Behaviour 0", verified_by="test")
        ],
        definition_of_done="done",
        edge_cases=[],
        approval_status="approved",
        human_approved=True,
    )
    return publish_approved(spec, FileSpecStore(tmp_path / "specs")).spec_version_id


# ---- Scenario 1: spec workflow approve path --------------------------------

# ---- Scenario 1: folder is rejected/resolved fast (FR-001/002, SC-002) ----
def test_scenario1_missing_folder_rejected(tmp_path, capsys) -> None:
    from ai_factory.shared.cli_util import EXIT_DEV_FAILED

    code = run(
        dev_main,
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
    # FR-007/SC-002: a missing folder is a fast-fail (exit 4), no pipeline.
    assert code == EXIT_DEV_FAILED


def test_scenario2_dev_delivers_pr(tmp_path, capsys) -> None:
    code = run(dev_main, _dev_args(tmp_path))
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["outcome"] == "delivered"
    assert data["pr"]["number"] >= 1
    # Identity derives from the folder feature name (FR-011/012), not a version.
    assert data["spec_version_id"] == "full"


# ---- Scenario 3: failed -> stopped-human -----------------------------------
def test_scenario3_persistent_failure_stops_human(tmp_path, capsys) -> None:
    code = run(dev_main, _dev_args(tmp_path, sandbox="fake-fail"))
    assert code == EXIT_STOPPED_HUMAN


# ---- Scenario 4: resume ----------------------------------------------------
def test_scenario4_resume_replays(tmp_path, capsys) -> None:
    first = run(dev_main, _dev_args(tmp_path, run_id="resume-1"))
    assert first == 0
    capsys.readouterr()
    second = run(
        dev_main,
        _dev_args(tmp_path, run_id="resume-1", resume=True),
    )
    assert second == 0
    data = json.loads(capsys.readouterr().out)
    assert data["outcome"] == "delivered"


# ---- Scenario 5: telemetry query + redaction -------------------------------
def test_scenario5_telemetry_redaction(tmp_path, capsys) -> None:
    store = FileTelemetryStore(tmp_path / "telemetry")
    store.add(
        "run-5",
        SpecRoleInvocation(
            role="requirements_reviewer",
            feedback="Authorization: Bearer qssecret123",
            telemetry=TelemetryRecord(result="rework"),
        ),
    )
    code = run(
        telemetry_main,
        ["--run", "run-5", "--store", str(tmp_path / "telemetry"), "--format", "json"],
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "qssecret123" not in out
    assert "[REDACTED]" in out
    raw = (tmp_path / "telemetry" / "run-5.jsonl").read_text(encoding="utf-8")
    assert "qssecret123" not in raw  # SC-010: never persisted


# ---- Scenario 6: soft budget -----------------------------------------------
def test_scenario6_soft_budget_warns_but_delivers(tmp_path, capsys) -> None:
    code = run(dev_main, _dev_args(tmp_path, budget_cost="0.0000001"))
    assert code == 0  # FR-019: overspend never blocks
    data = json.loads(capsys.readouterr().out)
    assert data["outcome"] == "delivered"
    assert data["overspend"] is True


# ---- Scenario 7: ADR -------------------------------------------------------
def test_scenario7_adr_only_when_significant(tmp_path) -> None:
    store = FileSpecStore(tmp_path / "specs")
    sandbox = FakeSandbox(SandboxResult(exit_code=0, stdout="1 passed"))
    git_host = FakeGitHost()

    arch = _published(tmp_path, intent="Migrate the user store to Postgres")
    app = build_dev_graph(
        store, sandbox, git_host, repo_root=tmp_path / "a", run_dir=tmp_path / "rs-a"
    )
    res = app.invoke(_init(arch, "a", tmp_path))
    assert res["outcome"] == "delivered"
    assert res["plan"].adr is not None  # FR-008 significant decision

    trivial = _published(tmp_path, intent="Fix typo in a label")
    app2 = build_dev_graph(
        store, sandbox, git_host, repo_root=tmp_path / "b", run_dir=tmp_path / "rs-b"
    )
    res2 = app2.invoke(_init(trivial, "b", tmp_path))
    assert res2["outcome"] == "delivered"
    assert res2["plan"].adr is None  # FR-008 no ADR for a trivial fix


def _init(version_id, run_id, tmp_path) -> dict:
    return {
        "run_id": f"run-{run_id}",
        "spec_version_id": version_id,
        "spec_run_id": "spec-run-q",
        "repo": str(tmp_path / run_id),
        "outcome": "planned",
        "dev_attempt": 0,
    }
