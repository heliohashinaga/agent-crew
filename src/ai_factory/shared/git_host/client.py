"""Pluggable git-host client (T062, FR-012, FR-022).

The factory opens a pull request through a :class:`GitHostClient` — it never
auto-merges into main (FR-012), so the client contract exposes only
``open_pr`` (+ state). Credentials for live hosts load ONLY from the
environment or a secret store (FR-018, FR-022). :class:`FakeGitHost`
provides deterministic behavior for tests.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from ai_factory.shared.secrets.loader import SecretSource, load_credential


class PullRequest(BaseModel):
    """A merge-ready pull request (never auto-merged; FR-012)."""

    number: int
    title: str
    url: str = ""
    head: str = ""
    base: str = "main"


class GitHostClient(Protocol):
    """The git-host contract: open a reviewed, merge-ready PR."""

    def open_pr(
        self, *, title: str, body: str, head: str, base: str = "main"
    ) -> PullRequest:
        """Open a PR from ``head`` onto ``base``; return its reference."""
        ...


class FakeGitHost:
    """Deterministic git host returning synthetic PRs (tests/dry runs)."""

    _next_number = 0

    def __init__(self) -> None:
        self.last_pr: PullRequest | None = None

    def open_pr(
        self, *, title: str, body: str, head: str, base: str = "main"
    ) -> PullRequest:
        FakeGitHost._next_number += 1
        pr = PullRequest(
            number=FakeGitHost._next_number,
            title=title,
            url=f"https://fake-host.example/pr/{FakeGitHost._next_number}",
            head=head,
            base=base,
        )
        self.last_pr = pr
        return pr


class GitHubAdapter:
    """Real GitHub adapter. Credentials come from env/secret store (FR-018/022)."""

    def __init__(
        self,
        repo: str,
        *,
        source: SecretSource | None = None,
        base_url: str = "https://api.github.com",
    ) -> None:
        self.repo = repo
        self.base_url = base_url
        self.token = load_credential("GITHUB_TOKEN", source=source) or load_credential(
            "GH_TOKEN", source=source
        )
        if not self.token:
            raise RuntimeError(
                "GITHUB_TOKEN not found in environment or secret store (FR-022)"
            )

    def open_pr(
        self, *, title: str, body: str, head: str, base: str = "main"
    ) -> PullRequest:
        import json
        import urllib.error
        import urllib.request

        payload = json.dumps(
            {"title": title, "body": body, "head": head, "base": base}
        ).encode()
        req = urllib.request.Request(
            f"{self.base_url}/repos/{self.repo}/pulls",
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"GitHub API error {exc.code}: {exc.read().decode()[:300]}"
            ) from exc
        return PullRequest(
            number=int(data.get("number", 0)),
            title=data.get("title", title),
            url=data.get("html_url", ""),
            head=data.get("head", {}).get("ref", head),
            base=data.get("base", {}).get("ref", base),
        )


def create_git_host(provider: str, **kwargs) -> GitHostClient:
    """Instantiate a git host by name: ``fake`` (tests) or ``github``."""
    if provider == "fake":
        return FakeGitHost()
    if provider == "github":
        return GitHubAdapter(repo=kwargs["repo"], source=kwargs.get("source"))
    raise ValueError(f"unknown git host provider: {provider!r}")


__all__ = [
    "FakeGitHost",
    "GitHubAdapter",
    "GitHostClient",
    "PullRequest",
    "create_git_host",
]
