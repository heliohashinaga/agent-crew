"""Tests for the core state models (T006).

Verifies :mod:`factory_state` against `data-model.md`: ``ApprovalStatus``,
``Checkpoint``, ``RunState`` (top-level run envelope), and ``FactoryState``
(the LangGraph state envelope).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ai_factory.shared.state.factory_state import (
    ApprovalStatus,
    Checkpoint,
    FactoryState,
    RunState,
)


def test_approval_status_enum_values() -> None:
    """``ApprovalStatus`` matches the data-model lifecycle exactly."""
    assert [k.value for k in ApprovalStatus] == [
        "draft",
        "under_review",
        "approved",
        "rejected",
        "superseded",
    ]


def test_factory_state_defaults() -> None:
    state = FactoryState(run_id="run-1", workflow="spec")
    assert state.approval_status is ApprovalStatus.DRAFT
    assert state.checkpoints == []
    assert state.payload == {}
    assert state.spec_version_id is None
    assert state.spec_run_id is None
    assert isinstance(state.updated_at, datetime)


def test_factory_state_rejects_unknown_workflow() -> None:
    with pytest.raises(ValidationError):
        FactoryState(run_id="run-1", workflow="bogus")


def test_factory_state_accepts_dev_workflow_and_handoff_refs() -> None:
    state = FactoryState(
        run_id="run-2",
        workflow="dev",
        spec_version_id="feature-v1-abc",
        spec_run_id="spec-run-9",
        approval_status=ApprovalStatus.APPROVED,
    )
    assert state.spec_version_id == "feature-v1-abc"
    assert state.spec_run_id == "spec-run-9"


def test_checkpoint_defaults() -> None:
    cp = Checkpoint(
        run_id="run-1", workflow="dev", phase="orchestrator", state_ref="ckpt#1"
    )
    assert cp.completed is False
    assert isinstance(cp.created_at, datetime)


def test_checkpoint_completed_flag() -> None:
    cp = Checkpoint(
        run_id="run-1",
        workflow="dev",
        phase="code_worker",
        state_ref="ckpt#2",
        completed=True,
    )
    assert cp.completed is True


def test_run_state_envelope_defaults() -> None:
    run = RunState(run_id="run-1", workflow="spec")
    assert run.status == "planned"
    assert run.checkpoints == []
    assert run.telemetry == []
    assert run.spec_version_id is None


def test_run_state_carries_handoff_refs() -> None:
    """Dev runs carry ``spec_version_id`` + ``spec_run_id`` (FR-025, SC-017)."""
    run = RunState(
        run_id="dev-run-1",
        workflow="dev",
        spec_version_id="feature-v1-abc",
        spec_run_id="spec-run-9",
        status="executing",
    )
    assert run.spec_version_id == "feature-v1-abc"
    assert run.spec_run_id == "spec-run-9"
    assert run.status == "executing"


def test_run_state_status_literal() -> None:
    with pytest.raises(ValidationError):
        RunState(run_id="run-1", workflow="dev", status="donezo")


def test_checkpoint_appends_to_run_and_factory_state() -> None:
    cp = Checkpoint(
        run_id="run-1", workflow="dev", phase="code_worker", state_ref="ckpt#1"
    )
    factory = FactoryState(run_id="run-1", workflow="dev")
    factory.checkpoints.append(cp)
    run = RunState(run_id="run-1", workflow="dev")
    run.checkpoints.append(cp)
    assert factory.checkpoints[0].phase == "code_worker"
    assert run.checkpoints[0].completed is False


def test_json_round_trip_serde() -> None:
    state = FactoryState(
        run_id="run-1",
        workflow="dev",
        spec_version_id="v1",
        approval_status=ApprovalStatus.APPROVED,
    )
    loaded = FactoryState.model_validate_json(state.model_dump_json())
    assert loaded == state
    assert loaded.approval_status is ApprovalStatus.APPROVED


def test_datetime_is_utc_aware() -> None:
    state = FactoryState(run_id="run-1", workflow="spec")
    assert state.updated_at.tzinfo is not None
    assert state.updated_at.utcoffset() == UTC.utcoffset(None)
