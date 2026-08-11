"""Folder resolution and artifact validation (002-folder-dev-run, T004/T005).

Resolves a speckit spec folder by name under ``specs/`` and validates that the
required artifacts (``spec.md``, ``plan.md``, ``tasks.md``) are present before
any workflow runs. Missing artifacts raise a fast-fail error (FR-007): the
factory never auto-generates or re-derives missing artifacts — external speckit
``plan``/``tasks`` skills bootstrap them (FR-005). Purely deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_ARTIFACTS = ("spec.md", "plan.md", "tasks.md")
OPTIONAL_ARTIFACTS = ("data-model.md",)


class FolderResolutionError(Exception):
    """Raised when a folder cannot be resolved for any reason."""


class MissingArtifactError(FolderResolutionError):
    """Raised when a required artifact is absent from a resolved folder."""

    def __init__(self, folder: Path, missing: list[str]) -> None:
        self.folder = folder
        self.missing = missing
        joined = ", ".join(missing)
        super().__init__(
            f"Folder '{folder.name}' is missing required artifact(s): {joined}. "
            "The factory does not generate missing artifacts — run the external "
            "speckit `plan`/`tasks` skills first (FR-007)."
        )


@dataclass(frozen=True)
class ResolvedFolder:
    """A validated speckit folder ready for parsing."""

    name: str
    path: Path
    artifacts: tuple[str, ...] = field(default=("spec.md", "plan.md", "tasks.md"))


def _find_specs_root(cwd: Path) -> Path:
    """Return the nearest ``specs/`` directory by climbing the tree."""
    cur = cwd
    while True:
        candidate = cur / "specs"
        if candidate.is_dir():
            return candidate
        if cur.parent == cur:
            return cwd / "specs"
        cur = cur.parent


def resolve_folder(
    name: str,
    *,
    specs_dir: str | Path | None = None,
    cwd: Path | None = None,
) -> ResolvedFolder:
    """Resolve ``name`` under ``specs/`` and validate its required artifacts.

    Climb the directory tree from ``cwd`` looking for ``specs/`` unless
    ``specs_dir`` is given explicitly. Raises :class:`FolderResolutionError`
    when the folder is missing, and :class:`MissingArtifactError` when one of
    the required artifacts is absent.
    """
    cwd = cwd or Path.cwd()
    specs_root = (
        _find_specs_root(cwd) if specs_dir is None else Path(specs_dir)
    )

    folder = specs_root / name
    if not folder.is_dir():
        raise FolderResolutionError(
            f"Spec folder '{name}' not found under {specs_root}"
        )

    validate_artifacts(folder)
    return ResolvedFolder(name=name, path=folder)


def validate_artifacts(folder: Path) -> None:
    """Assert all required artifacts exist; raise :class:`MissingArtifactError`."""
    missing = [a for a in REQUIRED_ARTIFACTS if not (Path(folder) / a).is_file()]
    if missing:
        raise MissingArtifactError(Path(folder), missing)


__all__ = [
    "FolderResolutionError",
    "MissingArtifactError",
    "ResolvedFolder",
    "REQUIRED_ARTIFACTS",
    "resolve_folder",
    "validate_artifacts",
]
