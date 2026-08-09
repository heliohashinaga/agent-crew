# Research: AI Software Development Factory

**Feature**: 001-ai-dev-factory | **Date**: 2026-08-09 | **Spec**: [spec.md](./spec.md)

This document resolves the Technical Context unknowns and records the
decisions, rationale, and alternatives for each technology choice and
design question surfaced during planning. Every entry is grounded in the
project decision notes (`docs/pi-vs-langgraph.md`,
`docs/pydantic-v1-decision.md`) and the constitution.

---

## R1. Orchestration-graph substrate: LangGraph

**Decision**: Use **LangGraph** as the orchestration-graph substrate. Each
workflow is a **separate `StateGraph`** — `spec_workflow/graph.py` and
`dev_workflow/graph.py` — rather than one merged graph.

**Rationale**:
- The factory has 9 roles, retry loops, escalation, and re-planning
  (FR-013/FR-014/FR-015) — exactly the conditional-branching,
  checkpointing, and state-management workload LangGraph is built for.
- Native **checkpointing** makes resumability (FR-020) a graph feature
  rather than bespoke persistence code; a re-launch resumes from the last
  checkpoint.
- LangGraph's `StateGraph` is **well-comprehended by LLMs**, lowering the
  risk of AI-assisted changes to the workflow graphs themselves (relevant
  since the factory edits its own kind of codebase).
- Two separate graphs directly realize FR-024 (two independent workflows)
  and FR-025 (clean hand-off boundary): the spec run and dev run are
  distinct top-level executions joined only by `spec_version_id`.

**Alternatives considered**:
- **Pi Agent (single runtime)**: rejected in `docs/pi-vs-langgraph.md` —
  lacks robust observability and state management for this complexity, and
  would force a 4–6 week refactor to LangGraph later. Pi remains useful as
  the *interactive coding agent* that builds the factory, but is not the
  factory's runtime substrate.
- **One merged graph**: rejected — conflates two different state machines
  (spec review loop vs. dev retry/escalation), couples the two workflows,
  and breaks the "spec can exist with zero dev runs" property (SC-009).

---

## R2. Observability backend: LangSmith

**Decision**: Use **LangSmith** as the observability backend for v1. The
spec run and the dev run are **two distinct top-level traces**, linked by
metadata (`spec_version_id`, `spec_run_id`) carried on the dev run.

**Rationale**:
- LangSmith is the native observability pairing for LangGraph (R1) and is
  recommended "from day 1" in `docs/pi-vs-langgraph.md` for tracing and evals.
- Per-role telemetry (FR-016: role, model, capability level, tokens, cost,
  latency, tool calls, retries, errors, escalations, result) is captured
  at graph-node boundaries.
- Two distinct traces + metadata link satisfy SC-016/SC-017 (the two
  workflows are separately findable and the dev run is traceable back to the
  spec run) **without** merging the graphs.

**Alternatives considered**:
- **OpenTelemetry-only / generic tracing**: viable but lower leverage for
  LLM-specific signals (tokens, model, capability level); deferred beyond
  v1. The spec is intentionally tech-agnostic on the backend (FR-024/FR-025
  name no tool), so swapping later is not blocked.
- **Single merged trace**: rejected — violates FR-024's clean-boundary
  intent and conflates spec-quality metrics with execution metrics.

**Note**: The spec deliberately names no observability tool in its
requirements (FR-024/FR-025/SC-016/SC-017 are tech-agnostic). LangSmith is a
**planning decision** recorded here, not a spec mandate.

---

## R3. State modeling: Pydantic (selective)

**Decision**: Use **Pydantic** for `FactoryState` and all critical models
(spec, plan, assessment, execution plan, ADR, telemetry record, review
decision, checkpoint). Use `TypedDict`/`dict` only for non-critical,
ephemeral, or pass-through payloads.

