"""Tests for the pluggable LLM provider abstraction (T012, R5, FR-018).

The provider layer is network-free and deterministic: a fake provider stands
in for a live model. Credentials must load via the env/secret-store path
(FR-018) — the factory never embeds provider keys in committed config.
"""

from __future__ import annotations

import pytest

from ai_factory.shared.llm.provider import (
    LLMMessage,
    LLMProvider,
    LLMResult,
    UnknownProviderError,
    create_provider,
)


class _StubSecretSource:
    def __init__(self, data: dict[str, str]) -> None:
        self._data = data

    def get(self, name: str) -> str | None:
        return self._data.get(name)


def test_create_fake_provider() -> None:
    provider = create_provider("fake")
    assert isinstance(provider, LLMProvider)


def test_fake_provider_completes_deterministically() -> None:
    provider = create_provider("fake")
    result = provider.complete([LLMMessage(role="user", content="hello")])
    assert isinstance(result, LLMResult)
    assert result.content
    assert result.model == "fake"


def test_fake_provider_echoes_instruction_mode() -> None:
    provider = create_provider("fake")
    msgs = [
        LLMMessage(role="system", content="Say hi"),
        LLMMessage(role="user", content="go"),
    ]
    result = provider.complete(msgs, instruction="draft")
    assert result.content
    # Fake reflects the instruction so callers can assert routing happened.
    assert "draft" in result.content


def test_llm_result_tracks_tokens() -> None:
    # Fake provider should report token counts so telemetry (FR-016) has data.
    provider = create_provider("fake")
    result = provider.complete([LLMMessage(role="user", content="0123456789")])
    assert result.tokens_in >= 0
    assert result.tokens_out >= 0


def test_unknown_provider_raises() -> None:
    with pytest.raises(UnknownProviderError):
        create_provider("does-not-exist")


def test_register_custom_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    class Custom(LLMProvider):
        model_name = "custom"

        def complete(self, messages, **kwargs) -> LLMResult:  # noqa: D102
            return LLMResult(content="c", model="custom", tokens_in=1, tokens_out=1)

        def close(self) -> None:  # noqa: D102
            return None

    # The registry is a plain module dict reused across tests; this is safe.
    from ai_factory.shared.llm import provider as _mod

    monkeypatch.setitem(_mod.PROVIDERS, "custom", Custom)
    provider = create_provider("custom")
    assert provider.complete([]).content == "c"


def test_credentials_come_from_env_not_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-018: a provider's credential lookup uses the secret-store path."""
    from ai_factory.shared.llm.provider import _resolve_credential

    monkeypatch.setenv("LLM_DEMO_KEY", "sk-demo-123")
    assert _resolve_credential("LLM_DEMO_KEY") == "sk-demo-123"


def test_credentials_fallback_to_secret_source(monkeypatch: pytest.MonkeyPatch) -> None:
    from ai_factory.shared.llm.provider import _resolve_credential

    monkeypatch.delenv("LLM_DEMO_KEY", raising=False)
    assert (
        _resolve_credential(
            "LLM_DEMO_KEY", source=_StubSecretSource({"LLM_DEMO_KEY": "from-store"})
        )
        == "from-store"
    )
