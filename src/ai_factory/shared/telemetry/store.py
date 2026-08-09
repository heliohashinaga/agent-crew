"""Local telemetry store (T031, FR-016/018, SC-003).

Records are persisted per ``run_id`` as line-delimited JSON and queried
locally (well under a second, SC-003). Every record is sanitized/redacted
at the store boundary (FR-018, SC-010) so no secret is ever written to disk.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_factory.shared.telemetry.emitter import TelemetryCapable, sanitize
from ai_factory.shared.telemetry.record import DevRoleInvocation, TelemetryRecord

DEFAULT_TELEMETRY = ".factory/telemetry"


def record_dev_invocation(
    role: str,
    run_id: str,
    store_path: str | Path = DEFAULT_TELEMETRY,
    *,
    result: str = "pass",
    capability_level: str = "standard",
    model: str = "",
    overspend: bool | None = None,
) -> None:
    """Record one dev-role invocation into the telemetry store (T071, FR-016)."""
    FileTelemetryStore(store_path).add(
        run_id,
        DevRoleInvocation(
            role=role,  # type: ignore[arg-type]
            model=model,
            capability_level=capability_level,
            telemetry=TelemetryRecord(result=result, overspend=overspend),
        ),
    )


class FileTelemetryStore:
    """A per-run, line-delimited JSON telemetry store on the local filesystem."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _run_path(self, run_id: str) -> Path:
        # run_id is opaque or user-provided; sanitize to a safe filename.
        safe = "".join(c for c in run_id if c.isalnum() or c in "._-") or "run"
        return self.root / f"{safe}.jsonl"

    def add(self, run_id: str, record: TelemetryCapable) -> None:
        """Persist a redacted ``record`` under ``run_id``."""
        self.root.mkdir(parents=True, exist_ok=True)
        safe = sanitize(record)
        with self._run_path(run_id).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(safe, default=str) + "\n")

    def get(self, run_id: str) -> list[dict[str, Any]]:
        """Return redacted records for ``run_id``, deduplicated by (role, attempt)."""
        raw = self._read_raw(run_id)
        latest: dict[tuple[str, int], dict[str, Any]] = {}
        for rec in raw:
            key = (str(rec.get("role", "")), int(rec.get("attempt", 1)))
            latest[key] = rec  # last write wins
        return list(latest.values())

    def get_latest(self, run_id: str) -> dict[str, Any] | None:
        """Return the most recently written record for ``run_id``, or ``None``."""
        raw = self._read_raw(run_id)
        return raw[-1] if raw else None

    def list_runs(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(p.stem for p in self.root.glob("*.jsonl"))

    def _read_raw(self, run_id: str) -> list[dict[str, Any]]:
        path = self._run_path(run_id)
        if not path.exists():
            return []
        out: list[dict[str, Any]] = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out


__all__ = ["FileTelemetryStore"]