**Rationale** (per `docs/pydantic-v1-decision.md`):
- `FactoryState` is complex (spec, plan, code, test results, security
  assessment, retry count, checkpoints, …); runtime validation catches
  malformed state early.
- IDE autocomplete and type narrowing reduce AI-assisted change errors.
- Pydantic models serialize cleanly for LangSmith (R2) and for checkpoint
  persistence (FR-020).
- "Pydantic selectively, not everywhere in v1" keeps the cost down on
  non-critical paths.

**Alternatives considered**:
- **Plain dicts everywhere**: rejected — runtime bugs, poor IDE support,
  no validation, worse LangSmith serialization.
- **Pydantic everywhere**: rejected — overkill for ephemeral/passthrough
  data; violates Simplicity (Principle V).

---

## R4. Runtime, language, packaging

**Decision**: Python ≥ 3.14, managed with `uv`; `src`-style packaging via
`pyproject.toml`; libraries are installable and independently testable.

**Rationale**: Mandated by the constitution ("Technology & Constraints").
No NEEDS CLARIFICATION — this is settled governance, not a planning choice.

---

## R5. LLM provider abstraction

**Decision**: Introduce a **pluggable LLM provider abstraction** under
`shared/llm/`. The Orchestrator selects a provider+model per role/task from
the assessment (FR-009). The factory loads provider credentials only from
the environment or a dedicated secret store (FR-018).

**Rationale**:
- FR-009 requires per-role model selection; a pluggable abstraction is the
  minimal design that supports this without hard-coding a vendor.
- FR-018 (credentials from env/secret store only) is enforceable at one
  seam if all providers go through the abstraction.

**Open implementation details (deferred to tasks/implementation)**:
- Exact provider set supported in v1 (e.g., OpenAI, Anthropic, a local
  model). The abstraction is the v1 deliverable; additional providers can
  be added without changing the workflows.
- Whether the abstraction wraps an existing SDK or is hand-rolled is a
  tasks-phase decision guided by Simplicity (Principle V).

**Alternatives considered**:
- **Hard-code one provider**: rejected — blocks FR-009's per-role model
  choice and the capability-level model mapping (FR-010).
- **No abstraction, call SDKs inline**: rejected — scatters credential
  handling and telemetry, violating FR-018's single-seam enforceability
  and Simplicity.

---

## R6. Sandboxed execution of AI-generated code

**Decision**: Run AI-generated code and tests inside an **isolated
container/sandbox by default**, with the target repository mounted
read-write and the rest of the host isolated (FR-021). A sandbox-runner
library under `shared/sandbox/` wraps the container runtime.

**Rationale**:
- The factory runs autonomously (FR-023) and may proceed unattended through
  retries/re-plans; un-sandboxed AI-generated code could damage the host or
  exfiltrate data. Bounding the blast radius is a security baseline, not a
  nice-to-have.
- Mounting the repo read-write lets the Code Worker and Test Runner operate
  normally while host isolation contains side effects.

**Open implementation details (deferred to tasks)**:
- Concrete runtime (Docker/Podman/etc.) — chosen for availability and a
  minimal client surface; not a spec concern.
- **Edge case (spec)**: if no container runtime is available, the factory
  MUST fail the run early with a clear reason rather than falling back to
  running on the host (spec Edge Cases).

**Alternatives considered**:
- **Run on host directly**: rejected — violates FR-021/SC-013 and the
  autonomous-run threat model.
- **Host + restricted working directory, no container**: rejected — weaker
  isolation; insufficient for arbitrary AI-generated code.

---

## R7. Git-host PR delivery

**Decision**: The factory **opens the PR itself** on the remote git host via
the host's API, using host credentials from the secret store (FR-022). A
pluggable git-host client lives under `shared/git_host/` (e.g., a GitHub
adapter, a GitLab adapter).

**Rationale**:
- FR-022 mandates factory-opened PRs; a pluggable client keeps the factory
  host-agnostic at the seam.
