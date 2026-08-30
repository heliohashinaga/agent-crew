# Contract: Hello-World Node CLI

**Feature**: `001-langchain-hello-node`

Primary contract between the user/developer and the base. The CLI **composes**
the library node; it does not contain business logic.

## Command

Module form (explicit `hello` verb):

```
uv run python -m agentcrew.cli hello <text>
```

Equivalent console-script form (the `hello` verb is implied by the dedicated
command and omitted):

```
uv run agentcrew-hello <text>
```

`main()` parses both accepted forms.

## Behavior

- Accepts a single `<text>` argument (an optional leading `hello` verb is
  tolerated and then ignored).
- Invokes the hello-world node with that text and returns its structured result.
- Empty or whitespace-only `<text>` is rejected as a usage error.

## Output formats

- **Human-readable** (default): `Hello, <text>!` on stdout.
- **JSON** via `--format json`:
  ```json
  { "input": "<text>", "greeting": "Hello, <text>!" }
  ```

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success — node produced a greeting |
| `1` | Usage error — missing/invalid `<text>` argument |
| `4` | Runtime error — invocation failed for an unexpected reason |

## Library seam

The same node is callable programmatically:

```python
from agentcrew.nodes.hello_world import build_hello_world_node

node = build_hello_world_node()
result = node.invoke("Ada")   # {"input": "Ada", "greeting": "Hello, Ada!"}
```

See [data-model.md](../data-model.md) for the result shape.