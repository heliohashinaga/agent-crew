"""SpecSource: folder resolution by origin (002-folder-dev-run, T018–T021, FR-011/012).

Resolves a speckit folder ``<name>`` by ``origin``:

* ``local``  — default, or ``path:<abs>``. Uses the nearest ``specs/<name>``
  (climbing the tree) and operates in-place.
* ``git``    — ``url#branch``. Treats the source repo as *untrusted input*:
  clones into a throwaway workdir, never pushes to origin directly, and writes
  back ``tasks.md`` completion only via an opened PullRequest (FR-012).

The implementation is pure and deterministic for classification; live git
clone/write-back happens through the git-host/sandbox layers in the CLI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

GIT_URL_RE = re.compile(r"^(?P<url>.+?)(?:#(?P<branch>[^#]+))?$")


class SpecSourceError(Exception):
    """Raised for malformed or unsupported SpecSource origins."""


@dataclass(frozen=True)
class SpecSource:
    """How a folder is sourced."""

    name: str
    origin: str = "local"
    url: str = ""
    branch: str = "main"

    @classmethod
    def from_arg(cls, value: str) -> SpecSource:
        """Parse a ``dev-run <folder>`` argument into a SpecSource."""
        if value.startswith("git:"):
            return cls.from_git(value[len("git:") :])
        if value.startswith("path:"):
            return cls(name=value[len("path:") :], origin="path")
        # Only treat as git when it is clearly a remote URL.
        is_url = bool(
            re.match(r"^(https?|ssh|git)://", value)
            or value.startswith("git@")
        )
        if is_url:
            return cls.from_git(value)
        # Default local: a bare folder name, or an existing path.
        return cls(name=value, origin="local")

    @classmethod
    def from_git(cls, spec: str) -> SpecSource:
        """Parse ``url#branch`` or bare URL into a git SpecSource."""
        m = GIT_URL_RE.match(spec)
        if not m or not m.group("url"):
            raise SpecSourceError(
                f"Malformed git source '{spec}'. Expected url#branch."
            )
        url = m.group("url").strip()
        branch = (m.group("branch") or "main").strip()
        if not branch:
            branch = "main"
        # Folder name derives from the repo slug for traceability.
        slug = url.rstrip("/").split("/")[-1]
        if slug.endswith(".git"):
            slug = slug[: -len(".git")]
        slug = re.sub(r"[^A-Za-z0-9_.-]", "_", slug)
        return SpecSource(name=slug or "repo", origin="git", url=url, branch=branch)


def resolve_path_for_source(source: SpecSource, specs_root: Path | None = None) -> Path:
    """Return the folder path for a local/path SpecSource."""
    if source.origin == "git":
        raise SpecSourceError("git SpecSource requires clone; use the CLI git adapter.")
    if source.origin == "path":
        p = Path(source.name)
        return p.resolve() if p.is_absolute() else (Path.cwd() / p).resolve()
    # local: nearest specs/<name>
    base = specs_root or Path.cwd() / "specs"
    return base / source.name


__all__ = ["SpecSource", "SpecSourceError", "resolve_path_for_source"]
