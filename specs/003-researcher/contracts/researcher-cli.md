# Contract: `ai-factory-researcher` CLI (Researcher role)

The researcher is a **mono-capacity, fixed** lookup role in the ai-factory. Its
CLI lets a caller (a human or a factory role/script) query either the local
repository (`repo` scope) or the web (`web` scope, in v1) and receive a
**concise, sourced `ResearchResult`** — keeping the invoking agent's context
small and using a constant execution profile (no `capability_levels` bump).

This contract defines the public interface for the `ai-factory-researcher`
console script.

## Interface

```text
ai-factory-researcher --scope <repo|web> --query <text> [--roots <path,...>]
             [--output-format <json|human>] [--run-id <id>]
             [--telemetry <bool>] [--help]
```

- **`--scope <repo|web>`** (default `repo`): which source to query.
  - `repo` — scan local text files under `--roots` (deterministic, network-free).
  - `web` — run multi-angle queries, rank (best-per-angle), fetch content,
    summarize via the injected/configured `LLMProvider` (network-bound, `-m
    integration`; errors surface non-zero, never silently empty).
- **`--query <text>`** (required): the natural-language query.
  - An **empty/absent** `--query` argument is a **usage error** (non-zero).
    An empty-string query `""` passed through is treated as "empty result" at
    the library level (FR-004) — the CLI still requires the flag to be present.
- **`--roots <path,...>`** (comma/repeated; **required for `repo`**): the repo
  root(s) to scan. Missing when `--scope repo` is a usage error (non-zero).
- **`--output-format <json|human>`** (default `json`): stdout shape.
- **`--run-id <id>`**, `--telemetry <bool>`: standard observability flags.

## Exit codes

| code | meaning |
|------|---------|
| `0`  | success — a `ResearchResult` was produced and written to stdout |
| `1`  | usage error (missing/invalid `--query`, `--roots` for `repo`, bad `--scope`, bad `--output-format`) |
| `4`  | a lookup/resolution error (missing root dir, web network/LLM failure) |

## stdout / stderr

- **stdout**: the result payload. For `--output-format json`, a valid JSON
  serialization of `ResearchResult`; for `human`, a readable brief (summary +
  source pointers). Parsable with `ResearchResult.model_validate_json(...)`.
- **stderr**: diagnostics, telemetry/summary notes, warnings. Never the payload.

## Json payload (ResearchResult)

```json
{
  "role": "researcher",
  "query": "<truncated query>",
  "summary": "<concise prose synthesis>",
  "sources": [
    { "path": "src/auth/service.py", "lines": "14-40", "snippet": null, "truncated": false }
  ],
  "scopes_used": ["repo"]
}
```

- `role` is always `"researcher"`.
- For `web` scope, `sources[].path` holds a URL; `lines`/`snippet` may be
  `null`; `truncated` notes content-capging.
- `scopes_used` reflects the actual scope(s) resolved (e.g. `["repo"]` or
  `["web"]`).

## Notes

- This feature's contract **supersedes any implied single-source CLI** and
  codifies repo + web in v1 (FR-010), multi-angle best-per-angle selection,
  and the mono-capacity profile. It does **not** add `--budget-cost`/model
  limits (out of v1 scope per user: cost/tuning is future work).
