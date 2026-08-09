"""Contract test for the shared library-CLI convention harness (T014).

Per `contracts/library-cli-convention.md`: every role/capability CLI emits
machine-readable JSON by default, a human form via ``--format human``,
diagnostics to stderr, meaningful exit codes, and MUST redact secrets before
emission (FR-018). This exercises the shared helpers in
:mod:`ai_factory.shared.cli_util` via a small sample CLI that uses them.
"""

from __future__ import annotations

import argparse
import json

from ai_factory.shared.cli_util import (
    EXIT_CLARIFICATION,
    EXIT_OK,
    CliError,
    add_output_format_arg,
    emit,
    run,
    write_stdout,
)


def _sample_cli(argv: list[str] | None = None) -> int:
    """A minimal library CLI that composes the shared helpers."""
    parser = argparse.ArgumentParser()
    add_output_format_arg(parser)
    parser.add_argument("--token", default=None)
    args = parser.parse_args(argv)

    out = {"role": "sample", "ok": True, "secret": "supersecretvalue"}
    write_stdout(emit(out, args.format, secrets=["supersecretvalue"]))
    return 0


def test_default_output_is_json() -> None:
    assert _sample_cli([]) == 0
    # JSON contract satisfied by emit() returning parseable JSON by default.
    text = emit({"role": "sample"})
    assert json.loads(text)["role"] == "sample"


def test_emit_redacts_secrets_before_emission() -> None:
    text = emit({"secret": "supersecretvalue"}, secrets=["supersecretvalue"])
    assert "supersecretvalue" not in text
    assert "[REDACTED]" in text


def test_human_format_is_not_json() -> None:
    text = emit({"role": "sample", "n": 3}, fmt="human")
    assert text
    assert not text.lstrip().startswith("{")
    assert "role" in text


def test_add_output_format_arg_defaults_to_json() -> None:
    parser = argparse.ArgumentParser()
    add_output_format_arg(parser)
    args = parser.parse_args([])
    assert args.format == "json"


def test_add_output_format_arg_accepts_human() -> None:
    parser = argparse.ArgumentParser()
    add_output_format_arg(parser)
    assert parser.parse_args(["--format", "human"]).format == "human"


def test_run_returns_success_code() -> None:
    assert run(_sample_cli, []) == 0
    assert run(_sample_cli, []) == EXIT_OK


def test_run_propagates_meaningful_exit_codes() -> None:
    def main(argv: list[str] | None = None) -> int:  # noqa: ARG001
        raise CliError("need more info", exit_code=EXIT_CLARIFICATION)

    assert run(main, []) == EXIT_CLARIFICATION  # 3


def test_run_catches_cli_error_and_returns_code() -> None:
    def main(argv: list[str] | None = None) -> int:  # noqa: ARG001
        raise CliError("boom", exit_code=2)

    assert run(main, []) == 2


def test_exit_code_constants_exist() -> None:
    from ai_factory.shared import cli_util as mod

    assert mod.EXIT_OK == 0
    assert mod.EXIT_REJECTED == 2
    assert mod.EXIT_CLARIFICATION == 3
