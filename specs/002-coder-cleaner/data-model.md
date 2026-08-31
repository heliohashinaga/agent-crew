# Data Model: Coder → Cleaner Agent Pipeline

Covers the shared state contract handed between the two pipeline agents and the
node result types they produce.

## Relationship: agents → shared `TaskState`

The two agents (`CoderAgent`, `CleanerAgent`) do not own their inputs/outputs
directly; they are **nodes** in the `CoderCleanerGraph` and communicate through a
shared `TaskState`. Each node returns a **partial update** to the state (LangGraph
semantics: only the keys it changes; default reducer is overwrite).

```
TaskState
  ├── task          (input, set by caller)          -> START
  ├── coder_output  (set by CoderAgent)             -> cleaner input
  ├── cleaner_output(set by CleanerAgent)           -> pipeline result
  └── error         (optional, set on failure)
```

## `TaskState` (graph shared state)

| Key | Type | Set by | Required | Constraints / Validation |
|-----|------|--------|----------|--------------------------|
| `task` | `str` | caller | yes | Non-empty, trimmed task text (FR-001/FR-003). Rejected if blank. |
| `coder_output` | `str` | CoderAgent | after coder | Candidate code text produced from `task`. |
| `cleaner_output` | `str` | CleanerAgent | after cleaner | Cleaned/refined code text. |
| `error` | `str` \| `None` | any node | no | Failure message propagated for a clear CLI exit (`4`). |

**Ordering constraint**: `coder_output` MUST be populated before the cleaner node
runs; the cleaner reads `coder_output` and produces `cleaner_output`
(FR-003/FR-004).

## `CoderOutput` / `CleanerOutput` (node results)

Concrete structured results (mirroring the existing `LLMNodeResult` pattern):

| Type | Field | Type | Required | Source |
|------|-------|------|----------|--------|
| `CoderOutput` | `task` | `str` | yes | trimmed input task |
| `CoderOutput` | `model` | `str` | yes | provider model id used (LLM) |
| `CoderOutput` | `code` | `str` | yes | candidate code (→ `coder_output`) |
| `CleanerOutput` | `code` | `str` | yes | the input code passed through |
| `CleanerOutput` | `refined` | `str` | yes | semantic-clean-code result (→ `cleaner_output`) |
| `CleanerOutput` | `llm_refine_applied` | `bool` | yes | whether the LLM refinement ran |

## Derivation rules

- `cleaner_output = llm_refine(coder_output)` — the cleaner applies **semantic
  clean code standards** (descriptive naming, small single-purpose functions,
  removing redundant comments) to the coder's code. It is LLM-backed (opt-in)
  and must fail gracefully (returning `coder_output` unchanged) if the model
  call fails.
- The cleaner is **not responsible for formatting** (FR-005). Deterministic
  formatting is delegated to a formatter (Black/ruff) run outside the cleaner
  node — the same path the project's CI/editor tooling already uses. This keeps
  the formatting step deterministic and the LLM out of that path.
- Empty/whitespace-only `task` is an input error — the CLI rejects it with a
  usage error (exit code `1`), per the contract.
- Empty/whitespace-only `task` is an input error — the CLI rejects it with a
  usage error (exit code `1`), per the contract.

## State transitions

Linear, non-looping: `START → task present → coder → coder_output → cleaner →
cleaner_output → END`. No conditional routing, no cycles (v1).

## Rationale

A single, explicitly typed shared state keeps the two agents decoupled while
making the handoff **observable** (each stage's output is a state key, FR-004).
The cleaner holds a single, well-scoped responsibility — **semantic clean code**
— and defers formatting to a deterministic formatter, so responsibilities do not
overlap (FR-005). InMemorySaver (if used) is only for dev/tests; persistence
across processes is out of scope.