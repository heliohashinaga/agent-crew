"""Contract test for the spec-agent role library CLI (T016, FR-002/003/006).

Per `contracts/library-cli-convention.md`: the spec-agent CLI consumes a
feature request and emits a draft ``SpecVersion`` as JSON (or human). The
draft must include acceptance criteria (FR-003) and surface bounded
clarifications for scope-critical ambiguity (FR-006). Runs network-free via
the deterministic agent core.
"""

from __future__ import annotations

import pytest

from ai_factory.shared.cli_util import EXIT_ERROR, run
from ai_factory.shared.spec_store.models import SpecVersion
from ai_factory.spec_workflow.spec_agent.cli import main


def test_drafts_spec_json_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    code = run(main, ["--request", "Add a logout button to the app"])
    assert code == 0
    out = capsys.readouterr().out
    spec = SpecVersion.model_validate_json(out)
    assert spec.intent
    assert "logout" in spec.intent.lower()
    assert spec.approval_status == "draft"


def test_draft_includes_acceptance_criteria(capsys: pytest.CaptureFixture[str]) -> None:
    """FR-003: a draft must carry acceptance criteria."""
    run(main, ["--request", "Sessions must expire after 30 minutes"])
    spec = SpecVersion.model_validate_json(capsys.readouterr().out)
    assert len(spec.acceptance_criteria) >= 1
    assert all(c.statement for c in spec.acceptance_criteria)


def test_draft_surfaces_clarification_for_missing_constraints(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """FR-006: scope-critical ambiguity yields a bounded clarification."""
    run(main, ["--request", "Make the dashboard better"])
    spec = SpecVersion.model_validate_json(capsys.readouterr().out)
    assert any(c.question for c in spec.clarifications)


def test_constraints_become_acceptance_criteria(
    capsys: pytest.CaptureFixture[str],
) -> None:
    run(main, ["--request", "Add export", "--constraint", "Exports must be CSV"])
    spec = SpecVersion.model_validate_json(capsys.readouterr().out)
    assert any("CSV" in c.statement for c in spec.acceptance_criteria)


def test_human_format_is_not_json(capsys: pytest.CaptureFixture[str]) -> None:
    run(main, ["--request", "Add logout", "--format", "human"])
    out = capsys.readouterr().out
    assert out
    assert not out.lstrip().startswith("{")


def test_missing_request_is_a_cli_error() -> None:
    assert run(main, []) == EXIT_ERROR
