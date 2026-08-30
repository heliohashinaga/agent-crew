"""``ai-factory-loop`` command-line interface (loop_engine, US5, FR-007).

Composes the shared ``cli_util`` helpers (JSON on stdout, diagnostics on
stderr) with injectable actor/gate seams so the loop runs deterministically
and network-free for ``--actor factory`` + ``--gate composite`` (reviewer
paths are integration-gated).
"""

from __future__ import annotations

import argparse

from ai_factory.loop_engine.engine import LoopConfigError, run_loop
from ai_factory.loop_engine.factory_actor import FactoryActor
from ai_factory.loop_engine.gate import LoopGateError
from ai_factory.loop_engine.models import (
    LoopBudget,
    LoopConfig,
    LoopStatus,
    RatchetConfig,
)
from ai_factory.shared.cli_util import (
    CliError,
    add_output_format_arg,
    emit,
    run,
    write_stderr,
    write_stdout,
)

# Meaningful exit codes for this CLI (contracts/loop-cli.md, FR-007).
EXIT_OK = 0
EXIT_PASSED = 0
EXIT_EXHAUSTED = 2
EXIT_RESOLUTION = 3
EXIT_ERROR_CODE = 4
EXIT_USAGE = 1


def build_parser() -> argparse.ArgumentParser:
    """Build the ``ai-factory-loop`` argument parser."""
    parser = argparse.ArgumentParser(prog="ai-factory-loop")
    parser.add_argument("--actor", choices=["factory"], default="factory")
    parser.add_argument("--gate", choices=["composite"], default="composite")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--ledger-dir", default="")
    parser.add_argument("--max-iterations", type=int, default=None)
    parser.add_argument("--budget-tokens", type=int, default=None)
    parser.add_argument("--budget-seconds", type=float, default=None)
    parser.add_argument("--budget-cost", type=float, default=None)
    parser.add_argument("--ratchet-max-stall", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--telemetry", action="store_true")
    parser.add_argument("--folder", default="spec_folder")
    add_output_format_arg(parser)
    return parser


def _verify_no_secrets(_value: object) -> None:
    # Seam: gate/actor credentials are never surfaced; redaction is applied by
    # cli_util.emit before any output (FR-008/FR-018).
    pass


def build_gate(args: argparse.Namespace):
    """Build the composite gate (Q2=C). Deterministic checks are injected here."""
    from ai_factory.loop_engine.gate import CompositeGate, artifact_exists

    # Pluggable deterministic check set (Q4=B): default artifact_exists.
    return CompositeGate(deterministic=[artifact_exists])


def build_loop_config(args: argparse.Namespace) -> LoopConfig:
    if not args.run_id or not args.run_id.strip():
        raise CliError("--run-id is required and non-empty.", exit_code=EXIT_USAGE)
    if args.max_iterations is None or args.max_iterations <= 0:
        raise CliError(
            "--max-iterations is required and must be > 0",
            exit_code=EXIT_RESOLUTION,
        )
    budget = None
    if any((args.budget_tokens, args.budget_seconds, args.budget_cost)):
        budget = LoopBudget(
            max_tokens=args.budget_tokens,
            max_seconds=args.budget_seconds,
            max_cost_usd=args.budget_cost,
        )
    ratchet = (
        RatchetConfig(max_stall=args.ratchet_max_stall)
        if args.ratchet_max_stall
        else None
    )
    # Injectable seam: composite gate (network-free deterministic core).
    gate = build_gate(args)
    actor = FactoryActor(folder=args.folder)
    return LoopConfig(
        actor=actor,
        gate=gate,
        max_iterations=args.max_iterations,
        budget=budget,
        ratchet=ratchet,
        run_id=args.run_id,
    )


def cmd(args: argparse.Namespace) -> int:
    """Run one loop and print its ``LoopResult`` (FR-007)."""
    config = build_loop_config(args)
    try:
        result = run_loop(
            config,
            ledger_dir=args.ledger_dir or None,
            resume=args.resume,
            telemetry=args.telemetry,
        )
    except (LoopConfigError, LoopGateError) as exc:
        raise CliError(str(exc), exit_code=EXIT_ERROR_CODE) from exc

    payload = result.model_dump(mode="json")
    write_stdout(emit(payload, args.format))

    # Meaningful exit codes (FR-007, contracts/loop-cli.md).
    if result.status in (LoopStatus.PASSED,):
        return EXIT_PASSED
    if result.status in (LoopStatus.EXHAUSTED, LoopStatus.STALLED):
        return EXIT_EXHAUSTED
    return EXIT_ERROR_CODE


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: parse args, run one loop, return exit code."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # argparse exits on bad flag values (e.g. non-int); map to usage error.
        return EXIT_USAGE
    try:
        return cmd(args)
    except CliError as exc:
        write_stderr(f"error: {exc}\n")
        return exc.exit_code


if __name__ == "__main__":  # pragma: no cover
    import sys

    sys.exit(run(main))