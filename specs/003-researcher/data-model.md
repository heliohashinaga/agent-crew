# Data Model: Researcher (Lookup / Context Probe)

**Feature**: `003-researcher`
**Status**: Draft

> Design shift (supersedes the earlier "repo-first, web-deferred" framing): v1
> ships **repo + web** scopes. `researcher` is a **mono-capacity, fixed role**
> with a constant execution profile carried in its own library (outside
> `capability_levels`), mirroring the `spec_agent.agent.draft_spec`
> deterministic-core pattern.

## Entities

### `ResearchSource`
A single sourced pointer returned by a lookup.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `path` | `str` | ✅ | File path (`repo` scope) or URL (`web` scope). |
| `lines` | `str \| None` | optional | Line-range like `"14-40"` (`repo`); `null` for `web`. |
| `snippet` | `str \| None` | optional | Short excerpt, if captured. |
| `truncated` | `bool` | default `false` | `true` when the source content was capped/truncated to bound context (FR-005). |

### `ResearchResult`
The payload returned by `lookup(...)` and by the CLI.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `role` | `str` | ✅ | Always `"researcher"`. |
| `query` | `str` | ✅ | The (possibly truncated) input query. |
| `summary` | `str` | default `""` | Concise prose synthesis; **must not** contain a verbatim full-file dump (FR-002); fits the invoking role's context window. |
| `sources` | `list[ResearchSource]` | default `[]` | Sourced pointers (paths/URLs). Empty for a no-match (FR-004). |
| `scopes_used` | `list[str]` | default `["repo"]` | e.g. `["repo"]`, `["web"]`. |
| `tokens` | `int` | default `0` | Telemetry (post-run observability, not a cost/limit). |
| `cost_usd` | `float` | default `0.0` | Telemetry. |
| `latency_s` | `float` | default `0.0` | Telemetry. |

## Relationships

- `ResearchResult` owns 0..* `ResearchSource` (via `sources`).
- A lookup returns exactly one `ResearchResult` (success) or raises a typed
  error (resolution/fetch/LLM failure).

## Validation Rules (from FRs)

- **FR-002**: `summary` concise, context-window-fitting, never a verbatim
  full-file dump.
- **FR-003**: `role == "researcher"`, `query`, `scopes_used` present.
- **FR-004**: no-match / empty-string query → empty `sources` + empty `summary`
  at the library level (an absent `--query` on the CLI is a usage error).
- **FR-005**: non-text/binary files and noise dirs excluded; large files capped
  and marked `truncated`.

## State Transitions

None — a lookup is **stateless** (request in → `ResearchResult` out). No
lifecycle/state machine. `web` scope depends on injectable collaborators
(`LLMProvider`, `WebFetcher`, `ContentFetcher`); the `repo` core is
deterministic and network-free.
