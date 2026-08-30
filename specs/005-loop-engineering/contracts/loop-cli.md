# Contract: `ai-factory-loop` CLI (Loop Engineering)

The `loop_engine` is a **Library-First** control-loop capability in the
ai-factory. Its CLI lets a caller (human or script) start or resume an
autonomous loop over an **actor** / **gate** and receive a **`LoopResult`**
— deterministic core, network-free. Review/LLM acts are behind injectable
seams and integration-gated.

This contract defines the public interface for the `ai-factory-loop`
console script.

## Interface

```text
ai-factory-loop --actor <binding> --gate <binding> --run-id <id>
               --ledger-dir <path> --max-iterations <N>
              [--budget-tokens <N>] [--budget-seconds <sec>] [--budget-cost <usd>]
              [--ratchet-max-stall <N>]
              [--output-format <json|human>] [--telemetry <bool>]
              [--resume] [--help]
```

- **`--actor <binding>`** (required): which concrete actor to use. v1 ships one:
  `factory` (the folder-driven dev-pipeline seam, Q1=A). Future bindings
  (media/video, arbitrary tasks) plug without changing the core.
- **`--gate <binding>`** (required): which gate to use. v1 ships `composite`
  (deterministic checks first, then independent reviewer, Q2=C). Reviewer is
  integration-gated.
- **`--run-id <id>`** (required): deterministic run scoping; resume requires the
  same `run_id`.
- **`--ledger-dir <path>`** (required): durable spine target (JSON-lines journal).
- **`--max-iterations <N>`** (required, `> 0`): hard termination bound (FR-003).
- **`--budget-tokens / --budget-seconds / --budget-cost`** (optional): termination
  budget dimensions (FR-003). Within `loop_engine`, exceeding a configured
  budget dimension is a **hard stop → `exhausted`** (Q7=A): an intentional,
  scoped divergence from the parent factory's soft-budget convention.
- **`--ratchet-max-stall <N>`** (optional): stall/progress ratchet (FR-003).
- **`--output-format <json|human>`** (default `json`): stdout shape.
- **`--resume`**: continue a paused/interrupted run from its ledger (FR-005).

## Exit codes

| code | meaning |
|------|---------|
| `0`  | success — `LoopResult.status == "passed"` |
| `2`  | exhausted/stalled/escalated — loop terminated without passing (distinct non-zero) |
| `3`  | resolution/configuration error — invalid config, missing actor/gate, `--max-iterations <= 0` |
| `4`  | `error` — an unavailable gate/actor surfaced a typed error to the CLI (US2 AS-3, F2), distinct from usage/resolution |
| `1`  | usage error — missing/invalid arguments, empty task/work input |

Per FR-007: `0` = passed; distinct non-zero codes for exhausted/escalation
(`2`), error (`4`), resolution/config (`3`), usage (`1`).

## stdout / stderr

- **stdout**: the `LoopResult` payload. For `--output-format json`, valid JSON
  serializable via `LoopResult.model_validate_json(...)`; for `human`, a readable
  brief (status, iterations, gate verdicts, budget, artifact pointers). stdout
  is never the diagnostic output.
- **stderr**: diagnostics, telemetry/summary notes, warnings. Never the payload.

## Json payload (LoopResult)

```json
{
  "run_id": "<id>",
  "status": "passed",
  "iterations": 3,
  "gates": [ { "passed": true, "checks": [ {"name":"suite_pass","stage":"deterministic","passed":true} ] } ],
  "budget": { "tokens": 120, "cost_usd": 0.001, "latency_s": 0.4 },
  "artifact_refs": ["specs/<feat>/..."],
  "escalation": null
}
```

- `status` ∈ `passed | exhausted | stalled | error`.
- `escalation` present (not `null`) whenever `status != "passed"` (FR-004).

## Telemetry

Every iteration emits a `TelemetryRecord` with `role == "loop_engine"` —
tokens/cost/latency/retries/errors/escalations/result — via the shared
telemetry seam; secret-like values are redacted before emission (FR-008).

## Notes

This contract supersedes any implied single-run CLI and codifies the
autonomous, terminating, resumable loop. It does **not** add multi-loop
composition, scheduled/event triggers, or interactive approval checkpoints
(out of v1 scope).