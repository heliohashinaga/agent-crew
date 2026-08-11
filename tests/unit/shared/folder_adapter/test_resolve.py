"""Unit tests for folder resolution & artifact validation (T004, FR-001/002/007)."""

from pathlib import Path

import pytest

from ai_factory.shared.folder_adapter.resolve import (
    FolderResolutionError,
    MissingArtifactError,
    resolve_folder,
)


def _write(root: Path, folder: str, files: dict[str, str]) -> Path:
    d = root / "specs" / folder
    for rel, content in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return d


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path


def test_resolve_full_folder(root: Path) -> None:
    _write(
        root,
        "full",
        {
            "spec.md": "# Spec\nFR-001: x\n",
            "plan.md": "# Plan\n## Tech Stack\n",
            "tasks.md": "# Tasks\n1. [ ] T001 Import.\n",
        },
    )
    resolved = resolve_folder("full", specs_dir=root / "specs")
    assert resolved.name == "full"
    assert resolved.path.is_dir()
    assert "spec.md" in resolved.artifacts


def test_missing_folder_raises(root: Path) -> None:
    with pytest.raises(FolderResolutionError):
        resolve_folder("does-not-exist", specs_dir=root / "specs")


def test_missing_required_artifact_raises(root: Path) -> None:
    _write(root, "broken", {"spec.md": "# Spec\n"})
    with pytest.raises(MissingArtifactError) as exc:
        resolve_folder("broken", specs_dir=root / "specs")
    assert "plan.md" in exc.value.missing
    assert "tasks.md" in exc.value.missing


def test_optional_artifacts_not_required(root: Path) -> None:
    _write(
        root,
        "minimal",
        {
            "spec.md": "# Spec\n",
            "plan.md": "# Plan\n",
            "tasks.md": "# Tasks\n",
        },
    )
    resolved = resolve_folder("minimal", specs_dir=root / "specs")
    assert resolved.name == "minimal"


def test_finds_specs_root_by_climbing(root: Path) -> None:
    # Create specs under root, then resolve from a deeply nested cwd.
    _write(
        root,
        "nested",
        {
            "spec.md": "# Spec\n",
            "plan.md": "# Plan\n",
            "tasks.md": "# Tasks\n",
        },
    )
    deep = root / "a" / "b" / "c"
    deep.mkdir(parents=True, exist_ok=True)
    resolved = resolve_folder("nested", cwd=deep)
    assert resolved.path.is_dir()


def test_missing_artifact_error_message_mentions_external_skills(root: Path) -> None:
    _write(root, "empty", {"spec.md": "# Spec\n"})
    with pytest.raises(MissingArtifactError) as exc:
        resolve_folder("empty", specs_dir=root / "specs")
    assert "speckit" in str(exc.value)
