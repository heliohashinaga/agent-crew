"""Integration tests for the real network/LLM ``web`` path (T015).

These tests are gated ``-m integration`` and opt out of conftest's network
block. They exercise the real :class:`UrllibWebFetcher` +
:class:`UrllibContentFetcher` with a deterministic :class:`FakeProvider` as the
LLM (fake keeps the summarizer deterministic and offline-friendly). On offline
CI they **skip** rather than fail — the live path is best-effort by design.
"""

from __future__ import annotations

import socket

import pytest

from ai_factory.researcher.agent import ResearcherWebError
from ai_factory.researcher.models import ResearchResult
from ai_factory.researcher.web import (
    UrllibContentFetcher,
    UrllibWebFetcher,
    web_lookup,
)
from ai_factory.shared.llm.provider import FakeProvider

# A stable, fetchable page for best-effort real-path coverage.
_LIVE_FIXTURE_URL = "https://example.com/"
_OFFLINE_HOST = ("example.com", 80)


def _network_available() -> bool:
    try:
        sock = socket.create_connection(_OFFLINE_HOST, timeout=3)
        sock.close()
        return True
    except OSError:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _network_available(), reason="network unavailable; skipping real web path"
    ),
]


def test_real_web_scope_returns_url_sources_and_summary() -> None:
    res = web_lookup(
        "example domain",
        llm=FakeProvider(),
        fetcher=UrllibWebFetcher(endpoint=_LIVE_FIXTURE_URL),
        content_fetcher=UrllibContentFetcher(timeout_s=5),
    )
    assert isinstance(res, ResearchResult)
    assert res.scopes_used == ["web"]
    assert res.sources and all(s.path.startswith("https://") for s in res.sources)
    # A real fetch happened; the LLM synthesized a concise summary.
    assert "example" in res.summary.lower()


def test_real_content_fetcher_retrieves_readable_text() -> None:
    fetcher = UrllibContentFetcher(timeout_s=5)
    text = fetcher.fetch(_LIVE_FIXTURE_URL)
    assert text  # non-empty readable text fetched over the real network


def test_web_scope_unreachable_endpoint_raises_typed_error() -> None:
    """A real, unreachable endpoint surfaces as ResearcherWebError (non-empty)."""
    with pytest.raises(ResearcherWebError):
        web_lookup(
            "query",
            llm=FakeProvider(),
            fetcher=UrllibWebFetcher(endpoint="https://invalid.invalid/none"),
            content_fetcher=UrllibContentFetcher(timeout_s=2),
        )