- Credentials come through the same secret-store path as LLM creds (FR-018),
  enforceable at one seam.

**Open implementation details (deferred to tasks)**:
- Which hosts are supported in v1 (e.g., GitHub only, or GitHub + GitLab).
  The abstraction is the v1 deliverable; adapters are additive.
- **Edge case (spec)**: if the host is unreachable or credentials are
  missing/invalid at delivery time, the factory MUST fail delivery with a
  clear reason and keep the local branch intact (spec Edge Cases).

**Alternatives considered**:
- **Prepare local branch, user opens PR**: rejected by the user
  clarification (FR-022) — the factory opens the PR.
- **Auto-merge the PR**: rejected — violates FR-012/FR-022 (humans merge).

---

## R8. Persistence & checkpoints

**Decision**: v1 persists artifacts (specs, plans, ADRs, checkpoints,
telemetry, run state) on the **local filesystem**. SQLite is a candidate
for telemetry/run query indexes but is **not mandatory for v1** — it is
deferred to the tasks phase as an optional index layer.

**Rationale**:
- Spec Assumptions explicitly scope v1 to local artifacts and rule out
  cross-host sharing; the filesystem is the simplest sufficient store
  (Simplicity, Principle V).
- LangGraph checkpointers (R1) provide the resumability mechanism (FR-020);
  a filesystem checkpointer is sufficient for v1.
- Telemetry (FR-016) can be emitted as structured records (JSON lines) and
  queried via the CLI; a DB is an optimization, not a v1 requirement.

**Alternatives considered**:
- **SQLite for all state from day 1**: rejected for v1 scope — adds a
  schema/migration surface (constitution "Migration" rule) without a v1
  need; keep as optional index later.
- **Remote/shared store**: rejected — out of scope for v1 (spec Assumptions).

---

## R9. Capability levels (FR-010)

**Decision**: Define per-role capability levels in one library
(`capability_levels/`), mapping each level to model, token budget,
iteration count, and tool-access. Code Worker and Test Engineer use
simple/standard/complex; Code Reviewer and Security Reviewer use
shallow/standard/deep (FR-010). The Orchestrator reads this mapping when
producing the Execution Plan (FR-009).

**Rationale**:
- Centralizing the level definitions keeps the capability-level contract
  in one testable place (Library-First) and lets the Orchestrator remain a
  pure decision layer.
- Exact model/budget/iteration/tool-access values are **implementation
  decisions** (spec Assumptions) and are filled during tasks/implementation,
  not here.

**Alternatives considered**:
- **Per-role ad-hoc levels**: rejected — duplicates the contract and
  scatters the model/budget mapping; violates Simplicity.

---

## R10. ADR production (FR-008)

**Decision**: The Technical Planner produces an **ADR only when a
significant architectural decision is present** (non-conventional choice,
important trade-off, workaround, legacy/system constraint, or unusual bug
fix). ADRs are recorded with decision, rationale, trade-offs, and
alternatives. The Code Reviewer validates adherence to the ADR; ADRs are
reviewed by the human at PR time (FR-023).

**Rationale**: Directly from FR-008 and the reference design — conditional
ADRs keep the design lightweight (Simplicity) while preserving traceability
for decisions that matter.

**Alternatives considered**:
- **ADR for every change**: rejected — noise; violates Simplicity.
- **No ADRs**: rejected — loses traceability for significant decisions
  (FR-008).

---

## R11. Issue handling, retry, escalation, re-planning (FR-013/014/015)

**Decision**: Model issue handling as LangGraph conditional edges within the
dev workflow graph: bounded retry loops per issue type (exponential backoff
for transient/infra; route-to-Code-Worker for deterministic bugs), escalation
to the appropriate role, and re-planning via the Technical Planner when a
limit is exceeded. CRITICAL security issues halt, fix immediately, and
require a full re-audit before merge (FR-014). The factory stops for a human
**only when re-planning itself fails** (FR-015).

