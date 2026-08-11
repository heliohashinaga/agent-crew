# Specification Quality Checklist: Folder-Driven Dev Run

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-09
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders (N/A: developer-tooling CLI feature; audience is technical)
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (FR-001..FR-014d each map to an acceptance scenario / SC; verified)
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- This feature consolidates the factory entry point: `spec-run`/`spec-workflow` are removed
  and `dev-run <folder>` consumes a ready speckit spec folder, mirroring the speckit
  `implement` skill. Requirement clarification/refinement is owned by the external speckit
  `clarify` skill, which can be run multiple times; the factory assumes the folder is ready
  and never re-derives requirements.
- Open items to close before `/speckit.plan`:
  1. `Content Quality` — the spec deliberately names speckit artifacts and factory workflow
     names (`spec.md`, `plan.md`, `tasks.md`). This is arguably an implementation reference;
     the names are the *contract* (folder contents), not HOW-to language. Confirm it is
     acceptable to keep artifact filenames as the entry contract, or abstract them further.
  2. `Written for non-technical stakeholders` — the spec uses factory/speckit domain terms;
     confirm the intended audience includes non-technical readers or accept technical framing
     (this is a developer-tooling feature).
  3. `All functional requirements have clear acceptance criteria` — each FR maps to an
     acceptance scenario/SC; confirm mapping coverage in the plan step.
- The decision to remove `spec-run` supersedes the original `001-ai-dev-factory` framing that
  the two workflows are joined ONLY by `spec_version_id`. This feature is a deliberate
  architecture change (see `spec.md` assumptions), to be flagged in reviews.
- FR-014d + SC-007c (skip warning) are specified and implemented: completed tasks that are
  skipped by default or pruned by a selector surface a non-blocking `skip_warnings` notice
  (named task + reason) in `dev-run` output; `--force` re-runs them without a warning.
