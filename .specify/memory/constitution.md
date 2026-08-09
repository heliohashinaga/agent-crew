<!--
Sync Impact Report
- Version change: (uninitialized) → 1.0.0
- Modified principles: none (initial ratification)
- Added sections:
  - Core Principles: I. Library-First, II. CLI Interface, III. Test-First (NON-NEGOTIABLE),
    IV. Integration Testing, V. Simplicity & Observability
  - Technology & Constraints
  - Development Workflow
  - Governance
- Removed sections: none
- Follow-up TODOs: none. Principles adopted from canonical Spec Kit philosophy
  adapted to the ai-factory project. Revisit and tailor once the project's
  domain (the "AI factory" scope) is defined in specs/README.
-->

# ai-factory Constitution

## Core Principles

### I. Library-First

Every capability starts as a standalone library before any UI, service, or
integration layer is built on top of it.

- Libraries MUST be self-contained, independently testable, and documented.
- Each library MUST have a clear single purpose; organizational-only libraries
  (grouping with no behavior) are forbidden.
- Consumers (CLIs, services, agents) depend on libraries, never the reverse.

**Rationale**: Isolated libraries are the unit of reuse, testability, and
LLM-assisted change; keeping behavior out of thin wrappers prevents hidden
coupling.

### II. CLI Interface

Every library MUST expose its functionality through a command-line interface.

- Text-in / text-out protocol: inputs via stdin or args, results to stdout,
  errors and diagnostics to stderr.
- MUST support both machine-readable (JSON) and human-readable output formats.
- Exit codes MUST be meaningful (0 success, non-zero failure).

**Rationale**: CLI boundaries make capabilities composable, scriptable, and
directly verifiable by both humans and AI agents without bespoke glue.

### III. Test-First (NON-NEGOTIABLE)

Test-driven development is mandatory and may not be skipped.

- Tests MUST be written and user-approved before implementation.
- Tests MUST fail before the implementation is written (Red).
- Implementation MUST be completed only when tests pass (Green), then refactored.
- The Red-Green-Refactor cycle is strictly enforced on every change.

**Rationale**: Tests written first encode the contract; they are the
executable specification that protects behavior during later, faster change.

### IV. Integration Testing

Integration tests MUST cover the seams where libraries, services, or schemas
meet.

- New library contract tests MUST be added when a library is introduced.
- Contract changes MUST update or add integration tests before merge.
- Inter-component communication and shared schemas MUST be covered.

**Rationale**: Unit tests prove internal correctness; integration tests prove
the system holds together at the boundaries most likely to break.

### V. Simplicity & Observability

Prefer the simplest design that satisfies the current requirement, and make
every component observable.

- YAGNI: do not build for speculative future needs; justify every abstraction.
- Structured logging MUST be emitted at component boundaries.
- Text I/O (Principle II) is the primary debuggability channel.
- Complexity MUST be justified against the simpler alternative it replaces.

**Rationale**: Simple, observable systems are easier to verify, change, and
trust—especially under AI-assisted development where hidden state compounds risk.

## Technology & Constraints

- **Runtime**: Python >= 3.14, managed with `uv`.
- **Project layout**: `src`-style packaging via `pyproject.toml`; libraries are
  installable and independently testable.
- **Spec Kit**: this project is governed by Spec Kit with the `pi` integration;
  the constitution → spec → plan → tasks → implementation workflow is binding.
- **I/O formats**: every CLI MUST support JSON and a human-readable format.
- **Dependencies**: new dependencies MUST be justified; prefer the standard
  library where it suffices.

## Development Workflow

- **Spec Kit flow**: Constitution → `/speckit.specify` → `/speckit.plan` →
  `/speckit.tasks` → `/speckit.implement`, in that order, before code.
- **Test gate**: no implementation merge without passing, user-approved tests
  (Principle III).
- **Review**: all changes MUST be reviewed for constitution compliance before
  merge; reviewers MUST reject changes that violate a NON-NEGOTIABLE principle.
- **Migration**: any change that breaks existing contracts MUST ship a migration
  path documented in the spec/plan.

## Governance

- This constitution supersedes all other project practices where they conflict.
- Amendments MUST be documented, reviewed, and approved, and MUST include a
  migration plan for any principle that is removed, renamed, or redefined.
- Versioning follows semantic versioning:
  - MAJOR: backward-incompatible governance or principle removal/redefinition.
  - MINOR: new principle/section added or materially expanded guidance.
  - PATCH: clarifications, wording, typo fixes, non-semantic refinements.
- Every PR and review MUST verify compliance with this constitution.
- Complexity MUST be justified against the simpler alternative; when in doubt,
  defer to the simpler design.

**Version**: 1.0.0 | **Ratified**: 2026-08-08 | **Last Amended**: 2026-08-08
