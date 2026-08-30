# Data Model: LangChain Foundation — Hello-World Node

Covers the single entity needed by the hello-world node.

## Relationship: `HelloWorldNode` → `HelloWorldNodeResult`

- **`HelloWorldNode`** (spec entity) is the processing unit; it accepts text
  input and returns a greeting.
- **`HelloWorldNodeResult`** (this data model) is the structured **output** that
  the node returns. The two are distinct concepts: node vs. node's result.

The output contract produced by the node. No persistence (stateless, single
run).

| Field | Type | Required | Constraints / Validation |
|-------|------|----------|--------------------------|
| `input` | `str` | yes | Non-empty, trimmed text supplied by the user (FR-002) |
| `greeting` | `str` | yes | Determined output string; same value for same `input` (FR-003) |

## Derivation rule

- `greeting = "Hello, " + input + "!"` for any non-empty `input` (after
  trimming surrounding whitespace).
- Empty/whitespace-only input is an input error — the CLI rejects it with a
  usage error (exit code `1`), per the contract.

## State transitions

None — the node is a pure function of its input (input → output), with no
mutable state or lifecycle.

## Rationale

Kept to a single validated structure to satisfy the "Simplicity (YAGNI)"
principle. Additional fields (e.g., telemetry, node id) are intentionally
deferred until real orchestration/multi-node scope appears.