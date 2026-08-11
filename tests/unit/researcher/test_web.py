"""Unit tests for the deterministic ``web`` core (T014, network-free).

The ``web`` scope runs multi-angle queries through injected collaborators
(``LLMProvider`` / ``WebFetcher`` / ``ContentFetcher``) with fakes so the
core is fully deterministic and never touches the network. On any fetch/LLM
failure it raises :class:`ResearcherWebError` (never silently empty).

Option D (multi-angle, best-per-angle): expand the query into 2-4 angles,
rank each angle's candidates by source quality via the LLM, fetch the winner's
content, and synthesize one concise summary capped by a context window.
"""

from __future__ import annotations

import logging

import pytest

from ai_factory.researcher.agent import ResearcherWebError
from ai_factory.researcher.models import ResearchResult
from ai_factory.researcher.web import ContentFetcher, WebFetcher, web_lookup
from ai_factory.shared.llm.provider import FakeProvider, LLMMessage, LLMProvider

logger = logging.getLogger(__name__)


class FakeWebFetcher(WebFetcher):
    """Deterministic candidate source for two angles."""

    def query(self, angle: str) -> list[str]:
        if "auth" in angle and "login" in angle:
            return ["https://docs.example.com/passwords.html"]
        return ["https://docs.example.com/security.html"]


class FakeContentFetcher(ContentFetcher):
    """Deterministic page content."""

    def fetch(self, url: str) -> str:
        return (
            "Salt the password hashes before storage; use a slow KDF such as "
            "bcrypt and compare using a constant-time function to avoid timing "
            "side-channels."
        )


def _run_web_lookup(query: str = "login authentication password") -> ResearchResult:
    return web_lookup(
        query,
        llm=FakeProvider(),
        fetcher=FakeWebFetcher(),
        content_fetcher=FakeContentFetcher(),
    )


def test_web_scope_returns_best_per_angle_url_sources() -> None:
    """scope=web yields URL sources (best-per-angle) + LLM-summarized summary."""
    res = _run_web_lookup()
    assert isinstance(res, ResearchResult)
    assert res.role == "researcher"
    assert res.scopes_used == ["web"]
    # At least one URL source surfaced (best-per-angle across 2-4 angles).
    assert res.sources
    assert all(s.path.startswith("https://") for s in res.sources)
    # A synthesized, concise summary was produced by the LLM summarizer.
    assert res.summary


def test_web_scope_multi_angle_calls_fetcher_per_angle() -> None:
    fetcher = FakeWebFetcher()
    content_fetcher = FakeContentFetcher()
    calls: list[str] = []

    class RecordingFetcher(WebFetcher):
        def query(self, angle: str) -> list[str]:
            calls.append(angle)
            return fetcher.query(angle)

    class RecordingContent(ContentFetcher):
        def fetch(self, url: str) -> str:
            return content_fetcher.fetch(url)

    web_lookup(
        "login authentication password",
        llm=FakeProvider(),
        fetcher=RecordingFetcher(),
        content_fetcher=RecordingContent(),
    )
    # Multi-angle expansion: between 2 and 4 distinct angles, each queried.
    assert 2 <= len(calls) <= 4


def test_web_scope_empty_angle_candidates_raises() -> None:
    """A fetch returning no candidates is a failure, never silently empty."""

    class NoResultsFetcher(WebFetcher):
        def query(self, angle: str) -> list[str]:
            return []

    with pytest.raises(ResearcherWebError):
        web_lookup(
            "some query",
            llm=FakeProvider(),
            fetcher=NoResultsFetcher(),
            content_fetcher=FakeContentFetcher(),
        )


def test_web_scope_content_fetch_failure_raises() -> None:
    """A content-fetch failure raises ResearcherWebError (never silent empty)."""

    class FailingContent(ContentFetcher):
        def fetch(self, url: str) -> str:
            raise ConnectionError("unreachable")

    with pytest.raises(ResearcherWebError):
        web_lookup(
            "login",
            llm=FakeProvider(),
            fetcher=FakeWebFetcher(),
            content_fetcher=FailingContent(),
        )


def test_web_scope_llm_failure_raises() -> None:
    """An LLM failure during ranking/synthesis raises ResearcherWebError."""

    class ExplodingProvider(LLMProvider):
        model_name = "exploding"

        def complete(  # pragma: no cover
            self, messages: list[LLMMessage], **kwargs
        ) -> object:
            raise RuntimeError("provider down")

        def close(self) -> None:
            return None

    with pytest.raises(ResearcherWebError):
        web_lookup(
            "login",
            llm=ExplodingProvider(),
            fetcher=FakeWebFetcher(),
            content_fetcher=FakeContentFetcher(),
        )


def test_web_scope_respects_context_window_cap() -> None:
    """The summarizer is capped by the configurable context-window limit."""

    class BigContent(ContentFetcher):
        def fetch(self, url: str) -> str:
            return "word " * 10_000

    # A tiny context window must not blow up; the summary stays concise.
    res = web_lookup(
        "login",
        llm=FakeProvider(),
        fetcher=FakeWebFetcher(),
        content_fetcher=BigContent(),
        context_window=256,
    )
    assert res.summary
    assert len(res.summary) <= 2048
