"""Unit tests for the ``loop_engine`` ledger/spine (T022-T025, FR-005)."""

from __future__ import annotations

import pytest

from ai_factory.loop_engine.ledger import Ledger, LedgerMissingError, resume_cursor
from ai_factory.loop_engine.models import (
    ActorOutput,
    ConfigRecord,
    FinalRecord,
    GateVerdict,
    IterationRecord,
    LoopStatus,
)


def test_append_and_read_back_in_order(tmp_path) -> None:  # noqa: ANN001
    ledger = Ledger(tmp_path, "run-x")
    ledger.append_config(ConfigRecord(run_id="run-x", config={"max_iterations": 5}))
    for n in (1, 2):
        ledger.append_iteration(
            IterationRecord(
                run_id="run-x",
                iteration=n,
                actor_out=ActorOutput(status=True),
                gate=GateVerdict(passed=True),
            )
        )
    ledger.append_final(
        FinalRecord(
            run_id="run-x", status=LoopStatus.PASSED, iterations=2
        )
    )

    records = ledger.read_all()
    assert [r["type"] for r in records] == ["config", "iteration", "iteration", "final"]
    assert records[1]["iteration"] == 1 and records[2]["iteration"] == 2


def test_atomic_append_no_partial_lines(tmp_path) -> None:  # noqa: ANN001
    ledger = Ledger(tmp_path, "run-y")
    ledger.append_iteration(
        IterationRecord(run_id="run-y", iteration=1, actor_out=ActorOutput(status=True))
    )
    # No .tmp leaked after append; file ends with a newline (complete JSON line).
    assert not (tmp_path / "run-y.ledger.jsonl.tmp").exists()
    text = (tmp_path / "run-y.ledger.jsonl").read_text(encoding="utf-8")
    assert text.rstrip("\n").endswith("}")


def test_last_iteration_returns_highest(tmp_path) -> None:  # noqa: ANN001
    ledger = Ledger(tmp_path, "run-z")
    ledger.append_config(ConfigRecord(run_id="run-z"))
    for n in (1, 2, 3):
        ledger.append_iteration(
            IterationRecord(run_id="run-z", iteration=n, actor_out=ActorOutput())
        )
    last, n = ledger.last_iteration()
    assert n == 3 and last is not None and last["iteration"] == 3


def test_resume_cursor_continues_from_k_plus_1(tmp_path) -> None:  # noqa: ANN001
    # write k=2 completed iterations -> resume at iteration 3 (FR-005, SC-004)
    ledger = Ledger(tmp_path, "run-r")
    ledger.append_config(ConfigRecord(run_id="run-r"))
    for n in (1, 2):
        ledger.append_iteration(
            IterationRecord(run_id="run-r", iteration=n, actor_out=ActorOutput())
        )
    assert resume_cursor(tmp_path, "run-r") == 3


def test_resume_cursor_missing_ledger_raises(tmp_path) -> None:  # noqa: ANN001
    with pytest.raises(LedgerMissingError):
        resume_cursor(tmp_path, "absent")


def test_corrupt_ledger_line_skipped_not_silent(tmp_path) -> None:  # noqa: ANN001
    ledger = Ledger(tmp_path, "run-c")
    ledger.append_config(ConfigRecord(run_id="run-c"))
    # inject a corrupt line
    with ledger.path.open("a", encoding="utf-8") as fh:
        fh.write("{not valid json}\n")
    records = ledger.read_all()
    assert len(records) == 1  # the corrupt line skipped; documented, not lossy
    # resume over corrupt tail still yields the last valid completed iteration
    assert resume_cursor(tmp_path, "run-c") == 1


def test_run_id_mismatch_uses_separate_ledger(tmp_path) -> None:  # noqa: ANN001
    # run_id scoping: separate run -> separate ledger file (FR-005); a resume
    # with a DIFFERENT run_id never overwrites another run's ledger.
    a = Ledger(tmp_path, "run-a")
    a.append_config(ConfigRecord(run_id="run-a"))
    a.append_iteration(IterationRecord(run_id="run-a", iteration=1))
    b = Ledger(tmp_path, "run-b")
    assert b.exists() is False
    assert resume_cursor(tmp_path, "run-a") == 2
    with pytest.raises(LedgerMissingError):
        resume_cursor(tmp_path, "run-b")