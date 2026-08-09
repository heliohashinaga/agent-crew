# Contract: spec-run CLI (Specification Workflow)

The Specification Workflow entrypoint. Turns a natural-language feature
request into an approved, versioned specification (FR-002, FR-024).

## Interface

```text
spec-run --request <text|--stdin> [--scope <scope>] [--format json|human]
```

- **Input**: a `FeatureRequest` (raw text, optional scope, constraints,
  linked materials).
- **Output (stdout)**: a `SpecVersion` (JSON by default). On approval, the
  emitted record carries the stable `spec_version_id` and `spec_run_id`
  (FR-025, SC-017).
- **Diagnostics**: to stderr.
- **Exit codes**: `0` approved; `2` rejected (review failed); `3` needs
  clarification (waiting on user); non-zero otherwise.

## Workflow (LangGraph `StateGraph`)

1. `spec_agent` — produces a draft spec (intent, rationale, acceptance
   criteria, definition of done, edge cases). Surfaces bounded
   clarifications for scope-critical ambiguity (FR-006).
2. `requirements_reviewer` — validates against clarity, completeness,
   consistency, testability, edge-case coverage (FR-004). On reject, routes
   back to `spec_agent` with specific feedback (bounded cycles).
3. `human_approval` gate — the run does not mark `approved` until a human
   approves (FR-005). Until then the spec is `under_review`.

## Guarantees

- MUST NOT write implementation code or perform codebase-specific technical
  refinement (FR-001).
- MUST persist the approved `SpecVersion` locally with a stable
  `spec_version_id` (FR-025).
- Records each `SpecRoleInvocation` (telemetry) per the
  [library CLI convention](./library-cli-convention.md).
- The run is a distinct top-level trace (FR-024); its `spec_run_id` is what
  a later dev run carries for traceability (SC-017).

## Out of scope

Technical plan, task breakdown, and any execution belong to `dev-run`
(FR-001; spec Assumptions).