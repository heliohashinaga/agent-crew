"""Tests for the git-host client abstraction (T061, FR-012/FR-022).

The factory opens a PR via a pluggable git-host client — never auto-merges
into main (FR-012). A fake host provides deterministic results; the GitHub
adapter loads credentials ONLY from env/secret store (FR-018, FR-022).
"""

from __future__ import annotations

import pytest

from ai_factory.shared.git_host.client import (
    FakeGitHost,
    PullRequest,
    create_git_host,
)


def test_fake_host_opens_pr() -> None:
    host = FakeGitHost()
    pr = host.open_pr(title="feat: x", body="body", head="feature/x", base="main")
    assert isinstance(pr, PullRequest)
    assert pr.url.startswith("http")
    assert pr.number == 1


def test_fake_host_tracks_state() -> None:
    host = FakeGitHost()
    pr = host.open_pr(title="t", body="b", head="feature/x", base="main")
    assert host.last_pr.number == pr.number
    assert pr.head == "feature/x"
    assert pr.base == "main"


def test_no_auto_merge_capability() -> None:
    """FR-012: the factory must not auto-merge to main."""
    assert not hasattr(FakeGitHost(), "merge")
    assert not hasattr(create_git_host("fake"), "merge")


def test_create_git_host_fake() -> None:
    host = create_git_host("fake")
    assert isinstance(host, FakeGitHost)


def test_create_git_host_unknown_raises() -> None:
    with pytest.raises(ValueError):
        create_git_host("weird")


def test_github_adapter_requires_credentials(monkeypatch) -> None:
    """FR-018/FR-022: GitHub adapter creds come from env/secret store only."""
    from ai_factory.shared.git_host.client import GitHubAdapter

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
        GitHubAdapter(repo="a/b")


def test_github_adapter_accepts_env_token(monkeypatch) -> None:
    from ai_factory.shared.git_host.client import GitHubAdapter

    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token_123")
    adapter = GitHubAdapter(repo="a/b")
    assert adapter.token == "ghp_test_token_123"
