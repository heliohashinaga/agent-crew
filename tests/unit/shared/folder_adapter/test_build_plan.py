"""Unit tests for TechnicalPlan assembly (T014/T015, FR-001/004/011/012)."""

from pathlib import Path

import pytest

from ai_factory.shared.folder_adapter.build_plan import build_plan


@pytest.fixture
def full_folder() -> Path:
    return Path(__file__).resolve().parents[3] / "fixtures" / "specs" / "full"


@pytest.fixture
def no_plan_folder() -> Path:
    return Path(__file__).resolve().parents[3] / "fixtures" / "specs" / "no-plan"


def test_build_plan_from_full_folder(full_folder: Path) -> None:
    result = build_plan(full_folder)
    plan = result.plan
    assert plan.goal == "Full Fixture — User Session Timeout"
    assert plan.spec_version_id == "full"  # identity = folder feature name
    assert len(plan.subtasks) == 7
    assert plan.subtasks[0].source_task_id == "T001"


def test_assessment_imported_from_plan(full_folder: Path) -> None:
    result = build_plan(full_folder)
    assert result.plan.assessment.security_surface  # hashed tokens (SECURITY)
    assert result.plan.assessment.architecture_impact is True  # Postgres


def test_plan_without_plan_md_degrades(no_plan_folder: Path) -> None:
    result = build_plan(no_plan_folder)
    assert result.plan.assessment.test_scope == []
    assert result.inferred  # inference note present


def test_paths_normalized_and_absolute_dropped(full_folder: Path) -> None:
    result = build_plan(full_folder)
    for sub in result.plan.subtasks:
        for f in sub.files:
            assert not f.startswith("/")
            assert "C:" not in f
