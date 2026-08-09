"""Phase-boundary checkpointer (T068, FR-020).

Records a checkpoint at every role/phase boundary so a Dev run can resume
from an interrupted point without redoing completed phases. Snapshots are
persisted per ``run_id`` + ``phase`` and reloadable on resume.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class CheckpointStore:
    """A local, per-run phase checkpoint store (FR-020)."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _phase_path(self, run_id: str) -> Path:
        return self.root / f"{run_id}.jsonl"

    def save(self, run_id: str, phase: str, snapshot: dict[str, Any]) -> None:
        """Record that ``phase`` completed for ``run_id`` with a snapshot."""
        self.root.mkdir(parents=True, exist_ok=True)
        record = {
            "phase": phase,
            "snapshot": snapshot,
            "completed_at": _utc_now_iso(),
        }
        path = self._phase_path(run_id)
        # Replace the phase record (idempotent resume) rather than append.
        records = self._read(run_id)
        records = [r for r in records if r["phase"] != phase]
        records.append(record)
        path.write_text(
            "\n".join(json.dumps(r, default=str) for r in records),
            encoding="utf-8",
        )

    def completed(self, run_id: str) -> list[str]:
        """Phases already completed for ``run_id`` (in completion order)."""
        return [r["phase"] for r in self._read(run_id)]

    def is_completed(self, run_id: str, phase: str) -> bool:
        return phase in self.completed(run_id)

    def load(self, run_id: str, phase: str) -> dict[str, Any] | None:
        for record in self._read(run_id):
            if record["phase"] == phase:
                return record["snapshot"]
        return None

    def completed_at(self, run_id: str, phase: str) -> str | None:
        """ISO timestamp when ``phase`` completed, or ``None`` (FR-020)."""
        for record in self._read(run_id):
            if record["phase"] == phase:
                return record.get("completed_at")
        return None

    def _read(self, run_id: str) -> list[dict[str, Any]]:
        path = self._phase_path(run_id)
        if not path.exists():
            return []
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out


__all__ = ["CheckpointStore"]
