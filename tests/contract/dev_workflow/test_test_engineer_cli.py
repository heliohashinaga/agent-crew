"""Contract test for the test-engineer role library CLI (T052, FR-011).

Produces a deterministic unit-test suite file covering every acceptance
criterion of the plan, and reports which criteria are covered.
"""

from __future__ import annotations

import json
import py_compile

from ai_factory.dev_workflow.technical_planner.planner import produce_plan
from ai_factory.dev_workflow.test_engineer.cli import main as cli_main
from ai_factory.dev_workflow.test_engineer.engineer import build_test_suite
from ai_factory.shared.cli_util import EXIT_ERROR, run
from ai_factory.shared.spec_store.models import AcceptanceCriterion, SpecVersion


def _plan(n_ac: int = 2) -> object:
    spec = SpecVersion(
        spec_version_id="f-v1-abc",
        intent="Add a search helper",
        acceptance_criteria=[
            AcceptanceCriterion(statement=f"Behaviour {i}", verified_by="test")
            for i in range(n_ac)
        ],
        definition_of_done="done",
        edge_cases=[],
    )
    return produce_plan(spec)


def test_build_test_suite_writes_runnable_suite(tmp_path) -> None:
    product = build_test_suite(_plan(), tmp_path)
    assert product.files
    for rel in product.files:
        py_compile.compile(str(tmp_path / rel), doraise=True)


def test_suite_covers_every_acceptance_criterion(tmp_path) -> None:
    plan = _plan(n_ac=3)
    product = build_test_suite(plan, tmp_path)
    # Each AC from the plan's subtasks appears in `covered` exactly once.
    existing = {c for sub in plan.subtasks for c in sub.acceptance_criteria}
    assert existing
    assert set(product.covered) == existing
    assert len(product.covered) == len(existing)


def test_cli_emits_suite_json(tmp_path, capsys) -> None:
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(_plan().model_dump_json(), encoding="utf-8")
    repo = tmp_path / "repo"
    code = run(cli_main, ["--plan-file", str(plan_file), "--repo", str(repo)])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["files"]
    assert (repo / data["files"][0]).exists()


def test_cli_missing_plan_is_error(tmp_path) -> None:
    assert (
        run(
            cli_main,
            ["--plan-file", str(tmp_path / "nope.json"), "--repo", str(tmp_path)],
        )
        == EXIT_ERROR
    )
