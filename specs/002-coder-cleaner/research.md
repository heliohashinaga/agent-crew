# Research: Coder → Cleaner Agent Pipeline

**Spec**: [spec.md](./spec.md) | Phase 0 output

## Question

How should `agent-crew` implement its first multi-node agent handoff (coder →
cleaner) while keeping the offline/deterministic base and opt-in LLM behavior?

## Findings (local + ecosystem)

- **`clean code` as the cleaner's mandate (user clarification)**: the
  `CleanerAgent` applies **clean code standards** to the code the coder
  generates. Literature (R. C. Martin) defines clean code as the standard for
  *creating* readable, maintainable, well-structured code — distinct from
  *refactoring*, which is the process of evolving existing code while preserving
  behavior. Rules center on: small functions that do one thing, descriptive
  verb-phrase names, consistent vocabulary, no redundant comments.
- **Two concerns, two owners (final decision = Option A)**:
  1. *Formatting* — perfectly solved by real formatters (Black, ruff): trailing
     whitespace (`trim_trailing_whitespace`), single EOF newline
     (`eol-last`/`missing-final-newline`), CRLF→LF, max line length
     (`--line-length`). These are **deterministic** and are delegated to the
     existing formatter (Black/ruff), **outside the cleaner node** (FR-005) — an
     LLM would be non-deterministic and could invent style.
  2. *Semantic clean code* — the cleaner's **only** job, LLM-backed (opt-in):
     descriptive naming, small single-purpose functions, removing redundant
     comments (e.g. the "reiterating the code" smell). Not safely automatable by
     a formatter.
- **Frontier (out of v1)**: removing dead code / unused imports is partially
  automatable only by a real linter (e.g. ruff `F401`/`F841`), which requires
  interpreting the language — deferred to a future "lint" step.
- **Multi-node orchestration** belongs in LangGraph (`StateGraph`/`START`/`END`,
  typed state, per-node partial updates) — already a transitive dep; also gives
  native LangSmith node traces.
- **Offline/LLM split** follows repo precedent (hello_world deterministic;
  `agentcrew.nodes.llm` opt-in, OpenRouter/OpenCode Go).
- **Handoff testability**: LangGraph nodes are plain functions over state, so a
  contract test can stub node outputs and assert coder-before-cleaner (no net).

## Recommended approach

1. Add `langgraph>=1.2.10` as an explicit dependency (FR-009).
2. Define shared `TaskState` + node results (`data-model.md`).
3. `CoderAgent` — LLM-backed, task → code (opt-in key).
4. `CleanerAgent` — **semantic clean code only**, LLM-backed (opt-in);
   formatting delegated to Black/ruff outside the cleaner (FR-005).
5. `CoderCleanerGraph` — `StateGraph`: START → coder → cleaner → END.
6. `agentcrew-code` CLI + offline contract/unit tests; opt-in real-LLM test.

## Trade-offs

- **Deterministic vs. LLM cleaner**: hybrid captured obvious value (an offline,
  always-predictable baseline) at minimal cost; deep stylistic cleaning stays
  opt-in. Final answer per user clarification: **hybrid**.
- **LangGraph vs. hand-rolled chaining**: LangGraph gives typed state, future
  routing/checkpointing, and native LangSmith node traces; cost is a new direct
  dependency (FR-009 makes it explicit).
- **Not in scope (v1)**: routing/loops, HITL, cross-process persistence, running
  the generated code (cleaner only normalizes text).

## Sources

- R. C. Martin, *Clean Code* (functions, meaningful names, smel/strategy) —
  sample chunks and Prentice Hall excerpts (ptgmedia.pearsoncmg.com, oreilly.com;
  seen via web search).
- Formatter/linter rules: Black (`--line-length`, trailing whitespace, EOF),
  ESLint Stylistic (`eol-last`, `no-trailing-spaces`), Ktlint, pylint
  (`missing-final-newline`, `max-line-length`), EditorConfig
  (`trim_trailing_whitespace`) — consulted via web search synthesis.
- LangGraph skill (session): `StateGraph`/`START`/`END`, partial-update
  semantics, InMemorySaver for dev/tests.
- Repository precedent: `specs/001-langchain-hello-node/`, `src/agentcrew/nodes/`
  (hello_world, llm), `.specify/memory/constitution.md`.