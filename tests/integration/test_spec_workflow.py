"""Integration test for the Specification Workflow (T020, FR-002/004/005/024/025).

Runs the full LangGraph spec workflow end-to-end with a tmp filesystem store.
The human-approval gate (FR-005) is exercised via the ``interrupt()`` /
``Command(resume=...)`` resume protocol. The graph is deterministic and
network-free (no container runtime required), but it is marked ``integration``
because it crosses the full spec pipeline and persists a real record.
"""

from __future__ import annotations

import pytest
from langgraph.types import Command

from ai_factory.shared.spec_store.handoff import load_spec_by_ref
from ai_factory.shared.spec_store.models import ApprovalStatus, FeatureRequest
from ai_factory.shared.spec_store.store import FileSpecStore
from ai_factory.spec_workflow.graph import build_spec_graph

pytestmark = pytest.mark.integration


def _app(tmp_path: pytest.TempPathFactory):
    store = FileSpecStore(tmp_path / "specs")
    app = build_spec_graph(store)
    return store, app


def _init(request_text: str, thread: str) -> dict:
    return {
        "request": FeatureRequest(raw_text=request_text, constraints=[]),
        "review_rounds": 0,
        "feedback": "",
        "spec_run_id": f"spec-run-{thread}",
        "outcome": "drafting",
        "spec": None,
    }


def test_approve_path_persists_approved_spec(tmp_path: pytest.TempPathFactory) -> None:
    """An approvable request pauses at the gate; approval publishes the spec."""
    store, app = _app(tmp_path)
    cfg = {"configurable": {"thread_id": "t-approve"}}
    initial = _init(
        "Sessions must expire after 30 minutes to end stale sessions", "t-approve"
    )

    result = app.invoke(initial, cfg)
    # Paused at the human-approval interrupt (FR-005).
    assert "__interrupt__" in result
    assert (
        result["__interrupt__"][0].value
        == "Approve this spec version? (continue to publish)"
    )
    assert result["outcome"] == "drafting"

    # A human approves → the spec is published with a stable id.
    resumed = app.invoke(Command(resume=True), cfg)
    assert resumed["outcome"] == "approved"
    assert resumed["spec"].approval_status == ApprovalStatus.APPROVED
    assert resumed["spec"].human_approved is True
    assert resumed["spec"].spec_version_id
    assert resumed["spec"].spec_run_id == "spec-run-t-approve"

    # The approved, versioned record is loadable by reference (FR-025).
    persisted = load_spec_by_ref(resumed["spec"].spec_version_id, store)
    assert persisted is not None
    assert persisted.intent == resumed["spec"].intent


def test_under_review_until_human_approves(
    tmp_path: pytest.TempPathFactory,
) -> None:
    """Denying approval leaves the spec under_review, not approved (FR-005)."""
    store, app = _app(tmp_path)
    cfg = {"configurable": {"thread_id": "t-defer"}}
    initial = _init(
        "Sessions must expire after 30 minutes to end stale sessions", "t-defer"
    )

    app.invoke(initial, cfg)
    resumed = app.invoke(Command(resume=False), cfg)
    assert resumed["outcome"] == "needs_clarification"
    assert resumed["spec"].approval_status == ApprovalStatus.UNDER_REVIEW
    assert resumed["spec"].human_approved is False


def test_rejected_when_review_rounds_exhausted(
    tmp_path: pytest.TempPathFactory,
) -> None:
    """A spec that never passes review is rejected after bounded cycles (FR-006)."""
    store, app = _app(tmp_path)
    cfg = {"configurable": {"thread_id": "t-reject"}}
    # No edge cases are derivable → reviewer rejects every round → reject.
    initial = _init("Add a feature to improve the dashboard", "t-reject")

    result = app.invoke(initial, cfg)
    assert result["outcome"] == "rejected"
    assert "__interrupt__" not in result


def test_negative_approval_never_publishes(tmp_path: pytest.TempPathFactory) -> None:
    """A deferred/rejected spec must NOT be persisted as an approved version."""
    store, app = _app(tmp_path)
    cfg = {"configurable": {"thread_id": "t-nopub"}}
    initial = _init(
        "Sessions must expire after 30 minutes to end stale sessions", "t-nopub"
    )

    app.invoke(initial, cfg)
    app.invoke(Command(resume=False), cfg)
    versions = store.list_feature_versions(
        "sessions-must-expire-after-30-minutes-to-end-stale-sessions"
    )
    assert versions == []


def test_spec_human_gate_resumes_in_place(tmp_path) -> None:
    """T086: the spec interrupt resumes in place — no restart, one version."""

    from langgraph.types import Command

    store, app = _app(tmp_path)
    cfg = {"configurable": {"thread_id": "t-resume"}}
    initial = _init(
        "Sessions must expire after 30 minutes to end stale sessions", "t-resume"
    )

    # First invoke pauses at the human-approval gate (FR-005) — run not finished.
    paused = app.invoke(initial, cfg)
    assert "__interrupt__" in paused
    assert paused["outcome"] == "drafting"

    # Resume the SAME run by answering the gate; it continues, not restarts.
    resumed = app.invoke(Command(resume=True), cfg)
    assert resumed["outcome"] == "approved"
    assert resumed["spec"].approval_status == ApprovalStatus.APPROVED
    assert resumed["spec"].spec_version_id

    # Resume posted exactly one published version (no duplicates from restart).
    versions = store.list_feature_versions(resumed["spec"].feature_slug)
    assert len(versions) == 1
