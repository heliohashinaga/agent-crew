"""Unit tests for git SpecSource resolution & write-back (T020/T021, FR-011/012/018)."""

import pytest

from ai_factory.shared.folder_adapter.git_source import (
    GitSource,
    GitSourceError,
    UntrustedGitSourceError,
    assert_untrusted_safe,
    clone,
    head_branch_for,
    sanitize_branch,
    write_back_tasks_pr,
)
from ai_factory.shared.folder_adapter.spec_source import SpecSource
from ai_factory.shared.git_host.client import FakeGitHost


def _git_source(tmp_path) -> GitSource:
    return clone(
        SpecSource.from_arg("git:https://github.com/acme/repo.git#main"),
        git_host=FakeGitHost(),
        sandbox=None,  # deterministic: clone() never executes the backend here
        workdir=tmp_path,
        run_id="run-1",
    )


def test_head_branch_is_deterministic_and_namespaced() -> None:
    assert head_branch_for("run-1") == "ai-factory/run-1"
    assert head_branch_for("run-1") == head_branch_for("run-1")
    assert head_branch_for("") == "ai-factory/folder-task-md"


def test_sanitize_branch_strips_bad_chars() -> None:
    assert sanitize_branch("run A/B#1") == "run-A-B-1"


def test_clone_binds_git_source(tmp_path) -> None:
    gs = _git_source(tmp_path)
    assert gs.source.origin == "git"
    assert gs.source.branch == "main"
    assert gs.head_branch.startswith("ai-factory/")


def test_clone_requires_git_origin(tmp_path) -> None:
    local = SpecSource(name="full", origin="local")
    with pytest.raises(GitSourceError):
        clone(
            local,
            git_host=FakeGitHost(),
            sandbox=None,
            workdir=tmp_path,
        )


def test_assert_untrusted_safe_rejects_inline_credentials() -> None:
    with pytest.raises(UntrustedGitSourceError):
        assert_untrusted_safe(
            SpecSource.from_arg("git:https://user:token@github.com/acme/repo")
        )


def test_assert_untrusted_safe_rejects_file_scheme() -> None:
    with pytest.raises(UntrustedGitSourceError):
        assert_untrusted_safe(SpecSource.from_arg("git:file:///tmp/local-repo"))


def test_write_back_uses_pr_not_direct_push(tmp_path) -> None:
    host = FakeGitHost()
    gs = _git_source(tmp_path)
    # Bind the same host so write-back uses it.
    gs = GitSource(
        source=gs.source, git_host=host, workdir=gs.workdir, run_id=gs.run_id
    )
    pr = write_back_tasks_pr(
        gs,
        completed_tasks_md="# Tasks\n- [x] T001 done\n",
        title="chore: complete",
    )
    # A PR was opened on the dedicated head branch (never a direct push).
    assert pr.number >= 1
    assert pr.head == gs.head_branch
    assert pr.base == "main"
    assert "tasks.md" in pr.title or "complete" in pr.title
