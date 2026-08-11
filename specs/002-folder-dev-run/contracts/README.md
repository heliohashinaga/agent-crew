# Contracts — Folder-Driven Dev Run (`002-folder-dev-run`)

The CLI and plan contracts for this feature.

| File | Purpose |
|------|---------|
| [dev-run-cli.md](./dev-run-cli.md) | The changed `dev-run` entrypoint: folder-based, reads `spec.md`/`plan.md`/`tasks.md` (FR-001/002), no re-derivation (FR-005), removed `spec-run` (FR-006), path normalization (FR-008). |
| [spec-run-cli.md](./spec-run-cli.md) | **Removal record** (not an active interface): documents `spec-run`/`spec-workflow` removal and migration notes (FR-006, FR-009). Read as history of what was removed — do not treat as a live contract. |
| [library-cli-convention.md](../001-ai-dev-factory/contracts/library-cli-convention.md) | Shared role-library CLI convention (JSON + human output, meaningful exit codes), referenced unchanged. |

## Key contract decisions

- **Entry** is a folder name, not a factory `spec_version_id`.
- **Assessment** is imported from `plan.md`, not re-derived only from `spec.md` (FR-004).
- **Requirements** are never re-derived or re-clarified inside the factory (FR-005).
- **Removal** of `spec-run`/`spec-workflow` from the required path (FR-006).
- **Normalization** of `tasks.md` file paths, excluding absolute/host paths (FR-008).
