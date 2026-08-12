"""T024 — the shared live provider wired into the researcher web scope (FR-007).

The ``web`` scope takes an injected ``LLMProvider``; this test verifies the
call-site seam that supplies the registered ``openai-compatible`` provider:

- Without credentials → falls back to ``FakeProvider`` (US1/scenario 2, US3).
- Injected with a stubbed ``openai-compatible`` transport → a ``web`` lookup
  returns an ``LLMResult``-summarized ``ResearchResult`` with **no network**.
"""

from __future__ import annotations

import pytest

from ai_factory.researcher.agent import ResearcherWebError
from ai_factory.researcher.models import ResearchResult
from ai_factory.researcher.provider import (
    build_researcher_llm,
    run_web_lookup,
)
from ai_factory.researcher.web import ContentFetcher, WebFetcher
from ai_factory.shared.llm.provider import (
    FakeProvider,
    LLMMessage,
    LLMProvider,
    LLMResult,
)


class FakeWebFetcher(WebFetcher):
    def query(self, angle: str) -> list[str]:
        return ["https://docs.example.com/passwords.html"]


class FakeContentFetcher(ContentFetcher):
    def fetch(self, url: str) -> str:
        return "Salt the password hashes before storage; use bcrypt."


class _RecordingLive(LLMProvider):
    """A stub that mimics an 'openai-compatible' transport (no network)."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def complete(self, messages: list[LLMMessage], **kwargs) -> LLMResult:  # type: ignore[override]
        self.calls.append({"model": kwargs.get("model")})
        return LLMResult(
            content="live web summary",
            model=str(kwargs.get("model", "opencode-go/deepseek-v4-flash")),
            tokens_in=5,
            tokens_out=6,
        )


class TestFallbackToFake:
    """US1/scenario 2 — no credentials never leaks or goes live."""

    def test_no_creds_returns_fake_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for name in ("OPENCODE_GO_API_KEY", "OPENROUTER_API_KEY", "AI_FACTORY_LIVE"):
            monkeypatch.delenv(name, raising=False)
        provider = build_researcher_llm()
        assert isinstance(provider, FakeProvider)

    def test_creds_without_optin_still_fake(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AI_FACTORY_LIVE", raising=False)
        monkeypatch.setenv("OPENCODE_GO_API_KEY", "sk-present")
        provider = build_researcher_llm()
        assert isinstance(provider, FakeProvider)


class TestLiveProvider:
    """T024 — injected live provider drives a web lookup with no network."""

    def test_web_lookup_uses_injected_live_provider(self) -> None:
        rec = _RecordingLive()
        result = run_web_lookup(
            "password hashing best practice",
            fetcher=FakeWebFetcher(),
            content_fetcher=FakeContentFetcher(),
            provider=rec,
        )
        assert isinstance(result, ResearchResult)
        assert result.scopes_used == ["web"]
        assert result.summary == "live web summary"
        assert rec.calls, "the injected live provider must be called"

    def test_explicit_live_returns_openai_compatible_class(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # live=True + creds → the registered openai-compatible provider class.
        monkeypatch.setenv("AI_FACTORY_LIVE", "1")
        monkeypatch.setenv("OPENCODE_GO_API_KEY", "sk-present")
        from ai_factory.shared.llm.openai_compatible import OpenAICompatibleProvider

        provider = build_researcher_llm(live=True)
        assert isinstance(provider, OpenAICompatibleProvider)

    def test_web_lookup_no_candidates_raises(self) -> None:
        class NoResultsFetcher(WebFetcher):
            def query(self, angle: str) -> list[str]:
                return []

        with pytest.raises(ResearcherWebError):
            run_web_lookup(
                "nothing",
                fetcher=NoResultsFetcher(),
                content_fetcher=FakeContentFetcher(),
                provider=_RecordingLive(),
            )
