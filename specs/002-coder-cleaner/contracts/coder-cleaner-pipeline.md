# Contract: Coder → Cleaner Pipeline (CLI + handoff)

**Spec**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

## Purpose

Pin the observable contract of the coder→cleaner pipeline: the node-to-node
handoff (Principle IV) and the `agentcrew-code` CLI surface (Principle II). The
pipeline is **language-agnostic** (Session 2026-08-31 clarification): it accepts a
task in any language and returns code in that language; formatting stays only in
the repo's Python Black/ruff tooling.

## Handoff contract (node-to-node)

Given a non-empty `task`, invoking the compiled graph MUST run the `coder` node
first, then the `cleaner` node, and return a state with both `coder_output` and
`cleaner_output` populated (FR-003/FR-004).

- `coder_output` — the candidate code produced by the coder from `task`.
- `cleaner_output` — the code after the **semantic-clean-code** cleaner
  (descriptive naming, small functions, removing redundant comments). If the
  cleaner can't run the LLM, it returns `coder_output` unchanged.

Ordering is asserted by a contract test using **mocked node outputs** (offline):
the cleaner node must observe `coder_output` already populated.

## CLI (`agentcrew-code`)

```
usage: agentcrew-code [--provider openrouter|opencode] [--model NAME]
                      [--format text|json] <task>
```

Behaviour:

- Reads the task (exactly one positional). Optionally accepts `--provider`
  (`openrouter` default / `opencode`), `--model`, `--format` (`text`|`json`).
- Loads provider keys from the local `.env` (reuses `agentcrew.nodes.llm`);
  if the selected provider has no key, fails fast with a clear hint.
- Calls the library graph (never contains business logic).

Exit codes:
| Code | Meaning |
|------|---------|
| `0`  | success |
| `1`  | usage error: missing/blank task, bad provider, bad flag |
| `4`  | runtime failure: missing provider key, LLM/cleaner failure |

Output:
- `--format text` (default): prints the cleaned code to stdout.
- `--format json`: prints a JSON object with `task`, `coder_output`,
  `cleaner_output`, and `model`.

Errors go to stderr.

## Compose-only rule

The CLI imports and composes `build_coder_cleaner_graph()` (and the nodes) from
the library. The reverse (library importing the CLI) is never allowed
(constitution Principle I).

## Testing seam (offline)

To test without network, inject **fake node outputs**: build the graph with node
functions whose underlying LLM call is replaced by a stub returning a fixed
`coder_output`; assert the cleaner then receives it and produces `cleaner_output`.
This is the basis of `tests/contract/test_coder_cleaner_graph.py` (T005) and
`tests/contract/test_coder_cli.py` (T011). Formatting is **not** part of the
cleaner (FR-005): use `ruff format`/Black at the CI/editor seam, never the LLM.