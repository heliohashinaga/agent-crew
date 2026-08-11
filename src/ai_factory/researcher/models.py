"""Data models for the ``researcher`` role (Library-First).

The researcher is a mono-capacity, fixed lookup role. Its core is
deterministic and network-free (``repo`` scope); the ``web`` scope
(Option D, multi-angle best-per-angle) is layered on injectable
collaborators (``LLMProvider`` / ``WebFetcher`` / ``ContentFetcher``).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchSource(BaseModel):
    """A single sourced pointer returned by a lookup.

    For ``repo`` scope ``path`` is a file path and ``lines`` may carry a
    line-range like ``"14-40"``; for ``web`` scope ``path`` is a URL.
    """

    path: str
    lines: str | None = None
    snippet: str | None = None
    truncated: bool = False


class ResearchResult(BaseModel):
    """The payload returned by :func:`ai_factory.researcher.agent.lookup`.

    ``summary`` is a concise prose synthesis that fits the invoking role's
    context window and never contains a verbatim full-file dump (FR-002).
    ``tokens`` / ``cost_usd`` / ``latency_s`` are post-run telemetry fields
    (observability), not cost/limit configuration.
    """

    role: str = "researcher"
    query: str = ""
    summary: str = ""
    sources: list[ResearchSource] = Field(default_factory=list)
    scopes_used: list[str] = Field(default_factory=lambda: ["repo"])

    # Telemetry (post-run observability; not a budget).
    tokens: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0
