"""Contract test for the requirements-reviewer role library CLI (T018, FR-004).

The reviewer validates a draft spec against clarity, completeness,
consistency, testability and edge-case coverage (FR-004), returning
Approve/Reject with explicit reasons. Exit code ``0`` on approve, ``2``
(rejected) on reject.
"""

from __future__ import annotations

import json

import pytest

from ai_factory.shared.cli_util import EXIT_ERROR, EXIT_REJECTED, run
from ai_factory.shared.spec_store.models import (
    AcceptanceCriterion,
    EdgeCase,
    SpecVersion,
)
from ai_factory.spec_workflow.requirements_reviewer.cli import main


def _approved_candidate() -> SpecVersion:
    return SpecVersion(
        spec_run_id="spec-run-1",
        intent="Add logout.",
        rationale="Users need a way to end sessions.",
        acceptance_criteria=[
            AcceptanceCriterion(
                statement="Given a signed-in user, clicking logout ends the session.",
                verified_by="automated test",
            )
        ],
        definition_of_done="Logout E2E passes.",
        edge_cases=[
            EdgeCase(
                description="Session already expired",
                expected_behavior="Redirect to login",
            )
        ],
    )


def _write(tmp_path: pytest.TempPathFactory, spec: SpecVersion) -> str:
    path = tmp_path / "spec.json"
    path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    return str(path)


def test_approves_complete_spec(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    code = run(main, ["--spec-file", _write(tmp_path, _approved_candidate())])
    assert code == 0
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["approved"] is True


def test_rejects_spec_without_acceptance_criteria(tmp_path, capsys) -> None:
    """FR-003/FR-004: a spec with no AC cannot pass review."""
    spec = _approved_candidate()
    spec.acceptance_criteria = []
    code = run(main, ["--spec-file", _write(tmp_path, spec)])
    assert code == EXIT_REJECTED
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["approved"] is False
    assert verdict["reasons"]
    assert any("acceptance" in r.lower() for r in verdict["reasons"])


def test_rejects_spec_without_intent(tmp_path, capsys) -> None:
    spec = _approved_candidate()
    spec.intent = ""
    code = run(main, ["--spec-file", _write(tmp_path, spec)])
    assert code == EXIT_REJECTED
    verdict = json.loads(capsys.readouterr().out)
    assert any("intent" in r.lower() for r in verdict["reasons"])


def test_rejects_spec_with_non_testable_ac(tmp_path, capsys) -> None:
    spec = _approved_candidate()
    spec.acceptance_criteria[0].verified_by = ""  # not testable
    code = run(main, ["--spec-file", _write(tmp_path, spec)])
    assert code == EXIT_REJECTED
    verdict = json.loads(capsys.readouterr().out)
    assert any("testable" in r.lower() for r in verdict["reasons"])


def test_missing_spec_file_is_a_cli_error() -> None:
    assert run(main, []) == EXIT_ERROR


def test_human_format_is_not_json(tmp_path, capsys) -> None:
    run(
        main,
        ["--spec-file", _write(tmp_path, _approved_candidate()), "--format", "human"],
    )
    out = capsys.readouterr().out
    assert out
    assert not out.lstrip().startswith("{")
