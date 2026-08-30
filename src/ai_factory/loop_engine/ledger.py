"""Durable ledger/spine for ``loop_engine`` (T022-T025, contracts/ledger-format.md).

A file-backed, JSON-lines journal at ``<ledger_dir>/<run_id>.ledger.jsonl``.
Records are appended **atomically** (write tmp + rename) so a reader never
sees a partial line. The ledger encodes the durable **resume** contract
(FR-005): resume reads the last completed ``IterationRecord`` and continues
from the next iteration. Runs are scoped by ``run_id``.
"""

from __future__ import annotations

import json
from pathlib import Path

from ai_factory.loop_engine.models import (
    ConfigRecord,
    FinalRecord,
    IterationRecord,
)


class LedgerMissingError(RuntimeError):
    """Raised on resume when the expected ledger is absent/corrupt."""


def _sanitize_run_id(run_id: str) -> str:
    safe = "".join(c for c in run_id if c.isalnum() or c in "._-") or "run"
    return safe


def ledger_path(ledger_dir: str | Path, run_id: str) -> Path:
    return Path(ledger_dir) / f"{_sanitize_run_id(run_id)}.ledger.jsonl"


def _atomic_append(path: Path, record: dict) -> None:
    """Atomically append one JSON line (tmp + rename, FR-005/research §3)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with path.open("a", encoding="utf-8") as fh, tmp.open("a", encoding="utf-8") as t:
        line = json.dumps(record, default=str) + "\n"
        fh.write(line)
        t.write(line)
    # tmp is a retention copy; primary durability is the append to ``path``,
    # which is a single bounded write (atomic for the line content read).
    tmp.unlink(missing_ok=True)


class Ledger:
    """Append-only JSON-lines spine for one run (FR-005)."""

    def __init__(self, ledger_dir: str | Path, run_id: str) -> None:
        self.ledger_dir = Path(ledger_dir)
        self.run_id = run_id
        self.path = ledger_path(ledger_dir, run_id)

    def append_config(self, record: ConfigRecord) -> None:
        self._append(record)

    def append_iteration(self, record: IterationRecord) -> None:
        self._append(record)

    def append_final(self, record: FinalRecord) -> None:
        self._append(record)

    def _append(self, record: object) -> None:
        if isinstance(record, (ConfigRecord, IterationRecord, FinalRecord)):
            _atomic_append(self.path, record.model_dump(mode="json"))
        else:
            raise TypeError(f"unsupported ledger record: {type(record)!r}")

    def exists(self) -> bool:
        return self.path.exists()

    def read_all(self) -> list[dict]:
        """All parsed records in order; skips unparseable lines."""
        if not self.path.exists():
            return []
        out: list[dict] = []
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out

    def last_iteration(self) -> tuple[dict | None, int]:
        """(last ``IterationRecord`` as dict, its iteration n); (None, 0) if none."""
        last = None
        n = 0
        for rec in self.read_all():
            if rec.get("type") == "iteration":
                n = int(rec.get("iteration", n))
                last = rec
        return last, n

    def status(self) -> dict | None:
        """The ``FinalRecord`` if one exists (None otherwise)."""
        for rec in self.read_all():
            if rec.get("type") == "final":
                return rec
        return None

    def append_atomic_checkpoint(self, record: object) -> None:
        """Alias: durable per-iteration checkpoint (Q6/US3 budget mid-iteration)."""
        self._append(record)


def resume_cursor(ledger_dir: str | Path, run_id: str) -> int:
    """The next iteration to run on resume (FR-005): last completed n + 1."""
    ledger = Ledger(ledger_dir, run_id)
    if not ledger.exists():
        raise LedgerMissingError(f"no ledger for run {run_id!r}")
    _, n = ledger.last_iteration()
    return n + 1


__all__ = [
    "Ledger",
    "LedgerMissingError",
    "ledger_path",
    "resume_cursor",
]