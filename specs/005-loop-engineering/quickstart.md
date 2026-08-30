# Quickstart — Loop Engineering Validation Guide

This guide proves the `loop_engine` feature works end-to-end. It is a
**validation/run guide** (design details live in `data-model.md`, `contracts/`,
`tasks.md`). No full implementation code here.

**Feature**: `005-loop-engineering`
**Prereqs**: `uv` (Python ≥ 3.14, `src`-layout `ai_factory`).

## 1. Setup & Green baseline

```bash
uv run ruff check .          # clean
uv run pytest -q             # unit + contract, no network
uv run pytest -m integration # reviewer-gate + real factory-actor (network/LLM, skips cleanly offline)
```

## 2. Deterministic core (no network) — FakeActor + FakeGate

All US1–US3 verification runs through unit/contract tests under
`tests/unit/loop_engine/` and `tests/contract/loop_engine/`:

- **US1 / FR-001**: `run_loop` returns `LoopResult` with correct iteration
  counts — gate passes on 1st call → `passed` in 1 iteration; gate fails k then
  passes → exactly k+1 iterations with repair context propagated; never-passing
  gate + `max_iterations=N` → `≤ N` iterations, `exhausted` (SC-001/SC-002).
- **US2 / FR-002**: no-self-grading — `FakeActor` claims success while
  `FakeGate` fails → `exhausted`, held-back reason is the **gate's** (SC-003).
  Gate-unavailable → typed error, never silent pass.
- **US3 / FR-003/004**: budget/ratchet termination — budget is a **hard stop**
  within `loop_engine` (Q7=A, scoped divergence from the factory's soft-budget);
  exhaustion → `exhausted`; ratchet no-progress → distinct `stalled` (Q5=A);
  both yield a concise escalation summary (status, iterations, bounded verdicts,
  budget, refs). Actor-exceptions (Q6=A) retry bounded by budget without
  consuming a `max_iterations` slot.
- **US4 / FR-005**: pause/resume on `tmp_path` — interrupt after k iterations,
  resume to `k+1`, total preserved (SC-004).

## 3. CLI — `ai-factory-loop`

```bash
# A loop that passes (exit 0, JSON on stdout, diagnostics on stderr)
uv run ai-factory-loop --actor factory --gate composite \
  --run-id demo-1 --ledger-dir /tmp/loop-ledger \
  --max-iterations 3 --output-format json
```

- Valid JSON on **stdout** parses via `LoopResult.model_validate_json(...)`,
  `status` shown, diagnostics on **stderr**, exit `0`.
- `--output-format human` → readable brief (status, iterations, verdicts,
  budget, artifact pointers).
- **Exhausted/escalation** → exits non-zero `2` (distinct from hard errors),
  `escalation` present in payload.
- **Usage/resolution errors** → exit `1` (missing args, empty input) / `3`
  (invalid config, `--max-iterations <= 0`, missing actor/gate); an unavailable
  gate/actor surfacing `status == "error"` → exit `4`.

See [`contracts/loop-cli.md`](./contracts/loop-cli.md) for the full
interface and exit-code table.

## 4. Resume

```bash
# Start, interrupt after k iterations (Ctrl-C / crash), then:
uv run ai-factory-loop --actor factory --gate composite \
  --run-id demo-1 --ledger-dir /tmp/loop-ledger \
  --max-iterations 5 --resume --output-format json
```

The loop continues from the **last completed checkpoint** — never re-running
completed iterations (FR-005, SC-004). See
[`contracts/ledger-format.md`](./contracts/ledger-format.md).

## 5. Telemetry

Each iteration emits a `TelemetryRecord` with `role == "loop_engine"` —
tokens/cost/latency/retries/errors/escalations/result — via the shared
telemetry seam; secret-like values are redacted (FR-008).

## Expected outcomes

| Run | Exit | Payload |
|-----|------|---------|
| gate passes | `0` | `status: passed` |
| never passes, budget/iter exhausted | `2` | `status: exhausted` (hard-stop on budget, Q7) or `stalled` (ratchet, Q5); `escalation` present |
| unavailable gate/actor | `4` | `status: error`, typed error surfaced |
| config invalid (no actor, `max_iterations<=0`) | `3` | error, no run |
| usage error (missing args, empty input) | `1` | usage message |
| reviewer gate offline (integration) | clear typed skip/error | never silent pass |

## References

- Data model: [`data-model.md`](./data-model.md)
- CLI contract: [`contracts/loop-cli.md`](./contracts/loop-cli.md)
- Seam contract: [`contracts/actor-gate-seam.md`](./contracts/actor-gate-seam.md)
- Ledger contract: [`contracts/ledger-format.md`](./contracts/ledger-format.md)