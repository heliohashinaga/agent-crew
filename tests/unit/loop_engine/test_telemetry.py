"""Unit tests for per-iteration telemetry (US5, T074, FR-008)."""

from __future__ import annotations

from ai_factory.loop_engine.engine import run_loop
from ai_factory.loop_engine.models import LoopConfig, LoopStatus
from ai_factory.shared.telemetry.store import FileTelemetryStore
from tests.unit.loop_engine.fakes import FakeActor, FakeGate


def test_telemetry_emits_role_loop_engine(tmp_path) -> None:  # noqa: ANN001
    actor = FakeActor()
    gate = FakeGate(pass_calls=[1])  # 2 iterations total
    config = LoopConfig(actor=actor, gate=gate, max_iterations=5, run_id="telem")
    result = run_loop(config, telemetry=True, telemetry_dir=tmp_path)
    assert result.status == LoopStatus.PASSED

    store = FileTelemetryStore(tmp_path)
    records = store.get("telem")
    assert len(records) >= 1  # deduped by role/attempt
    for rec in records:
        assert rec["role"] == "loop_engine"
        assert "password" not in str(rec).lower()
        assert "apikey" not in str(rec).lower()


def test_telemetry_no_secret_values(tmp_path) -> None:  # noqa: ANN001
    actor = FakeActor()
    gate = FakeGate(pass_calls=[0])
    config = LoopConfig(actor=actor, gate=gate, max_iterations=3, run_id="telem2")
    run_loop(config, telemetry=True, telemetry_dir=tmp_path)

    data = (tmp_path / "telem2.jsonl").read_text(encoding="utf-8")
    # secrets redacted at store boundary; no secret-looking values
    assert "password" not in data.lower()
    assert "apikey" not in data.lower()


def test_telemetry_exhausted_includes_status(tmp_path) -> None:  # noqa: ANN001
    actor = FakeActor()
    gate = FakeGate(never_pass=True)
    config = LoopConfig(actor=actor, gate=gate, max_iterations=2, run_id="telem3")
    result = run_loop(config, telemetry=True, telemetry_dir=tmp_path)
    assert result.status == LoopStatus.EXHAUSTED

    store = FileTelemetryStore(tmp_path)
    recs = store.get("telem3")
    assert recs
    last = recs[-1]
    assert "exhausted" in str(last) or "fail" in str(last)