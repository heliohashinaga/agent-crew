"""Unit tests for SpecSource resolution (T018/T019, FR-011/012)."""

import pytest

from ai_factory.shared.folder_adapter.spec_source import (
    SpecSource,
    SpecSourceError,
    resolve_path_for_source,
)


def test_local_default() -> None:
    s = SpecSource.from_arg("full")
    assert s.origin == "local"
    assert s.name == "full"


def test_path_origin() -> None:
    s = SpecSource.from_arg("path:/tmp/myfolder")
    assert s.origin == "path"
    assert s.name == "/tmp/myfolder"


def test_git_with_branch() -> None:
    s = SpecSource.from_arg("git:https://github.com/acme/repo.git#dev")
    assert s.origin == "git"
    assert s.branch == "dev"
    assert s.name == "repo"  # slug from URL


def test_git_default_branch() -> None:
    s = SpecSource.from_arg("git:https://github.com/acme/repo")
    assert s.origin == "git"
    assert s.branch == "main"


def test_git_short_spec() -> None:
    s = SpecSource.from_arg("git@github.com:org/project.git#main")
    assert s.origin == "git"


def test_git_resolve_requires_clone() -> None:
    s = SpecSource.from_arg("git:https://github.com/acme/repo")
    with pytest.raises(SpecSourceError):
        resolve_path_for_source(s)


def test_local_path_resolves(tmp_path) -> None:
    folder = tmp_path / "x"
    folder.mkdir()
    s = SpecSource.from_arg(f"path:{folder}")
    p = resolve_path_for_source(s, specs_root=tmp_path / "specs")
    assert p.resolve() == folder.resolve()
