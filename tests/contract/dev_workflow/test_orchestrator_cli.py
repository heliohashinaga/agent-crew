"""Contract test for the orchestrator role library CLI (T037, FR-009).

The Orchestrator is a pure decision layer: from a Technical Planner's
assessment it produces an Execution Plan per role (model, capability level,
budget, timeout, parallelization, retry policy). It MUST NOT do specialized
work (FR-009). Low vs high complexity must yield different capability
levels (FR-010, T041).
"""

from __future__ import annotations

import json

from ai_factory.dev_workflow.orchestrator.cli import main
from ai_factory.dev_workflow.orchestrator.orchestrator import assess, plan
from ai_factory.shared.cli_util import EXIT_ERROR, run
from ai_factory.shared.spec_store.models import (
    AcceptanceCriterion,
    EdgeCase,
    SpecVersion,
)


def _spec(n_ac: int, n_edge: int) -> SpecVersion:
    return SpecVersion(
        spec_version_id="f-v1-abc",
        intent="Deliver the capability.",
        acceptance_criteria=[
            AcceptanceCriterion(statement=f"Criterion {i}", verified_by="test")
            for i in range(n_ac)
        ],
        definition_of_done="done",
        edge_cases=[
            EdgeCase(description=f"Edge {i}", expected_behavior="handled")
            for i in range(n_edge)
        ],
    )


def test_simple_spec_maps_to_simple_levels() -> None:
    spec = _spec(n_ac=1, n_edge=1)
    assert assess(spec) == "simple"
    ep = plan(spec)
    assert ep.complexity == "simple"
    assert ep.for_role("code_worker").capability_level == "simple"
    assert ep.for_role("code_reviewer").capability_level == "shallow"


def test_complex_spec_maps_to_complex_levels() -> None:
    spec = _spec(n_ac=8, n_edge=5)
    assert assess(spec) == "complex"
    ep = plan(spec)
    assert ep.for_role("code_worker").capability_level == "complex"
    assert ep.for_role("security_reviewer").capability_level == "deep"


def test_plan_assigns_all_dev_roles() -> None:
    ep = plan(_spec(2, 2))
    roles = {r.role for r in ep.roles}
    assert {
        "technical_planner",
        "orchestrator",
        "code_worker",
        "code_reviewer",
        "test_engineer",
        "test_runner",
        "security_reviewer",
    } == roles


def test_plan_budget_tracks_capability() -> None:
    ep = plan(_spec(2, 2))
    worker = ep.for_role("code_worker")
    assert worker.budget.tokens is not None and worker.budget.tokens > 0
    assert ep.budget_total.tokens is None or ep.budget_total.tokens > 0


def test_cli_emits_json_plan(tmp_path, capsys) -> None:
    path = tmp_path / "spec.json"
    path.write_text(_spec(2, 2).model_dump_json(indent=2), encoding="utf-8")
    code = run(main, ["--spec-file", str(path)])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert "roles" in data
    roles = {r["role"] for r in data["roles"]}
    assert "code_worker" in roles and "security_reviewer" in roles


def test_cli_human_format(tmp_path, capsys) -> None:
    path = tmp_path / "spec.json"
    path.write_text(_spec(1, 1).model_dump_json(indent=2), encoding="utf-8")
    code = run(main, ["--spec-file", str(path), "--format", "human"])
    assert code == 0
    out = capsys.readouterr().out
    assert not out.lstrip().startswith("{")


def test_cli_missing_spec_is_error(tmp_path) -> None:
    assert run(main, ["--spec-file", str(tmp_path / "nope.json")]) == EXIT_ERROR
