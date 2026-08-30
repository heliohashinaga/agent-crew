# Research: LangChain Foundation — Hello-World Node

**Phase 0 output** — resolves the technical unknowns in the plan before design.

## Unknowns & Findings

### 1. How to represent an offline, deterministic node idiomatically in LangChain

- **Decision**: Implement the node as a `langchain_core.runnables.Runnable`
  built from a plain Python callable (via `RunnableLambda`). This is the
  smallest idiomatic LangChain building block and gives us `invoke()` /
  `stream()` semantics for free, with **no model, network, or credentials**.
- **Rationale**: A future agent swarm is composed of nodes, and LangChain's
  core building block is a `Runnable`. Starting with a `RunnableLambda` wires
  the framework in genuinely (imports `agentcrew` → `langchain_core`)
  while keeping the first slice deterministic and CI-safe. It validates the
  exact seam later nodes (including LLM-backed ones) will use.
- **Alternatives considered**:
  - A custom `Runnable` subclass with `invoke()`. More moving parts for no gain
    now; revisit only when a node needs custom streaming/batching semantics.
  - A real LLM-backed node (e.g., an LLM model wrapper). Requires API keys,
    network and non-determinism — explicitly out of scope for this first slice
    (spec `Out of Scope`).
  - A plain free function with no LangChain primitives. Technically simpler but
    does not actually establish the LangChain foundation the user asked for.

### 2. Invocation & output contract

- **Decision**: Use `runnable.invoke(input_str)`, returning a small structured
  result `{"input": <text>, "greeting": "Hello, <text>!"}`. Deterministic for a
  given input (FR-003).
- **Rationale**: A structured dict (validated as a Pydantic model) gives the CLI
  and tests a stable, machine-readable contract (CLI principle) while remaining
  hum, human-friendly.
- **Alternatives considered**: return a bare string — loses structure; unvalidated
  dict — no type guarantees for downstream nodes.

### 3. CLI shape

- **Decision**: A minimal `main()` under `cli.py` that composes the library node,
  formats human-readable output, and maps results to exit codes (0 / 4 / 1).
- **Rationale**: Upholds the constitution's "every library exposes a CLI with
  JSON + human output and meaningful exit codes" while staying minimal.
- **Alternatives considered**: no CLI at all (fires only via library) — violates
  the constitution's CLI principle.

## Consolidated Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Node type | `RunnableLambda` (LangChain core) | Idiomatic wiring; offline/deterministic |
| Invocation | `run.invoke(input)` | Standard LangChain semantics |
| Output | structured dict, Pydantic-validated | stable machine/human contract |
| CLI | `python -m agentcrew.cli` | compose library; JSON + human + exit codes |
| Runtime | zero network/credentials/deps beyond declared | spec constraint; CI-safe |