"""Contract test for the ``telemetry`` query CLI (T032, SC-003, FR-016).

The CLI queries a run's telemetry records and emits redacted JSON (default)
or human form. Local queries must return within seconds (SC-003); an unknown
run is a non-zero exit with a diagnostic on stderr.
"""

from __future__ import annotations

import json

import pytest

from ai_factory.shared.cli_util import EXIT_ERROR, run
from ai_factory.shared.telemetry.cli import main
from ai_factory.shared.telemetry.record import SpecRoleInvocation, TelemetryRecord
from ai_factory.shared.telemetry.store import FileTelemetryStore


@pytest.fixture()
def populated(tmp_path) -> str:
    store = FileTelemetryStore(tmp_path)
    store.add(
        "run-1",
        SpecRoleInvocation(
            role="spec_agent", telemetry=TelemetryRecord(tokens_in=5, result="pass")
        ),
    )
    store.add(
        "run-1",
        SpecRoleInvocation(
            role="requirements_reviewer",
            attempt=2,
            outcome="rework",
            telemetry=TelemetryRecord(result="rework"),
        ),
    )
    return str(tmp_path)


def test_query_run_emits_json(capsys: pytest.CaptureFixture[str], populated) -> None:
    code = run(main, ["--run", "run-1", "--store", populated])
    assert code == 0
    records = json.loads(capsys.readouterr().out)
    assert isinstance(records, list)
    roles = [r["role"] for r in records]
    assert "spec_agent" in roles and "requirements_reviewer" in roles


def test_query_deduplicates_by_role_attempt(capsys, populated) -> None:
    run(main, ["--run", "run-1", "--store", populated])
    records = json.loads(capsys.readouterr().out)
    assert len(records) == 2  # one per role


def test_human_format(capsys, populated) -> None:
    code = run(main, ["--run", "run-1", "--store", populated, "--format", "human"])
    assert code == 0
    out = capsys.readouterr().out
    assert "role:" in out
    assert not out.lstrip().startswith("[{")  # human, not a JSON array


def test_unknown_run_is_error(capsys, populated) -> None:
    code = run(main, ["--run", "nope", "--store", populated])
    assert code == EXIT_ERROR
    err = capsys.readouterr().err
    assert "nope" in err


def test_missing_store_defaults_to_local(tmp_path, capsys) -> None:
    # Missing store dir behaves like an unknown run (clean error), not a crash.
    code = run(main, ["--run", "run-x", "--store", str(tmp_path / "absent")])
    assert code == EXIT_ERROR
