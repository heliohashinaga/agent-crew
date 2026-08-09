"""Tests for the phase checkpointer (T068, FR-020).

Per-role phase boundaries are recorded so a run can resume without redoing
completed phases. Snapshots are persisted per run+phase and loadable back.
"""

from __future__ import annotations

from datetime import datetime

from ai_factory.shared.state.checkpointer import CheckpointStore


def test_save_and_completed_phases(tmp_path) -> None:
    store = CheckpointStore(tmp_path)
    store.save("run-1", "code_worker", {"files": ["a.py"]})
    store.save("run-1", "test_runner", {"passed": True})
    assert store.completed("run-1") == ["code_worker", "test_runner"]
    assert store.is_completed("run-1", "code_worker") is True
    assert store.is_completed("run-1", "security_reviewer") is False


def test_load_phase_snapshot(tmp_path) -> None:
    store = CheckpointStore(tmp_path)
    store.save("run-1", "planner", {"plan": "x"})
    snap = store.load("run-1", "planner")
    assert snap == {"plan": "x"}


def test_load_unknown_phase_is_none(tmp_path) -> None:
    store = CheckpointStore(tmp_path)
    assert store.load("run-1", "missing") is None
    assert store.completed("nope") == []


def test_checkpoint_records_timestamp(tmp_path) -> None:
    store = CheckpointStore(tmp_path)
    store.save("run-1", "deliver", {"url": "x"})
    ts = store.completed_at("run-1", "deliver")
    assert ts is not None
    datetime.fromisoformat(ts)  # valid ISO ts


def test_persists_across_reopen(tmp_path) -> None:
    CheckpointStore(tmp_path).save("run-1", "code_worker", {"files": ["a.py"]})
    reopened = CheckpointStore(tmp_path)
    assert reopened.is_completed("run-1", "code_worker") is True
    assert reopened.load("run-1", "code_worker")["files"] == ["a.py"]


def test_run_ids_are_isolated(tmp_path) -> None:
    store = CheckpointStore(tmp_path)
    store.save("run-a", "planner", {})
    assert store.completed("run-b") == []
