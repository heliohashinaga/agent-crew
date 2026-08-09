"""Tests for the local-filesystem spec store (T010, FR-025).

FR-025: the spec workflow emits an approved spec with a stable
``spec_version_id``, persisted locally; a dev run loads that version by
reference. The store must therefore version specs monotonically per feature
and produce stable ids.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_factory.shared.spec_store.models import (
    AcceptanceCriterion,
    EdgeCase,
    SpecVersion,
)
from ai_factory.shared.spec_store.store import FileSpecStore, StoreError


def _spec(version: int = 1, **overrides: object) -> SpecVersion:
    kwargs: dict[str, object] = {
        "spec_run_id": "spec-run-1",
        "version": version,
        "intent": "Add a password-reset flow",
        "rationale": "Users need to recover access",
        "acceptance_criteria": [
            AcceptanceCriterion(
                statement=(
                    "Given a registered user, resetting the password sends an email"
                ),
                verified_by="integration test",
            )
        ],
        "definition_of_done": "Password reset E2E passes",
        "edge_cases": [
            EdgeCase(description="Unknown email", expected_behavior="Generic error")
        ],
        "clarifications": [],
        "assumptions": [],
        "approval_status": "approved",
        "human_approved": True,
    }
    kwargs.update(overrides)
    return SpecVersion(**kwargs)


def test_save_assigns_stable_version_id(tmp_path: Path) -> None:
    store = FileSpecStore(tmp_path)
    saved = store.save(_spec(version=1))
    assert saved.spec_version_id
    # Saving the same version again yields the SAME id (stable).
    again = store.save(_spec(version=1))
    assert again.spec_version_id == saved.spec_version_id


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    store = FileSpecStore(tmp_path)
    saved = store.save(_spec(version=1))
    loaded = store.load(saved.spec_version_id)
    assert loaded is not None
    assert loaded.spec_version_id == saved.spec_version_id
    assert loaded.intent == "Add a password-reset flow"
    assert loaded.acceptance_criteria[0].statement.startswith("Given a registered user")
    assert loaded.edge_cases[0].description == "Unknown email"
    assert loaded.approval_status == "approved"
    assert loaded.human_approved is True
    assert loaded.spec_run_id == "spec-run-1"


def test_load_missing_version_returns_none(tmp_path: Path) -> None:
    store = FileSpecStore(tmp_path)
    assert store.load("does-not-exist-v1-00000000") is None


def test_versions_monotonic_per_feature(tmp_path: Path) -> None:
    store = FileSpecStore(tmp_path)
    v1 = store.save(_spec(version=1))
    v2 = store.save(_spec(version=2))
    assert v1.version == 1
    assert v2.version == 2
    assert v1.spec_version_id != v2.spec_version_id


def test_store_auto_assigns_next_version(tmp_path: Path) -> None:
    store = FileSpecStore(tmp_path)
    first = store.save(_spec(version=1))
    second = store.save(_spec(version=2))
    assert (second.version, second.spec_run_id) == (2, "spec-run-1")
    assert first.spec_run_id == "spec-run-1"


def _password_reset_slug() -> str:
    return _spec(version=1).feature_slug


def test_list_feature_versions_ordered(tmp_path: Path) -> None:
    store = FileSpecStore(tmp_path)
    store.save(_spec(version=2, spec_run_id="run-b"))
    store.save(_spec(version=1, spec_run_id="run-a"))
    versions = store.list_feature_versions(_password_reset_slug())
    assert [v.version for v in versions] == [1, 2]
    assert [v.spec_run_id for v in versions] == ["run-a", "run-b"]


def test_latest_returns_highest_version(tmp_path: Path) -> None:
    store = FileSpecStore(tmp_path)
    v1 = store.save(_spec(version=1))
    store.save(_spec(version=2))
    latest = store.latest(_password_reset_slug())
    assert latest is not None
    assert latest.version == 2
    assert latest.spec_version_id != v1.spec_version_id


def test_ids_are_stable_across_store_reopen(tmp_path: Path) -> None:
    store1 = FileSpecStore(tmp_path)
    saved = store1.save(_spec(version=1))
    store2 = FileSpecStore(tmp_path)
    assert store2.load(saved.spec_version_id) is not None


def test_approved_requires_human_approval(tmp_path: Path) -> None:
    """FR-005: ``human_approved`` must be true before ``approved``."""
    with pytest.raises(ValidationError):
        _spec(version=1, approval_status="approved", human_approved=False)


def test_draft_does_not_require_human_approval() -> None:
    spec = _spec(version=1, approval_status="draft", human_approved=False)
    assert spec.approval_status == "draft"


def test_different_features_do_not_collide(tmp_path: Path) -> None:
    store = FileSpecStore(tmp_path)
    a = store.save(_spec(version=1, intent="Feature A"))
    b = store.save(_spec(version=1, intent="Feature B"))
    assert a.spec_version_id != b.spec_version_id
    assert len(store.list_feature_versions("feature-a")) == 1
    assert len(store.list_feature_versions("feature-b")) == 1


def test_corrupt_file_raises_store_error(tmp_path: Path) -> None:
    store = FileSpecStore(tmp_path)
    saved = store.save(_spec(version=1))
    (tmp_path / saved.feature_slug / f"{saved.spec_version_id}.json").write_text(
        "{not json"
    )
    with pytest.raises(StoreError):
        store.load(saved.spec_version_id)
