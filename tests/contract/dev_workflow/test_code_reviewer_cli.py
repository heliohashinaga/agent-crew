"""Contract test for the code-reviewer role library CLI (T050, FR-011/FR-008).

Reviews the code worker's product: implemented files exist and compile,
unit tests accompany each module, documentation/ADR artifacts are present
when the plan requires them (FR-008 adherence), and rejections carry
specific reasons.
"""

from __future__ import annotations

import json

from ai_factory.dev_workflow.code_reviewer.cli import main as cli_main
from ai_factory.dev_workflow.code_reviewer.reviewer import review
from ai_factory.dev_workflow.code_worker.worker import CodeWorkProduct, implement
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


def _implemented(plan, repo) -> CodeWorkProduct:
    return implement(plan, repo)


def test_review_approves_good_product(tmp_path) -> None:
    plan = _plan()
    product = _implemented(plan, tmp_path)
    verdict = review(product, plan, tmp_path)
    assert verdict.approved is True
    assert verdict.reasons == []


def test_review_rejects_failed_validation(tmp_path) -> None:
    plan = _plan()
    product = _implemented(plan, tmp_path)
    product = product.model_copy(
        update={"validation": "failed", "errors": ["x broken"]}
    )
    verdict = review(product, plan, tmp_path)
    assert verdict.approved is False
    assert any("validation" in r for r in verdict.reasons)


def test_review_rejects_missing_impl_files(tmp_path) -> None:
    plan = _plan()
    product = _implemented(plan, tmp_path)
    # Delete every implementation module from disk.
    for rel in product.files:
        (tmp_path / rel).unlink()
    verdict = review(product, plan, tmp_path)
    assert verdict.approved is False
    assert any(
        "missing" in r.lower() or "not found" in r.lower() for r in verdict.reasons
    )


def test_review_rejects_missing_tests(tmp_path) -> None:
    plan = _plan()
    product = _implemented(plan, tmp_path)
    for rel in product.files:
        if rel.startswith("test_"):
            (tmp_path / rel).unlink()
    verdict = review(product, plan, tmp_path)
    assert verdict.approved is False
    assert any("test" in r.lower() for r in verdict.reasons)


def test_adr_adherence_requires_recorded_decision(tmp_path) -> None:
    """T046: an architectural plan must have its ADR committed in the repo."""
    plan = _plan(intent="Migrate the user store to Postgres")
    product = _implemented(plan, tmp_path)
    assert plan.adr is not None
    verdict = review(product, plan, tmp_path)
    assert verdict.approved is True  # ADR doc present -> adherence holds


def test_adr_adherence_rejects_missing_record(tmp_path) -> None:
    plan = _plan(intent="Migrate the user store to Postgres")
    product = _implemented(plan, tmp_path)
    import shutil

    shutil.rmtree(tmp_path / "docs")
    verdict = review(product, plan, tmp_path)
    assert verdict.approved is False
    assert any("adr" in r.lower() for r in verdict.reasons)


def test_cli_emits_verdict(tmp_path, capsys) -> None:
    plan = _plan()
    product = _implemented(plan, tmp_path)
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(plan.model_dump_json(), encoding="utf-8")
    product_file = tmp_path / "product.json"
    product_file.write_text(product.model_dump_json(), encoding="utf-8")
    code = run(
        cli_main,
        [
            "--plan-file",
            str(plan_file),
            "--product-file",
            str(product_file),
            "--repo",
            str(tmp_path),
        ],
    )
    assert code == 0
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["approved"] is True


def test_cli_missing_input_is_error(tmp_path) -> None:
    assert (
        run(
            cli_main,
            [
                "--plan-file",
                str(tmp_path / "a.json"),
                "--product-file",
                str(tmp_path / "b.json"),
                "--repo",
                str(tmp_path),
            ],
        )
        == EXIT_ERROR
    )
