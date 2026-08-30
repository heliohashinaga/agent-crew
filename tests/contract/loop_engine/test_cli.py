"""Contract tests for the ``ai-factory-loop`` CLI (US5, T070-T073, FR-007)."""

from __future__ import annotations

import json

from ai_factory.loop_engine.cli import (
    EXIT_EXHAUSTED,
    EXIT_OK,
    EXIT_RESOLUTION,
    main,
)
from ai_factory.loop_engine.models import LoopResult
from ai_factory.shared.cli_util import run


def _run_cli(argv: list[str]) -> int:
    return run(main, argv)


def test_missing_run_id_usage_error(capsys, monkeypatch) -> None:  # noqa: ANN001
    # A synthetic config path surfaces --run-id validation as a usage error.
    # Simulate by omitting --run-id while providing the rest.
    code = _run_cli(
        ["--actor", "factory", "--gate", "composite", "--max-iterations", "3"]
    )
    err = capsys.readouterr().err
    assert code != 0
    assert "run-id" in err


def test_max_iterations_abc_usage_error(capsys, monkeypatch) -> None:  # noqa: ANN001
    code = _run_cli(["--run-id", "r", "--max-iterations", "abc"])
    out = capsys.readouterr().out
    # abc fails int parsing -> argparse error, no payload on stdout
    assert code != 0
    assert out == ""


def test_loop_passed_exit_0_json_stdout(capsys) -> None:  # noqa: ANN001
    code = _run_cli(
        [
            "--actor",
            "factory",
            "--gate",
            "composite",
            "--run-id",
            "cli-pass",
            "--max-iterations",
            "3",
        ]
    )
    captured = capsys.readouterr()
    assert code == EXIT_OK  # US5 AS-1
    result = LoopResult.model_validate_json(captured.out)
    assert result.status.value == "passed"
    assert json.loads(captured.out)["status"] == "passed"


def test_loop_exhausted_exit_2(capsys, monkeypatch) -> None:  # noqa: ANN001
    # Inject a never-passing gate so the loop exhausts its max_iterations.
    import ai_factory.loop_engine.cli as cli_mod
    from tests.unit.loop_engine.fakes import FakeGate

    monkeypatch.setattr(
        cli_mod, "build_gate", lambda *a, **k: FakeGate(never_pass=True)
    )
    code = _run_cli(
        [
            "--actor",
            "factory",
            "--gate",
            "composite",
            "--run-id",
            "cli-exh",
            "--max-iterations",
            "3",
        ]
    )
    captured = capsys.readouterr()
    assert code == EXIT_EXHAUSTED  # US5 AS-2
    result = LoopResult.model_validate_json(captured.out)
    assert result.status.value in ("exhausted", "stalled")
    assert result.escalation is not None


def test_human_output(capsys) -> None:  # noqa: ANN001
    code = _run_cli(
        [
            "--actor",
            "factory",
            "--gate",
            "composite",
            "--run-id",
            "cli-human",
            "--max-iterations",
            "3",
            "--format",
            "human",
        ]
    )
    captured = capsys.readouterr()
    assert code == EXIT_OK
    assert "status:" in captured.out
    assert not captured.out.lstrip().startswith("{")  # not JSON


def test_resolution_error_exit_3(capsys) -> None:  # noqa: ANN001
    code = _run_cli(
        [
            "--actor",
            "factory",
            "--gate",
            "composite",
            "--run-id",
            "cli-bad",
            "--max-iterations",
            "0",
        ]
    )
    assert code == EXIT_RESOLUTION  # US5 AS-3 resolution/config error