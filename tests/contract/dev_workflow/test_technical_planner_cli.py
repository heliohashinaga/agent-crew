"""Contract test for the technical-planner role library CLI (T044, FR-007/008).

The planner maps an approved spec to a TechnicalPlan + Assessment
(complexity, risk, architecture impact, test scope, security surface,
documentation) and produces an ADR ONLY when architecture impact is real
(FR-008).
"""

from __future__ import annotations

import json

from ai_factory.dev_workflow.technical_planner.cli import main
from ai_factory.dev_workflow.technical_planner.planner import assess, produce_plan
from ai_factory.shared.cli_util import EXIT_ERROR, run
from ai_factory.shared.spec_store.models import AcceptanceCriterion, SpecVersion


def _spec(intent: str, n_ac: int = 1, **overrides) -> SpecVersion:
    kwargs = {
        "spec_version_id": "f-v1-abc",
        "intent": intent,
        "acceptance_criteria": [
            AcceptanceCriterion(statement=f"Behaviour {i}", verified_by="test")
            for i in range(n_ac)
        ],
        "definition_of_done": "done",
    }
    kwargs.update(overrides)
    return SpecVersion(**kwargs)


def test_simple_fix_gets_no_adr() -> None:
    """FR-008: NO ADR for a simple, conventional fix."""
    spec = _spec("Fix typo in login button label")
    plan = produce_plan(spec)
    assert plan.adr is None
    assert plan.assessment.architecture_impact is False
    assert plan.assessment.complexity == "simple"


def test_architecture_choice_gets_one_adr() -> None:
    """FR-008: an ADR IS created for a significant architectural decision."""
    spec = _spec("Migrate the user store from files to Postgres")
    plan = produce_plan(spec)
    assert plan.adr is not None
    assert plan.assessment.architecture_impact is True
    assert plan.adr.title
    assert plan.adr.trade_offs and plan.adr.alternatives


def test_assessment_surface_detection() -> None:
    spec = _spec("Add password reset with emailed tokens")
    a = assess(spec)
    assert a.security_surface  # auth-related spec exposes a security surface
    assert a.risk in ("medium", "high")


def test_subtasks_are_generated_per_acceptance_criterion() -> None:
    spec = _spec("Add a binary search helper", n_ac=2)
    plan = produce_plan(spec)
    assert len(plan.subtasks) >= 2
    assert all(t.acceptance_criteria for t in plan.subtasks)


def test_cli_emits_plan_json(tmp_path, capsys) -> None:
    path = tmp_path / "spec.json"
    path.write_text(
        _spec("Fix typo in login button label").model_dump_json(), encoding="utf-8"
    )
    code = run(main, ["--spec-file", str(path)])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["assessment"]["complexity"] == "simple"
    assert data["adr"] is None
    assert len(data["subtasks"]) >= 1


def test_cli_missing_spec_is_error(tmp_path) -> None:
    assert run(main, ["--spec-file", str(tmp_path / "nope.json")]) == EXIT_ERROR
