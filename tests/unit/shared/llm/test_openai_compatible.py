"""Tests for the OpenAI-compatible live provider (T002-T007, US1/US2, FR-018).

The provider uses only stdlib ``urllib`` and reads all credentials via the
env/secret-store path (FR-018). Network access is never required in unit
tests: ``urllib.request.urlopen`` is frozen with canned responses. Secrets are
redacted in every error surface (SC-005).
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

import pytest

from ai_factory.shared.llm.openai_compatible import (
    OpenAICompatibleError,
    OpenAICompatibleProvider,
)
from ai_factory.shared.llm.provider import (
    PROVIDERS,
    LLMMessage,
    LLMProvider,
    LLMResult,
    UnknownProviderError,
    create_provider,
)
from ai_factory.shared.secrets.loader import REDACTED


class _StubSecretSource:
    """In-memory secret source for credential-resolution tests."""

    def __init__(self, data: dict[str, str]) -> None:
        self._data = data

    def get(self, name: str) -> str | None:
        return self._data.get(name)


def _canned_response(
    content: str = "ok", model: str = "opencode-go/deepseek-v4-flash"
) -> bytes:
    body = {
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7},
        "model": model,
    }
    return json.dumps(body).encode("utf-8")


def _freeze_urlopen(monkeypatch: pytest.MonkeyPatch, payload: bytes) -> dict[str, Any]:
    """Replace ``urllib.request.urlopen`` and record the posted request."""
    recorded: dict[str, Any] = {}

    class _FakeResponse:
        def __init__(self, data: bytes) -> None:
            self._data = data

        def read(self) -> bytes:
            return self._data

        def __enter__(self) -> _FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def _fake_urlopen(request: urllib.request.Request, *args, **kwargs):  # type: ignore[no-untyped-def]
        recorded["url"] = request.full_url
        recorded["method"] = request.get_method()
        recorded["headers"] = dict(request.headers)
        recorded["body"] = request.data.decode("utf-8") if request.data else None
        return _FakeResponse(payload)

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    return recorded


def test_module_imports_and_scaffold() -> None:
    """T002 — the module imports and exposes the provider class."""
    import ai_factory.shared.llm.openai_compatible  # noqa: F401

    assert hasattr(OpenAICompatibleProvider, "complete")


def test_registered_in_registry_and_buildable_without_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T003 — registered as ``openai-compatible``; safe to build with no env."""
    for name in ("OPENCODE_GO_API_KEY", "OPENROUTER_API_KEY",
                 "OPENCODE_GO_BASE_URL", "OPENROUTER_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    assert "openai-compatible" in PROVIDERS
    provider = create_provider("openai-compatible")
    assert isinstance(provider, LLMProvider)
    assert isinstance(provider, OpenAICompatibleProvider)


def test_unknown_name_still_raises() -> None:
    """T003 — an unregistered name still raises the existing typed error."""
    with pytest.raises(UnknownProviderError):
        create_provider("definitely-not-a-provider")


def test_resolves_creds_from_secret_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """T004 — keys/base URLs resolve via a supplied secret source (FR-018)."""
    source = _StubSecretSource(
        {
            "OPENCODE_GO_API_KEY": "sk-secret",
            "OPENCODE_GO_BASE_URL": "https://api.opencode-go.example",
        }
    )
    provider = OpenAICompatibleProvider(credentials=source)
    assert provider.api_key == "sk-secret"
    assert "api.opencode-go.example" in provider.base_url


def test_missing_key_fails_fast_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    """T004 — a missing key fails fast with a clear typed error, no hang.

    Construction is always safe (no env required, T003); the typed error is
    raised when a live call needs the missing credential.
    """
    monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    provider = OpenAICompatibleProvider()
    with pytest.raises(OpenAICompatibleError):
        provider.complete([LLMMessage(role="user", content="q")])


def test_complete_posts_and_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    """T005 — POST /chat/completions, parse body into an LLMResult."""
    recorded = _freeze_urlopen(
        monkeypatch,
        _canned_response(content="hi", model="opencode-go/deepseek-v4-flash"),
    )
    provider = OpenAICompatibleProvider(
        credentials=_StubSecretSource(
            {"OPENCODE_GO_API_KEY": "k", "OPENCODE_GO_BASE_URL": "https://api.example"}
        ),
    )
    result = provider.complete(
        [
            LLMMessage(role="system", content="be brief"),
            LLMMessage(role="user", content="hello"),
        ],
        model="opencode-go/deepseek-v4-flash",
    )
    assert isinstance(result, LLMResult)
    assert result.content == "hi"
    assert result.model == "opencode-go/deepseek-v4-flash"
    assert result.tokens_in == 11
    assert result.tokens_out == 7
    # Request URL is the chat completions endpoint.
    assert recorded["url"].endswith("/chat/completions")
    assert recorded["method"] == "POST"
    body = json.loads(recorded["body"])
    assert body["model"] == "opencode-go/deepseek-v4-flash"
    assert body["messages"][-1]["content"] == "hello"


def test_per_call_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """T006 — per-call model/temperature/max_tokens override the defaults."""
    recorded = _freeze_urlopen(monkeypatch, _canned_response(content="x"))
    provider = OpenAICompatibleProvider(
        credentials=_StubSecretSource(
            {"OPENROUTER_API_KEY": "k", "OPENROUTER_BASE_URL": "https://o.example"}
        ),
        api_key_name="OPENROUTER_API_KEY",
        base_url_env="OPENROUTER_BASE_URL",
        default_model="openrouter/qwen/qwen3.8-max",
    )
    provider.complete(
        [LLMMessage(role="user", content="q")],
        model="openrouter/qwen/qwen3.8-max",
        temperature=0.2,
        max_tokens=123,
    )
    body = json.loads(recorded["body"])
    assert body["model"] == "openrouter/qwen/qwen3.8-max"
    assert body["temperature"] == 0.2
    assert body["max_tokens"] == 123


def test_http_error_redacts_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """T007 — non-2xx surfaces OpenAICompatibleError with the key redacted."""
    from json import dumps

    secret = "sk-super-secret-value"

    class _FakeResponse:
        def __init__(self) -> None:
            self.status = 401
            self.reason = "Unauthorized"

        def read(self) -> bytes:
            return dumps({"error": {"message": f"bad key {secret}"}}).encode("utf-8")

        def close(self) -> None:
            return None

        def __enter__(self) -> _FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def _boom(request, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise urllib.error.HTTPError(
            "https://api.example/chat/completions",
            401,
            "Unauthorized",
            {},
            _FakeResponse(),
        )

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    provider = OpenAICompatibleProvider(
        credentials=_StubSecretSource({"OPENCODE_GO_API_KEY": secret})
    )
    with pytest.raises(OpenAICompatibleError) as exc:
        provider.complete([LLMMessage(role="user", content="q")])
    assert REDACTED in str(exc.value)
    assert secret not in str(exc.value)


def test_non_json_response_raises_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    """T007 — a non-JSON body surfaces a typed error (redacted)."""
    _freeze_urlopen(monkeypatch, b"<html>not json</html>")
    provider = OpenAICompatibleProvider(
        credentials=_StubSecretSource({"OPENCODE_GO_API_KEY": "k"})
    )
    with pytest.raises(OpenAICompatibleError):
        provider.complete([LLMMessage(role="user", content="q")])