**Rationale**: Native LangGraph conditional edges and checkpointing (R1)
make these loops first-class graph features rather than bespoke control
flow. Bounded defaults for retries/re-plans are implementation decisions
(spec Assumptions), filled during tasks.

**Alternatives considered**:
- **Unbounded retries**: rejected — violates "bounded" (FR-014/FR-015).
- **Hard-stop on any failure**: rejected — defeats the autonomous factory
  (FR-023) and the issue-handling design (FR-013).

---

## R12. Model mapping for *implementing* the factory (distinct from runtime)

**Decision**: Use a tiered model mapping for **implementing** the AI Factory
— the coding agent that writes the factory's own code — separate from the
runtime model selection (R5, FR-009). Base tier: **DeepSeek V4-Flash**
(~$0.14/$0.28 per 1M tokens, 1M context, ~54.4% SWE-bench, open-weight MIT)
for ~90% of the work (state, secrets, CLI boilerplate, Pydantic schemas,
contract tests, role libraries). Strong tier: **DeepSeek V4-Pro**
(~$0.435/$0.87, 1M context, ~80.6% SWE-bench) for the 2–3 architecturally
sensitive files where errors force core refactors: `spec_workflow/graph.py`
(T021), `dev_workflow/graph.py` (T064), and `shared/spec_store/handoff.py`
(T025). The sensitive files MUST be reviewed manually after generation.

**Rationale**:
- V4-Flash is the price/performance leader as of Aug 2026 (~50× cheaper
  than Claude Sonnet 5 post-Sep-1 pricing), with a 1M context window that
  satisfies the multi-file requirement of this codebase.
- Open-weight MIT pricing is stable and unaffected by the Sep 1, 2026
  Sonnet 5 price/tokenizer increase.
- V4-Pro on the sensitive files closes the quality gap at ~3× Flash's cost
  (still far below Sonnet); manual review of those 2–3 files mitigates the
  remaining risk.
- This is an **implementation-time** decision recorded for the implementer;
  it does NOT constrain the factory's runtime model selection (R5/FR-009),
  which is calibrated per-role via telemetry (SC-006).

**Alternatives considered**:
- **Claude Sonnet 5 base + Opus 5 on graphs** (~$5–20 MVP): lowest risk but
  50× the cost and exposed to the Sep 1 price increase. Viable if budget is
  unconstrained.
- **Kimi K2.7 base + DeepSeek V3.2 on graphs** (~$0.50–3 MVP): cheaper than
  Claude but ~5× the V4-Flash tier; superseded by V4-Flash's 1M context at
  lower cost.
- **Single model everywhere**: rejected — the sensitive graphs warrant a
  stronger model than the boilerplate workload justifies.

**Note**: Model names/prices move fast; confirm V4-Flash/V4-Pro pricing on
the provider site before locking in. The strategy (cheap base + strong on
sensitive files) is stable regardless of exact versions.

---

## Summary of resolved NEEDS CLARIFICATION

| Item | Resolution |
|------|------------|
| Language/version | Python ≥ 3.14 + `uv` (constitution) — R4 |
| Orchestration substrate | LangGraph, two `StateGraph`s — R1 |
| Observability backend | LangSmith, two traces + metadata link — R2 |
| State modeling | Pydantic selective — R3 |
| LLM provider | Pluggable abstraction, env/secret-store creds — R5 |
| Code execution isolation | Container/sandbox by default — R6 |
| PR delivery | Factory-opened PR via host API client — R7 |
| Persistence | Local filesystem for v1; SQLite optional — R8 |
| Capability levels | Centralized level-mapping library — R9 |
| ADRs | Conditional, by Technical Planner — R10 |
| Implementation models (coding agent) | DeepSeek V4-Flash base + V4-Pro on sensitive graphs — R12 |
| Issue handling | LangGraph conditional edges, bounded — R11 |

No NEEDS CLARIFICATION markers remain in Technical Context.