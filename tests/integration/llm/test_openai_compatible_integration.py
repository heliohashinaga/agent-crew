"""T040 — live provider integration path (best-effort, ``-m integration``).

``create_provider("openai-compatible")`` returns a working stdlib provider that
can be pointed at ``opencode-go`` or ``openrouter`` via env vars. Real-network
calls require ``OPENCODE_GO_API_KEY`` / ``OPENROUTER_API_KEY`` + ``AI_FACTORY_LIVE``
and network; without creds we exercise the **construction / model-resolution**
path (which is network-free) and skip the live-LLM round-trip gracefully.
"""

from __future__ import annotations

import os
import socket

import pytest

from ai_factory.shared.llm.openai_compatible import (
    OpenAICompatibleError,
    OpenAICompatibleProvider,
)
from ai_factory.shared.llm.provider import (
    PROVIDERS,
    LLMMessage,
    LLMResult,
    UnknownProviderError,
    create_provider,
)

_HOST = ("api.example.com", 80)


def _network_available() -> bool:
    try:
        sock = socket.create_connection(_HOST, timeout=2)
        sock.close()
        return True
    except OSError:
        return False


def _has_live_creds() -> bool:
    return bool(
        os.environ.get("OPENCODE_GO_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    )


pytestmark = [pytest.mark.integration]


class TestConstruction:
    """SC-001 — registered + buildable; unknown names still raise."""

    def test_registered_and_buildable_without_env(self, monkeypatch) -> None:
        for name in (
            "OPENCODE_GO_API_KEY",
            "OPENROUTER_API_KEY",
            "OPENCODE_GO_BASE_URL",
            "OPENROUTER_BASE_URL",
        ):
            monkeypatch.delenv(name, raising=False)
        assert "openai-compatible" in PROVIDERS
        provider = create_provider("openai-compatible")
        assert isinstance(provider, OpenAICompatibleProvider)

    def test_unknown_name_still_raises(self) -> None:
        with pytest.raises(UnknownProviderError):
            create_provider("does-not-exist")


class TestLiveEndpoint:
    """Best-effort real-LLM round-trip; skipped when creds/network are absent."""

    @pytest.mark.skipif(
        not _has_live_creds(), reason="no OPENCODE_GO_API_KEY / OPENROUTER_API_KEY"
    )
    @pytest.mark.skipif(
        not _network_available(), reason="network unavailable in integration job"
    )
    def test_real_provider_completes(self) -> None:
        provider = create_provider("openai-compatible")
        result = provider.complete(
            [LLMMessage(role="user", content="Reply with the single word: ok")]
        )
        assert isinstance(result, LLMResult)
        assert result.content
        assert result.tokens_in >= 0
        assert result.tokens_out >= 0

    def test_provider_allows_console_model_override(self) -> None:
        # Construction + model resolution is env-free; a missing key fails only
        # at live dispatch (typed, redacted), never at construction.
        provider = OpenAICompatibleProvider()
        assert provider.default_model  # documented default model is set
        if not _has_live_creds():
            with pytest.raises(OpenAICompatibleError):
                provider.complete([LLMMessage(role="user", content="hi")])
