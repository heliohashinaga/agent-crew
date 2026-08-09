"""Tests for the telemetry store (T031, SC-003, FR-018).

Records are persisted keyed by ``run_id`` and queried locally in well under
seconds (SC-003). Records are sanitized/redacted at the store boundary so no
secret is persisted (FR-018/SC-010).
"""

from __future__ import annotations

from ai_factory.shared.telemetry.record import SpecRoleInvocation, TelemetryRecord
from ai_factory.shared.telemetry.store import FileTelemetryStore


def _inv(role: str, attempt: int = 1, **overrides) -> SpecRoleInvocation:
    kwargs = {
        "role": role,
        "attempt": attempt,
        "telemetry": TelemetryRecord(result="pass"),
    }
    kwargs.update(overrides)
    return SpecRoleInvocation(**kwargs)  # type: ignore[arg-type]


def test_add_and_get_round_trip(tmp_path) -> None:
    store = FileTelemetryStore(tmp_path)
    store.add("run-1", _inv("spec_agent"))
    records = store.get("run-1")
    assert len(records) == 1
    assert records[0]["role"] == "spec_agent"
    assert records[0]["attempt"] == 1


def test_get_unknown_run_is_empty(tmp_path) -> None:
    store = FileTelemetryStore(tmp_path)
    assert store.get("does-not-exist") == []


def test_get_unknown_run_via_query(tmp_path) -> None:
    store = FileTelemetryStore(tmp_path)
    assert store.get_latest("does-not-exist") is None


def test_records_are_deduplicated_by_role_attempt(tmp_path) -> None:
    store = FileTelemetryStore(tmp_path)
    store.add("run-1", _inv("spec_agent", attempt=1, outcome="rework"))
    store.add("run-1", _inv("spec_agent", attempt=1, outcome="pass"))
    records = store.get("run-1")
    assert len(records) == 1
    assert records[0]["outcome"] == "pass"  # last write wins


def test_redaction_at_store_boundary(tmp_path) -> None:
    """FR-018/SC-010: secrets never touch disk."""
    store = FileTelemetryStore(tmp_path)
    store.add(
        "run-1", _inv("spec_agent", feedback="Authorization: Bearer losttoken123")
    )
    raw = (tmp_path / "run-1.jsonl").read_text(encoding="utf-8")
    assert "losttoken123" not in raw
    assert store.get("run-1")[0]["feedback"].endswith("[REDACTED]")


def test_persists_across_reopen(tmp_path) -> None:
    FileTelemetryStore(tmp_path).add("run-1", _inv("requirements_reviewer", attempt=2))
    reopened = FileTelemetryStore(tmp_path)
    records = reopened.get("run-1")
    assert len(records) == 1
    assert records[0]["role"] == "requirements_reviewer"


def test_list_runs(tmp_path) -> None:
    store = FileTelemetryStore(tmp_path)
    store.add("run-a", _inv("spec_agent"))
    store.add("run-b", _inv("requirements_reviewer"))
    runs = store.list_runs()
    assert "run-a" in runs and "run-b" in runs


def test_get_latest_returns_last_record(tmp_path) -> None:
    store = FileTelemetryStore(tmp_path)
    store.add("run-1", _inv("spec_agent", attempt=1))
    store.add("run-1", _inv("requirements_reviewer", attempt=1))
    latest = store.get_latest("run-1")
    assert latest["role"] == "requirements_reviewer"
