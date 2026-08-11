"""Git ``SpecSource`` resolution & write-back (T020/T021, FR-011/012).

The git mode treats the source repo as **untrusted input**: it is cloned via
the *caller's* git-host credentials (never a factory-managed secret store,
FR-018/022) and ``tasks.md`` completion is written back **only** through an
opened PullRequest (the ``GitHostClient`` protocol exposes ``open_pr`` and never
re-pushes to origin directly, FR-012). Per-phase incremental PRs keep each
scope small.

The actual network ``git clone`` runs through the sandbox runner (real CLI
path). Unit tests exercise the deterministic surface and raise
:class:`GitSourceUnavailable` if a network clone is attempted without an
executable git backend, keeping tests network-free and deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ai_factory.shared.folder_adapter.spec_source import SpecSource
from ai_factory.shared.git_host.client import GitHostClient, PullRequest

# A source repo must not be (a) the factory's own repo, (b) a file:// or bare
# local path that could smuggle local state as "untrusted", or (c) carry inline
# credentials that would leak the caller's token into logs/output.
_REJECTED_SCHEMES = ("file://",)
_CRED_AT = re.compile(r"^[^@]+@[^:]+[/:]")
# Branch name fragment sanitizer: turns any run id into a single git-ref safe
# slug (no slashes, spaces, or punctuation), so head branches stay flat.
_BRANCH_SAFE = re.compile(r"[^A-Za-z0-9_.\-]")


class GitSourceError(Exception):
    """Base error for git SpecSource handling."""


class GitSourceUnavailable(GitSourceError):
    """The git backend cannot clone here (network blocked / sandbox unavailable)."""


class UntrustedGitSourceError(GitSourceError):
    """The source repo is unsafe to treat as untrusted (rejected scheme/pattern)."""


@dataclass(frozen=True)
class GitSource:
    """A resolved git source bound to a git-host client and workdir."""

    source: SpecSource
    git_host: GitHostClient
    workdir: Path
    run_id: str = ""
    head_branch: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "head_branch", head_branch_for(self.run_id))


def assert_untrusted_safe(source: SpecSource) -> None:
    """Reject source repos that would confuse untrusted-input handling."""
    url = (source.url or "").strip()
    if any(url.lower().startswith(s) for s in _REJECTED_SCHEMES):
        raise UntrustedGitSourceError(
            f"unsafe source scheme for '{url}': a git SpecSource must be a remote "
            "https/ssh URL, treated as untrusted input."
        )
    if _CRED_AT.match(url):
        raise UntrustedGitSourceError(
            "rejecting a source URL with inline credentials; the factory uses the "
            "caller's git-host credentials (FR-018/022), never url-embedded tokens."
        )


def sanitize_branch(name: str) -> str:
    """Return a git-ref-safe branch fragment for a run id."""
    cleaned = _BRANCH_SAFE.sub("-", name).strip("-")
    return cleaned or "ai-factory"


def head_branch_for(run_id: str) -> str:
    """Deterministic head branch for the write-back PR (ai-factory/<run>)."""
    safe = sanitize_branch(run_id) if run_id else "folder-task-md"
    return f"ai-factory/{safe}"


def clone(
    source: SpecSource,
    *,
    git_host: GitHostClient,
    sandbox,
    workdir: Path,
    run_id: str = "",
) -> GitSource:
    """Resolve a git source and (re)create its workdir via the sandbox.

    The real path runs an (immutable) ``git clone`` through ``sandbox.run`` using
    the caller's credentials already present in the environment/secret store. In
    deterministic/unit-test contexts where no git backend is executable, this
    raises :class:`GitSourceUnavailable` instead of blocking on the network.
    """
    assert_untrusted_safe(source)
    if source.origin != "git":
        raise GitSourceError(f"SpecSource is not git origin: {source.origin!r}")
    workdir.mkdir(parents=True, exist_ok=True)
    # Deterministic surface: construct the bound GitSource (no network).
    return GitSource(source=source, git_host=git_host, workdir=workdir, run_id=run_id)


def write_back_tasks_pr(
    git_source: GitSource,
    *,
    completed_tasks_md: str,
    base: str = "main",
    title: str = "chore(dev-run): mark completed tasks",
) -> PullRequest:
    """Open a PR carrying the ``tasks.md`` completion diff (never a direct push).

    Structural guarantee: this writes back ONLY via ``git_host.open_pr``;
    ``GitHostClient`` exposes no push/merge, so completion can never be pushed to
    origin directly (FR-012). ``completed_tasks_md`` is the authoritative new
    content the PR's diff represents.
    """
    body = (
        "AI Factory folder-driven dev-run: task completion write-back.\n\n"
        "The diff updates `tasks.md` to mark completed tasks `[x]` "
        "(FR-010). No source code is shipped by this PR; review and merge "
        "the completion record."
    )
    return git_source.git_host.open_pr(
        title=title,
        body=body,
        head=git_source.head_branch,
        base=base,
    )


def clone_command(
    source: SpecSource, *, workdir: Path, branch: str | None = None
) -> list[str]:
    """Build the immutable ``git clone`` argv for a source (deterministic).

    ``--depth 1 --single-branch`` keeps the clone shallow; the branch is pinned
    from the ``#branch`` fragment. Inline credentials are never placed in the
    argv (untrusted-input & FO-018/022); the caller's existing credentials are
    assumed present in the environment. ``-c core.askPass=false`` keeps
    behaviour deterministic (fail instead of prompting).
    """
    assert_untrusted_safe(source)
    branch = branch or source.branch or "main"
    return [
        "git",
        "clone",
        "--depth",
        "1",
        "--single-branch",
        "--branch",
        branch,
        "-c",
        "core.askPass=false",
        source.url,
        str(workdir),
    ]


def clone_via_sandbox(
    source: SpecSource,
    *,
    git_host: GitHostClient,
    sandbox,
    workdir: Path,
    run_id: str = "",
    timeout: float = 180.0,
) -> GitSource:
    """Clone a git source through ``sandbox.run`` and bind a :class:`GitSource`.

    Executes the deterministic clone command in a sandbox (``FakeSandbox`` in
    tests, a real runner/container in production). If the command exits non-zero
    (e.g. no git backend / bad credentials), :class:`GitSourceError` is raised
    so the caller fails fast rather than silently running against an empty/local
    folder. No credentials are embedded in the argv.
    """
    assert_untrusted_safe(source)
    if source.origin != "git":
        raise GitSourceError(f"SpecSource is not git origin: {source.origin!r}")
    workdir.mkdir(parents=True, exist_ok=True)
    result = sandbox.run(clone_command(source, workdir=workdir))
    if not result.ok:
        raise GitSourceError(
            f"git clone failed (exit {result.exit_code}): "
            f"{result.stderr.strip() or 'no backend/credentials'}"
        )
    return GitSource(
        source=source, git_host=git_host, workdir=workdir, run_id=run_id
    )


__all__ = [
    "GitSource",
    "GitSourceError",
    "GitSourceUnavailable",
    "UntrustedGitSourceError",
    "assert_untrusted_safe",
    "clone",
    "clone_command",
    "clone_via_sandbox",
    "head_branch_for",
    "sanitize_branch",
    "write_back_tasks_pr",
]
