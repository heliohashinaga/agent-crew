# Contracts — Researcher (003-researcher)

Feature contracts for the `researcher` role.

| Contract | Path | Covers |
|----------|------|--------|
| Researcher CLI | [`researcher-cli.md`](./researcher-cli.md) | `ai-factory-researcher --scope repo\|web` interface, exit codes, JSON payload, stdout/stderr split |

The `researcher` is a **mono-capacity, fixed** role; it does **not** participate in
`capability_levels`. Its CLI exposes both `repo` (deterministic, network-free) and
`web` (Option D, multi-angle best-per-angle) scopes returning `ResearchResult`.
Cost/model-limit tuning is out of scope for v1.
