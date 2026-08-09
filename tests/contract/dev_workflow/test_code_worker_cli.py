"""Contract test for the code-worker role library CLI (T048, FR-011).

The code worker implements the technical plan: writes implementation modules
with unit tests into the repo, locally validates the modules (compile), and
produces documentation files when the assessment requires it.
"""

from __future__ import annotations

import json
import py_compile
from pathlib import Path

from ai_factory.dev_workflow.code_worker.cli import main as cli_main
from ai_factory.dev_workflow.code_worker.worker import implement
from ai_factory.dev_workflow.technical_planner.planner import produce_plan
from ai_factory.shared.cli_util import EXIT_ERROR, run
from ai_factory.shared.spec_store.models import AcceptanceCriterion, SpecVersion


def _plan(intent: str = "Add a binary search helper") -> object:
    spec = SpecVersion(
        spec_version_id="f-v1-abc",
        intent=intent,
        acceptance_criteria=[
            AcceptanceCriterion(
                statement="Search returns the index of a found element",
                verified_by="test",
            )
        ],
        definition_of_done="done",
        edge_cases=[],
    )
    return produce_plan(spec)


def test_implement_writes_modules_and_tests(tmp_path: Path) -> None:
    product = implement(_plan(), tmp_path)
    assert product.validation == "passed"
    assert len(product.files) >= 2
    written = [p for p in product.files if p.endswith(".py")]
    assert written
    # Every written module compiles.
    for rel in written:
        py_compile.compile(str(tmp_path / rel), doraise=True)


def test_implementation_covers_unit_tests(tmp_path: Path) -> None:
    product = implement(_plan(), tmp_path)
    assert any("test_" in f for f in product.files)


def test_implement_writes_documentation_when_required(tmp_path: Path) -> None:
    plan = _plan(intent="Migrate the user store to Postgres")
    product = implement(plan, tmp_path)
    assert product.doc_written is True
    assert (tmp_path / "README.md").exists()


def test_implement_skips_docs_when_not_required(tmp_path: Path) -> None:
    product = implement(_plan(intent="Fix typo in label"), tmp_path)
    assert product.doc_written is False
    assert not (tmp_path / "README.md").exists()


def test_cli_writes_and_emits_json(tmp_path: Path, capsys) -> None:
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(_plan().model_dump_json(), encoding="utf-8")
    repo = tmp_path / "repo"
    code = run(cli_main, ["--plan-file", str(plan_file), "--repo", str(repo)])
    assert code == 0
    product = json.loads(capsys.readouterr().out)
    assert product["validation"] == "passed"
    assert (repo / product["files"][0]).exists()


def test_cli_missing_plan_is_error(tmp_path) -> None:
    assert (
        run(
            cli_main,
            ["--plan-file", str(tmp_path / "nope.json"), "--repo", str(tmp_path)],
        )
        == EXIT_ERROR
    )
