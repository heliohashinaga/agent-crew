# Contract: Ledger / Spine Format (Loop Engineering)

The ledger (the "spine" / user's `memory.md`) is the **durable state** of a
loop run, persisting across iterations and process runs so an interrupted loop
can be **resumed** from the last completed checkpoint instead of restarting
(FR-005). It is **file-backed, JSON-lines**, escribed **atomically** so a reader
never sees a partial record.

This contract defines the ledger format and the resume contract.

## Location & scoping

- Stored under the caller-supplied `--ledger-dir <path>` (or `tmp_path` in
  tests).
- One file per run: `<run_id>.ledger.jsonl`.
- **Deterministic `run_id` scoping**: resume requires the same `run_id`;
  concurrent/resumed runs over the same ledger are scoped by `run_id`, and a
  resume with a different `run_id` starts a fresh run (documented; no silent
  overwrite of a different run).

## Records (append-only JSON lines)

Each line is a complete JSON object of one record type.

**Config record** (first line, once):
```json
{ "type": "config", "run_id": "<id>", "config": { "actor": "factory",
  "gate": "composite", "max_iterations": 5, "budget": null, "ratchet": null } }
```

**Iteration record** (one per completed iteration):
```json
{ "type": "iteration", "run_id": "<id>", "iteration": 2,
  "actor_out": { "status": true, "artifact_refs": ["..."] },
  "gate":   { "passed": false, "checks": [ { "name":"suite_pass",
              "stage":"deterministic","passed":false,"reasons":["..."] } ],
              "consumed": { "tokens": 40, "cost_usd": 0.0002, "latency_s": 0.1 } },
  "budget_delta": { "tokens": 40, "cost_usd": 0.0002, "latency_s": 0.1 },
  "repair_context": "<= bounded, concise verdict ref (never full dump)" }
```

**Final record** (last line, once):
```json
{ "type": "final", "run_id": "<id>", "status": "exhausted", "iterations": 5,
  "budget_consumed": { "tokens": 200, "cost_usd": 0.001, "latency_s": 0.6 },
  "escalation": { "status": "exhausted", "iterations": 5, "partial_artifacts": ["..."] } }
```

## Atomicity

- **Atomic write** (tmp + rename): each record is written to a temp file then
  atomically renamed onto the ledger, so a concurrent reader never sees a
  half-written line. This matches the research rule "escrita atômica" (§3).

## Bounded content

- Artifacts are **referenced, not duplicated** into the ledger (edge case).
- `reasons` / repair context stay **concise** (fits context window); the ledger
  records the last N verdicts, never unbounded history (§3 "memory.md bounded").

## Resume contract (FR-005)

- **Resume** reads the ledger for `run_id`, locates the **last completed
  `IterationRecord`** (highest `iteration`), and continues from iteration `k+1`
  (never re-running completed iterations).
- **Absent ledger on resume** → start a **new run** (with a warning) or surface
  a clear error.
- **Corrupt ledger on resume** → same documented behavior (new run + warning or
  clear typed error) — **never silently corrupt data**.
- `LoopResult` is derivable from the ledger at the end (or reconstructed on
  resume for a run summary: iterations, verdicts, budget, status — human- and
  machine-readable, US4).

## Testability

- `tmp_path` ledger makes pause/resume deterministic and network-free: start a
  loop with a failing gate, simulate interruption after k iterations, resume,
  assert the loop continues from `k+1` and completes with the correct total
  (SC-004).