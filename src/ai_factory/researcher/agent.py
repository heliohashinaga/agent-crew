"""Deterministic ``repo``-scope lookup core for the ``researcher`` role.

The ``repo`` core is network-free and deterministic (Library-First, mirrors
``spec_agent.agent.draft_spec``). It scans text files under the given roots,
matches a tokenized query against file paths/names and (for small files) head
contents, and returns a concise ``ResearchResult``.

The ``web`` scope (Option D, multi-angle best-per-angle) is layered on
injectable collaborators (``llm`` / ``fetcher`` / ``content_fetcher``) and is
implemented in :mod:`ai_factory.researcher.web`. Requesting it without the
required collaborators raises :class:`ResearcherWebError`.
"""

from __future__ import annotations

import os
import re

from ai_factory.researcher.models import ResearchResult, ResearchSource

# Noise directories excluded from a deterministic repo scan.
_NOISE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
}

# Code extensions receive priority: a single term match (path or content)
# is enough for code, while docs need a stronger signal (see _scan_repo).
_CODE_EXTS = {
    ".py", ".pyi", ".java", ".ts", ".tsx", ".js", ".jsx", ".go",
    ".rs", ".c", ".cpp", ".h", ".hpp", ".sh", ".rb", ".kt", ".swift",
    ".sql", ".vue",
}


def _is_code(path: str) -> bool:
    return any(path.endswith(ext) for ext in _CODE_EXTS)


# Text extensions we index for deterministic matching.
_TEXT_EXTS = {".py", ".md", ".txt", ".toml", ".yaml", ".yml", ".json", ".cfg", ".ini"}

# Bound per-file indexing to keep the result small (conciseness invariant,
# not a model/cost budget).
_MAX_PER_FILE_BYTES = 4096


class ResearcherWebError(ValueError):
    """Raised when the ``web`` scope is requested without the required
    injectable collaborators (or the real web path is unavailable)."""


def _is_text(path: str) -> bool:
    return any(path.endswith(ext) for ext in _TEXT_EXTS)


def _read_head(path: str, limit: int = _MAX_PER_FILE_BYTES) -> str:
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read(limit)
    except (OSError, UnicodeDecodeError):
        return ""


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


def _needs_scan(path: str) -> bool:
    base = os.path.basename(path)
    return not base.startswith((".", "~", "#")) and not base.endswith("~")


def _scan_repo(root: str, query_terms: set[str]) -> list[ResearchSource]:
    sources: list[ResearchSource] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _NOISE_DIRS]
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            if not _is_text(full) or not _needs_scan(full):
                continue
            path_terms = _tokenize(full)
            head = _read_head(full)
            head_terms = _tokenize(head) if head else set()
            path_match = bool(query_terms & path_terms)
            content_hits = len(query_terms & head_terms)
            if _is_code(full):
                is_match = path_match or content_hits >= 1
            else:
                # Docs need a stronger signal: a term in the path, or at
                # least 2 distinct query terms in the content (avoid
                # surfacing incidental one-word mentions).
                is_match = path_match or content_hits >= 2
            if is_match:
                truncated = len(head.encode("utf-8")) >= _MAX_PER_FILE_BYTES
                rel = os.path.relpath(full, root)
                line_count = head.count("\n") or 1
                sources.append(
                    ResearchSource(
                        path=rel,
                        lines=f"1-{line_count}",
                        snippet=head[:200],
                        truncated=truncated,
                    )
                )
    return sources


def _build_summary(query: str, sources: list[ResearchSource]) -> str:
    if not sources:
        return ""
    parts = [f"Found {len(sources)} relevant file(s) for query '{query}':"]
    for src in sources:
        loc = f" ({src.lines.strip()})" if src.lines else ""
        tail = " [truncated]" if src.truncated else ""
        parts.append(f"- {src.path}{loc}{tail}")
    return "\n".join(parts)


def lookup(
    query: str,
    *,
    roots: list[str],
    scopes: list[str] | None = None,
    llm=None,
    fetcher=None,
    content_fetcher=None,
) -> ResearchResult:
    """Run a lookup against the given roots.

    Deterministic ``repo`` scope: scans text files under ``roots`` for a
    tokenized match and returns a ``ResearchResult`` with source pointers and a
    concise summary. ``scopes`` defaults to ``["repo"]``.
    """
    used_scopes = list(scopes) if scopes else ["repo"]

    if "web" in used_scopes and (llm is None or fetcher is None):
        raise ResearcherWebError(
            "web scope requires injected llm + fetcher (+ optional content_fetcher)"
        )

    if used_scopes == ["web"]:
        # Delegate entirely to the web core (Option D, best-per-angle).
        from ai_factory.researcher.web import web_lookup

        return web_lookup(
            query,
            llm=llm,  # type: ignore[arg-type]
            fetcher=fetcher,  # type: ignore[arg-type]
            content_fetcher=content_fetcher,  # type: ignore[arg-type]
        )

    if "web" in used_scopes:
        raise ResearcherWebError(
            "web scope cannot be combined with repo scope in a single lookup"
        )

    sources: list[ResearchSource] = []
    if "repo" in used_scopes:
        terms = _tokenize(query)
        if terms:  # empty query -> no sources, empty summary (FR-004)
            for root in roots:
                if os.path.isdir(root):
                    sources.extend(_scan_repo(root, terms))
            # De-dup by path, keep first occurrence.
            seen: set[str] = set()
            unique: list[ResearchSource] = []
            for src in sources:
                if src.path not in seen:
                    seen.add(src.path)
                    unique.append(src)
            sources = unique

    return ResearchResult(
        query=query,
        summary=_build_summary(query, sources),
        sources=sources,
        scopes_used=used_scopes,
    )
