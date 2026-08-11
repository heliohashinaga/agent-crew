"""Integration test for the spec→dev hand-off seam (FR-006/009, SC-017).

The `spec_version_id` single join key is removed (fr-009); a folder-driven
`dev-run` carries no factory-issued version and its identity derives from the
folder feature name (residual mapping, FR-006). This exercises spec-store
publishing, by-reference loading of legacy specs, and folder-identity
traceability.
"""

from __future__ import annotations

import json

import pytest

from ai_factory.shared.spec_store.handoff import (
    PublicationError,
    load_spec_by_ref,
    publish_approved,
)
from ai_factory.shared.spec_store.models import ApprovalStatus, EdgeCase, SpecVersion
from ai_factory.shared.spec_store.store import FileSpecStore

pytestmark = pytest.mark.integration


def _approved(version: int = 1) -> SpecVersion:
    return SpecVersion(
        spec_run_id=f"spec-run-{version}",
        version=version,
        intent="Lock a user account after failed attempts.",
        acceptance_criteria=[],
        definition_of_done="done",
        edge_cases=[
            EdgeCase(
                description="Max attempts reached",
                expected_behavior="Account is locked",
            )
        ],
        approval_status=ApprovalStatus.APPROVED,
        human_approved=True,
    )


def test_publish_assigns_stable_version_and_run(tmp_path) -> None:
    store = FileSpecStore(tmp_path)
    published = publish_approved(_approved(), store)
    assert published.spec_version_id
    assert published.spec_run_id == "spec-run-1"
    # Stable: republishing the same version yields the same id.
    again = publish_approved(_approved(), store)
    assert again.spec_version_id == published.spec_version_id


def test_load_spec_by_reference(tmp_path) -> None:
    store = FileSpecStore(tmp_path)
    published = publish_approved(_approved(version=2), store)
    loaded = load_spec_by_ref(published.spec_version_id, store)
    assert loaded is not None
    assert loaded.spec_version_id == published.spec_version_id
    assert loaded.spec_run_id == "spec-run-2"


def test_load_unknown_reference_returns_none(tmp_path) -> None:
    store = FileSpecStore(tmp_path)
    assert load_spec_by_ref("nope-v1-deadbeef", store) is None


def test_cannot_publish_unapproved_spec(tmp_path) -> None:
    """FR-005: only human-approved specs may be published."""
    store = FileSpecStore(tmp_path)
    draft = _approved()
    draft.approval_status = ApprovalStatus.DRAFT
    draft.human_approved = False
    with pytest.raises(PublicationError):
        publish_approved(draft, store)


def test_dev_traceability_pairs_are_recorded(tmp_path) -> None:
    """SC-017: a dev run carries ``spec_version_id`` + ``spec_run_id``."""
    store = FileSpecStore(tmp_path)
    published = publish_approved(_approved(version=3), store)
    dev_ref = {
        "spec_version_id": published.spec_version_id,
        "spec_run_id": published.spec_run_id,
    }
    assert dev_ref["spec_version_id"]
    assert dev_ref["spec_run_id"] == "spec-run-3"
    assert load_spec_by_ref(dev_ref["spec_version_id"], store) is not None


def test_spec_and_dev_runs_are_linked_by_reference(tmp_path, capsys) -> None:
    """FR-009: the dev-run join key is the folder feature name, not a version.

    A folder-driven ``dev-run`` consumes the speckit folder as-is and refuses
    a ``--spec-version`` (single join key removed). Its traceability identity
    is the folder feature name, never a factory-issued ``spec_version_id``.
    """
    from pathlib import Path

    from ai_factory.cli.dev_run import main as dev_main
    from ai_factory.shared.cli_util import run

    folder = Path(__file__).resolve().parents[1] / "fixtures" / "specs" / "full"
    code = run(
        dev_main,
        [
            str(folder),
            "--repo",
            str(tmp_path / "repo"),
            "--run-dir",
            str(tmp_path / "runstate"),
            "--sandbox",
            "fake",
            "--git-host",
            "fake",
            "--format",
            "json",
        ],
    )
    assert code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["outcome"] == "delivered"
    # Identity derives from the folder feature name (FR-011/012), not a version.
    assert summary["spec_version_id"] == "full"
    # No separate factory-issued spec_run_id join is emitted (FR-009).
    assert summary.get("spec_run_id") in (None, "")
