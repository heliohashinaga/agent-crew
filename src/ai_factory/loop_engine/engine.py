"""Core control loop for ``loop_engine`` (FR-001, US1).

``run_loop`` executes an **actor → gate → repair → repeat** loop until the
external gate passes or termination conditions are met, persisting a durable
ledger/spine so a run can be paused/resumed. The deterministic core is
**network-free**; review/LLM work sits behind injectable seams.

Invariants:
- FR-002/US2: success derives exclusively from the external ``Gate`` — the
  actor's ``status`` claim is never the loop's verdict (no self-grading).
- FR-003/US3: termination guaranteed (``max_iterations``, budget, ratchet).
- Q5=A: ``stalled`` is a distinct status; Q6=A: actor-exceptions are
  budget-bounded retries, separate from ``max_iterations``; Q7=A: budget is a
  hard stop within ``loop_engine``.
- FR-005/US4: durable ledger + resume from last completed checkpoint.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_factory.loop_engine.actor import Actor, Gate
from ai_factory.loop_engine.budget import BudgetTracker, StallRatchet
from ai_factory.loop_engine.escalation import build_escalation
from ai_factory.loop_engine.gate import LoopGateError
from ai_factory.loop_engine.ledger import Ledger, LedgerMissingError
from ai_factory.loop_engine.models import (
    ActorOutput,
    BudgetDelta,
    ConfigRecord,
    FinalRecord,
    GateVerdict,
    IterationRecord,
    LoopConfig,
    LoopResult,
    LoopStatus,
    RepairContext,
)
from ai_factory.shared.telemetry.store import record_dev_invocation


class LoopActorError(RuntimeError):
    """Raised on a hard (fail-fast) actor failure (Q6 edge, T053)."""


class LoopConfigError(ValueError):
    """Raised when ``LoopConfig`` is invalid (FR-009)."""


class LoopRunOptions:
    """Runtime options for ``run_loop`` (kept out of the serialised model)."""

    def __init__(
        self,
        *,
        ledger_dir: str | Path | None = None,
        resume: bool = False,
        telemetry: bool = False,
        telemetry_dir: str | Path | None = None,
    ) -> None:
        self.ledger_dir = Path(ledger_dir) if ledger_dir else None
        self.resume = resume
        self.telemetry = telemetry
        self.telemetry_dir = Path(telemetry_dir) if telemetry_dir else None


def _prepare(
    config: LoopConfig, opts: LoopRunOptions
) -> tuple[Ledger | None, int, int]:
    """Validate config + resolve the starting iteration (fresh or resume).

    Returns ``(ledger, start_iteration, budget_start_key)``.
    """
    try:
        config.validate_config()
    except ValueError as exc:
        raise LoopConfigError(str(exc)) from exc

    ledger: Ledger | None = None
    start = 1
    if opts.ledger_dir is not None:
        ledger = Ledger(opts.ledger_dir, config.run_id)
        if opts.resume:
            if not ledger.exists():
                # FR-005: absent ledger on resume -> fresh run + warning.
                try:
                    from ai_factory.shared.cli_util import write_stderr
                except Exception:  # noqa: BLE001
                    write_stderr = print
                write_stderr(
                    f"warning: no ledger for {config.run_id!r}; starting fresh\n"
                )
                start = 1
            else:
                try:
                    from ai_factory.loop_engine.ledger import resume_cursor

                    start = resume_cursor(opts.ledger_dir or ".", config.run_id)
                except LedgerMissingError:
                    start = 1
        else:
            cfg_snapshot = config.model_dump(
                mode="json", exclude={"actor", "gate", "ledger_dir"}
            )
            ledger.append_config(
                ConfigRecord(run_id=config.run_id, config=cfg_snapshot)
            )
    return ledger, start


def run_loop(
    config: LoopConfig,
    *,
    ledger_dir: str | Path | None = None,
    resume: bool = False,
    telemetry: bool = False,
    telemetry_dir: str | Path | None = None,
    on_iteration: Any = None,
) -> LoopResult:
    """Run the autonomous control loop (FR-001) until pass or termination."""
    opts = LoopRunOptions(
        ledger_dir=ledger_dir,
        resume=resume,
        telemetry=telemetry,
        telemetry_dir=telemetry_dir,
    )
    ledger, start = _prepare(config, opts)

    actor: Actor = config.actor  # type: ignore[assignment]
    gate: Gate = config.gate  # type: ignore[assignment]

    tracker = BudgetTracker(config.budget)
    ratchet = StallRatchet(config.ratchet)
    verdicts: list[GateVerdict] = []
    artifact_refs: list[str] = []
    prior_failed = False
    prior_verdict: GateVerdict | None = None
    final_status: LoopStatus = LoopStatus.PASSED
    errors = 0
    escalations = 0
    retries = 0

    iteration = start
    attempts = 0
    while iteration <= config.max_iterations:
        # Q7=A: budget is a hard stop — do not start another iteration if exhausted.
        if tracker.exceeded():
            final_status = LoopStatus.EXHAUSTED
            escalations += 1
            break

        context = RepairContext(
            prior_verdict=prior_verdict,
            prior_failed=prior_failed,
            iteration=iteration,
            message=",".join(prior_verdict.reasons()) if prior_verdict else "",
        )

        # Actor invoke (Q6=A: exceptions are budget-bounded retries, not crashes).
        try:
            actor_out: ActorOutput = actor.invoke(context)
        except Exception as exc:  # noqa: BLE001 - actor may fail arbitrarily
            retries += 1
            errors += 1
            prior_failed = True
            prior_verdict = GateVerdict(passed=False, checks=[])
            if ledger is not None:
                ledger.append_iteration(
                    IterationRecord(
                        run_id=config.run_id,
                        iteration=iteration,
                        actor_out=ActorOutput(status=False),
                        gate=GateVerdict(passed=False),
                        budget_delta=BudgetDelta(tokens=1),
                        repair_context=f"actor error: {exc}",
                    )
                )
            # actor-exception consumes budget (retry cost) but not an iteration slot;
            # advance budget counter, do NOT increment iteration.
            tracker.add(BudgetDelta(tokens=1, cost_usd=0.0))
            if tracker.exceeded():
                final_status = LoopStatus.EXHAUSTED
                escalations += 1
                break
            continue

        ratchet.record(actor_out)
        attempts += 1
        if actor_out.artifact_refs:
            artifact_refs = list(
                dict.fromkeys([*artifact_refs, *actor_out.artifact_refs])
            )

        # Gate verify (FR-002: the external gate decides).
        try:
            verdict: GateVerdict = gate.verify(actor_out)
        except LoopGateError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LoopGateError(f"gate unavailable: {exc}") from exc

        verdicts.append(verdict)
        tracker.add(verdict.consumed)
        prior_failed = not verdict.passed
        prior_verdict = verdict

        if ledger is not None:
            ledger.append_iteration(
                IterationRecord(
                    run_id=config.run_id,
                    iteration=iteration,
                    actor_out=actor_out,
                    gate=verdict,
                    budget_delta=verdict.consumed,
                    repair_context=",".join(verdict.reasons()),
                )
            )

        if telemetry:
            _emit_telemetry(config, opts, iteration, verdict, errors, retries)

        # Stall ratchet (Q5=A): distinct stalled status.
        if ratchet.stalled():
            final_status = LoopStatus.STALLED
            escalations += 1
            break

        # Gate passed -> success (FR-002).
        if verdict.passed:
            final_status = LoopStatus.PASSED
            break

        if tracker.exceeded():
            final_status = LoopStatus.EXHAUSTED
            escalations += 1
            break

        iteration += 1

    if iteration > config.max_iterations and final_status == LoopStatus.PASSED:
        # Ran out of max_iterations without the gate passing (FR-003).
        final_status = LoopStatus.EXHAUSTED
        escalations += 1

    result = LoopResult(
        run_id=config.run_id,
        status=final_status,
        iterations=attempts,
        gates=verdicts,
        budget=tracker.budget_summary(),
        artifact_refs=artifact_refs,
    )

    if final_status != LoopStatus.PASSED:
        result.escalation = build_escalation(
            status=final_status,
            iterations=result.iterations,
            verdicts=verdicts,
            budget=result.budget,
            partial_artifacts=artifact_refs,
        )

    if ledger is not None:
        ledger.append_final(
            FinalRecord(
                run_id=config.run_id,
                status=final_status,
                iterations=result.iterations,
                budget_consumed=result.budget,
                escalation=result.escalation,
            )
        )
        if telemetry:
            _emit_telemetry_final(config, opts, result, errors, retries, escalations)

    return result


def _emit_telemetry(
    config: LoopConfig,
    opts: LoopRunOptions,
    iteration: int,
    verdict: GateVerdict,
    errors: int,
    retries: int,
) -> None:
    _write_telemetry(
        opts,
        config.run_id,
        {
            "iteration": iteration,
            "status": "pass" if verdict.passed else "fail",
            "errors": errors,
            "retries": retries,
        },
    )


def _emit_telemetry_final(
    config: LoopConfig,
    opts: LoopRunOptions,
    result: LoopResult,
    errors: int,
    retries: int,
    escalations: int,
) -> None:
    _write_telemetry(
        opts,
        config.run_id,
        {
            "iteration": result.iterations,
            "status": str(result.status.value),
            "errors": errors,
            "retries": retries,
            "escalations": escalations,
        },
    )


def _write_telemetry(
    opts: LoopRunOptions, run_id: str, fields: dict[str, Any]
) -> None:
    if not opts.telemetry:
        return
    # Per-iteration telemetry record with role == "loop_engine" (FR-008);
    # sanitized/redacted at the store boundary (no secret-looking values).
    record_dev_invocation(
        role="loop_engine",
        run_id=run_id,
        store_path=opts.telemetry_dir or ".factory/telemetry/loop",
        result=str(fields.get("status", "pass")),
        capability_level="standard",
        model="",
    )


__all__ = [
    "LoopActorError",
    "LoopConfigError",
    "LoopRunOptions",
    "run_loop",
]