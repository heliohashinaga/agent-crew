"""Integration test for the spec→dev hand-off seam (T024/T025, FR-025, SC-017).

A Development run must inherit ONLY a reference (``spec_version_id`` +
``spec_run_id``) from a Specification run and load the spec by that reference
— never re-derive requirements. This exercises publish-by-reference and the
guarantees around publishing.
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
    """T085/FR-024+SC-017: two distinct traces joined only by a reference.

    The Specification run emits an approved, versioned SpecVersion; the
    Development run consumes that SAME spec by ``spec_version_id`` — it
    never re-derives the requirements.
    """
    from ai_factory.cli.dev_run import main as dev_main
    from ai_factory.cli.spec_run import main as spec_main
    from ai_factory.shared.cli_util import run

    spec_store = tmp_path / "specs"
    # Trace 1: spec run approves a spec and publishes a version.
    code = run(
        spec_main,
        [
            "--request",
            "Sessions must expire after 30 minutes to end stale sessions",
            "--auto-approve",
            "--store",
            str(spec_store),
            "--format",
            "json",
        ],
    )
    assert code == 0
    published = SpecVersion.model_validate_json(capsys.readouterr().out)
    assert published.approval_status == ApprovalStatus.APPROVED

    # Trace 2: dev run loads by the published reference (SC-017).
    code = run(
        dev_main,
        [
            "--spec-version",
            published.spec_version_id,
            "--spec-store",
            str(spec_store),
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
    # Distinct traces, connected ONLY by the reference.
    assert summary["spec_version_id"] == published.spec_version_id
    assert summary["spec_run_id"] is not None
    assert summary["spec_version_id"] != summary["spec_run_id"]
