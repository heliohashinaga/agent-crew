# No-Plan Fixture — Feature Flags

A speckit folder that omits `plan.md`, exercising the degradation path where the
adapter must fall back to defaults plus an inference note (US-2, FR-004, SC-005).

## Functional Requirements

- FR-001: Support feature flags for tenant isolation.
- FR-002: Provide a flag management CLI.

## Non-Goals

- No runtime config service.
