"""Full quickstart suite (T090): Scenarios 1-7 as integration tests.

Exercises the documented end-to-end paths of `specs/.../quickstart.md` using
the real CLI entry points (``spec-run`` / ``dev-run``) with fake sandbox +
git host, plus the telemetry query and the dev graph for budget/ADR
scenarios. Network/container-free and deterministic.
"""

from __future__ import annotations

import json

import pytest

from ai_factory.cli.dev_run import main as dev_main
from ai_factory.cli.spec_run import main as spec_main
from ai_factory.dev_workflow.graph import build_dev_graph
from ai_factory.shared.cli_util import (
    EXIT_REJECTED,
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


def _dev_args(tmp_path, version_id, **extra) -> list:
    args = [
        "--spec-version",
        version_id,
        "--spec-store",
        str(tmp_path / "specs"),
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
def test_scenario1_spec_approved(tmp_path, capsys) -> None:
    code = run(
        spec_main,
        [
            "--request",
            APPROVABLE,
            "--auto-approve",
            "--store",
            str(tmp_path / "specs"),
            "--format",
            "json",
        ],
    )
    assert code == 0
    spec = json.loads(capsys.readouterr().out)
    assert spec["approval_status"] == "approved"
    assert spec["human_approved"] is True
    assert spec["spec_version_id"]
    assert spec["acceptance_criteria"]  # FR-003
    assert spec["definition_of_done"]
    assert spec["edge_cases"]  # derived from the 'expire' keyword
    assert "code" not in spec  # FR-001: no implementation code in a spec


def test_scenario1b_rejected_exit2(tmp_path, capsys) -> None:
    # A request with no derivable edge cases is rejected by the reviewer.
    code = run(
        spec_main,
        [
            "--request",
            "Fix the dashboard colour",
            "--auto-approve",
            "--store",
            str(tmp_path / "specs"),
        ],
    )
    assert code == EXIT_REJECTED


# ---- Scenario 2: dev approval -> PR delivered ------------------------------
def test_scenario2_dev_delivers_pr(tmp_path, capsys) -> None:
    version_id = _published(tmp_path)
    code = run(dev_main, _dev_args(tmp_path, version_id))
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["outcome"] == "delivered"
    assert data["pr"]["number"] >= 1
    assert data["spec_version_id"] == version_id


# ---- Scenario 3: failed -> stopped-human -----------------------------------
def test_scenario3_persistent_failure_stops_human(tmp_path, capsys) -> None:
    version_id = _published(tmp_path)
    code = run(dev_main, _dev_args(tmp_path, version_id, sandbox="fake-fail"))
    assert code == EXIT_STOPPED_HUMAN


# ---- Scenario 4: resume ----------------------------------------------------
def test_scenario4_resume_replays(tmp_path, capsys) -> None:
    version_id = _published(tmp_path)
    first = run(dev_main, _dev_args(tmp_path, version_id, run_id="resume-1"))
    assert first == 0
    capsys.readouterr()
    second = run(
        dev_main,
        _dev_args(tmp_path, version_id, run_id="resume-1", resume=True),
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
    version_id = _published(tmp_path)
    code = run(dev_main, _dev_args(tmp_path, version_id, budget_cost="0.0000001"))
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
