# Absolute Paths Fixture — Logging Library

A speckit folder whose tasks.md contains absolute and out-of-repo paths that the
adapter must normalize (FR-008) and shared-file conflicts the adapter must flag
(SC-003).

## Functional Requirements

- FR-001: Centralize application logging.
- FR-002: Provide JSON formatter for structured logs.
- FR-003: Emit per-role telemetry to a log sink.
- FR-004: Do not write logs into the source tree.

## Non-Goals

- No replacing the system log daemon.
