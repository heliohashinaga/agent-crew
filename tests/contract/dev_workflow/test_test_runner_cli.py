"""Contract test for the test-runner role library CLI (T054, FR-011, FR-021).

Runs the generated suites inside the sandbox (FR-021) and maps the sandbox
exit/output to a structured, evidence-backed result.
"""

from __future__ import annotations

import json

from ai_factory.dev_workflow.technical_planner.planner import produce_plan
from ai_factory.dev_workflow.test_engineer.engineer import build_test_suite
from ai_factory.dev_workflow.test_runner.cli import main as cli_main
from ai_factory.dev_workflow.test_runner.runner import run_tests
from ai_factory.shared.cli_util import EXIT_ERROR, run
from ai_factory.shared.sandbox.runner import FakeSandbox, SandboxResult
from ai_factory.shared.spec_store.models import AcceptanceCriterion, SpecVersion


def _repo_with_suite(tmp_path):
    spec = SpecVersion(
        spec_version_id="f-v1-abc",
        intent="Add a search helper",
        acceptance_criteria=[
            AcceptanceCriterion(
                statement="Search returns the index", verified_by="test"
            )
        ],
        definition_of_done="done",
        edge_cases=[],
    )
    build_test_suite(produce_plan(spec), tmp_path)
    return tmp_path


def test_pass_result_from_clean_sandbox(tmp_path) -> None:
    sandbox = FakeSandbox(SandboxResult(exit_code=0, stdout="3 passed", duration=0.5))
    result = run_tests(_repo_with_suite(tmp_path), sandbox)
    assert result.passed is True
    assert result.failures == []
    assert result.evidence["exit_code"] == 0


def test_fail_result_captures_failure_lines(tmp_path) -> None:
    sandbox = FakeSandbox(
        SandboxResult(
            exit_code=1,
            stdout="FAILED test_suite.py::test_ac_1 - assert",
            stderr="boom",
        )
    )
    result = run_tests(_repo_with_suite(tmp_path), sandbox)
    assert result.passed is False
    assert result.failures
    assert any("test_ac_1" in f for f in result.failures)


def test_run_tests_reports_suites(tmp_path) -> None:
    sandbox = FakeSandbox(SandboxResult(exit_code=0, stdout="ok"))
    result = run_tests(_repo_with_suite(tmp_path), sandbox)
    assert result.suites == ["test_suite.py"]


def test_cli_emits_json_with_fake_sandbox(tmp_path, capsys) -> None:
    code = run(
        cli_main,
        [
            "--repo",
            str(_repo_with_suite(tmp_path)),
            "--sandbox",
            "fake",
            "--format",
            "json",
        ],
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["passed"] is True
    assert data["evidence"]["exit_code"] == 0


def test_cli_docker_sandbox_missing_runtime_fails_early(tmp_path, monkeypatch) -> None:
    """SC-013: no container runtime ⇒ non-zero exit, diagnostic on stderr."""
    import shutil

    monkeypatch.setattr(shutil, "which", lambda _name: None)
    code = run(
        cli_main, ["--repo", str(_repo_with_suite(tmp_path)), "--sandbox", "docker"]
    )
    assert code == EXIT_ERROR
