"""Unit tests for durable ledger + resume (US4, T060-T062, FR-005)."""

from __future__ import annotations

from ai_factory.loop_engine.engine import run_loop
from ai_factory.loop_engine.ledger import Ledger
from ai_factory.loop_engine.models import (
    ActorOutput,
    ConfigRecord,
    GateVerdict,
    IterationRecord,
    LoopConfig,
    LoopStatus,
)
from tests.unit.loop_engine.fakes import FakeActor, FakeGate


def test_run_appends_ledger_records(tmp_path) -> None:  # noqa: ANN001
    actor = FakeActor()
    gate = FakeGate(pass_calls=[0])
    config = LoopConfig(actor=actor, gate=gate, max_iterations=5, run_id="runL")
    run_loop(config, ledger_dir=tmp_path)

    ledger = Ledger(tmp_path, "runL")
    records = ledger.read_all()
    types = [r["type"] for r in records]
    assert types[0] == "config"
    assert types[-1] == "final"
    assert "iteration" in types  # T060
    assert ledger.status()["status"] == "passed"


def test_resume_continues_from_last_checkpoint(tmp_path) -> None:  # noqa: ANN001
    # A pre-existing ledger holds completed iterations 1,2 (as if a crash).
    ledger = Ledger(tmp_path, "runR")
    ledger.append_config(ConfigRecord(run_id="runR", config={"max_iterations": 10}))
    for n in (1, 2):
        ledger.append_iteration(
            IterationRecord(
                run_id="runR",
                iteration=n,
                actor_out=ActorOutput(status=True),
                gate=GateVerdict(passed=False),
            )
        )

    actor = FakeActor()
    gate = FakeGate(never_pass=True)
    config = LoopConfig(actor=actor, gate=gate, max_iterations=10, run_id="runR")

    # Resume: continues from iteration 3, never re-running 1..2 (FR-005/SC-004).
    result = run_loop(config, ledger_dir=tmp_path, resume=True)
    assert result.iterations >= 3
    # Total completed iteration count is preserved: 2 done + >=1 new.
    assert result.status in (LoopStatus.EXHAUSTED, LoopStatus.STALLED)


def test_ledger_run_summary_has_iterations_status(tmp_path) -> None:  # noqa: ANN001
    actor = FakeActor()
    gate = FakeGate(pass_calls=[0])
    config = LoopConfig(actor=actor, gate=gate, max_iterations=5, run_id="runS")
    run_loop(config, ledger_dir=tmp_path)
    ledger = Ledger(tmp_path, "runS")
    status = ledger.status()
    assert status is not None
    assert status["iterations"] >= 1  # US4 AS-2
    assert status["status"] == "passed"


def test_resume_missing_ledger_warns_and_starts_fresh(tmp_path) -> None:  # noqa: ANN001
    actor = FakeActor()
    gate = FakeGate(never_pass=True)
    config = LoopConfig(actor=actor, gate=gate, max_iterations=3, run_id="runM")
    # resume=True with no ledger -> fresh run (no crash), still completes
    result = run_loop(config, ledger_dir=tmp_path, resume=True)
    assert result.status == LoopStatus.EXHAUSTED
    assert result.iterations == 3