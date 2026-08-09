# Contract: Library CLI Convention

Every role/capability library in `src/ai_factory/` exposes a CLI that
follows this contract (constitution Principle II; FR-017).

## Interface

- **Input**: via stdin or args (text-in / args-in).
- **Output (stdout)**: machine-readable JSON by default; a human-readable
  format via a `--format human` flag.
- **Diagnostics**: to stderr.
- **Exit codes**: `0` success; non-zero failure (meaningful, not generic).

## Required behaviors

- MUST emit a `TelemetryRecord` (FR-016) for each invocation to the
  observability backend, with `role`, `model`, `capability_level`,
  `tokens_in/out`, `cost`, `latency`, `tool_calls`, `retries`, `errors`,
  `escalations`, `result`.
- MUST NOT emit secret-looking values; redaction is applied before any
  log/telemetry emission (FR-018, SC-010).
- Credentials MUST come from the environment or a dedicated secret store,
  never from committed config (FR-018).

## Relationship to workflows

The two workflow CLIs (`spec-run`, `dev-run`) compose these library CLIs;
libraries never depend on a workflow. This keeps each role independently
testable (constitution Principle I) and the two workflows decoupled
(FR-024).