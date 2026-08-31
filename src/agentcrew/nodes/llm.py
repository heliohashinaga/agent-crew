"""LLM-backed node: calls an OpenAI-compatible chat API (OpenRouter / OpenCode Go).

This is the first *networked* node in agentcrew. It is a LangChain ``Runnable``
just like ``hello_world`` (same ``invoke``/``stream`` semantics), but it reaches
out to a hosted OpenAI-compatible chat endpoint. It requires an API key for the
chosen provider and network access. It is intentionally *not* imported by the
offline CLI path so the base stays deterministic — this node is opt-in for LLM
testing/tracing.

Two providers are supported out of the box, both served through the OpenAI
``/v1/chat/completions`` shape:

- ``openrouter``  -> base ``https://openrouter.ai/api/v1`` (``OPENROUTER_API_KEY``)
- ``opencode``    -> OpenCode Go, base ``https://opencode.ai/zen/go/v1``
                     (``OPENCODE_GO_API_KEY``)
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_openai import ChatOpenAI

from agentcrew.nodes.models import LLMNodeResult

# Make OPENROUTER_API_KEY / OPENCODE_GO_API_KEY (and other vars) from a local
# .env take effect regardless of entry point (CLI or direct import). Doesn't
# override already-set environment variables.
load_dotenv()

Provider = Literal["openrouter", "opencode"]

# Per-provider defaults (env var -> fallback value). Explicit args win over env.
_PROVIDER_DEFAULTS: dict[Provider, dict[str, str]] = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "model_env": "OPENROUTER_MODEL",
        "model": "anthropic/claude-sonnet-4-5",
    },
    "opencode": {
        "base_url": "https://opencode.ai/zen/go/v1",
        "api_key_env": "OPENCODE_GO_API_KEY",
        "model_env": "OPENCODE_GO_MODEL",
        "model": "kimi-k3",
    },
}


def _resolve(provider: Provider, field: str, explicit: str | None) -> str:
    """Resolve a config value by precedence: explicit arg -> env -> preset default.

    Only the ``model`` field reads an env var override (``*_MODEL``); the API
    key reads its own ``*_API_KEY`` env var; ``base_url`` always uses the
    provider preset (no env override). Field/env are never crossed.
    """
    if explicit is not None:
        return explicit
    preset = _PROVIDER_DEFAULTS[provider]
    if field == "api_key":
        # API key has no built-in default; fall back to empty if env unset.
        return os.environ.get(preset["api_key_env"], "").strip()
    if field == "model":
        return os.environ.get(preset["model_env"], "").strip() or preset["model"]
    # base_url
    return preset["base_url"]


def _build_chat(
    provider: Provider,
    *,
    model: str,
    api_key: str,
    base_url: str,
) -> ChatOpenAI:
    return ChatOpenAI(model=model, api_key=api_key or None, base_url=base_url)


def provider_api_key(provider: Provider) -> str:
    """Return the resolved API key for a provider (from env if none was passed).

    Empty string means no key is configured for that provider.
    """
    return _resolve(provider, "api_key", None)


@lru_cache(maxsize=8)
def _cached_chat(
    provider: str, model: str, api_key: str, base_url: str
) -> ChatOpenAI:
    """Return a cached chat client so repeated invokes reuse one connection."""
    return _build_chat(provider, model=model, api_key=api_key, base_url=base_url)


def build_llm_node(
    provider: Provider = "openrouter",
    *,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    cached: bool = True,
) -> Runnable:
    """Return a ``Runnable`` that chats with an OpenAI-compatible model.

    Args:
        provider: ``"openrouter"`` (default) or ``"opencode"`` (OpenCode Go).
        model: Model id. Defaults to the provider's env var, then a built-in
            fallback (``anthropic/claude-sonnet-4-5`` for OpenRouter,
            ``kimi-k3`` for OpenCode Go).
        api_key: Provider API key. Defaults to the provider's key env var
            (``OPENROUTER_API_KEY`` / ``OPENCODE_GO_API_KEY``). If none is
            found, the base URL must supply auth another way.
        base_url: API base URL override (defaults to the provider's endpoint).
        cached: Reuse a shared cached client when ``True`` (default), which
            avoids rebuilding the connection on every ``invoke`` — recommended
            for tracing/testing. Pass ``cached=False`` for a fresh client.
    """
    base_url = _resolve(provider, "base_url", base_url)
    api_key = _resolve(provider, "api_key", api_key)
    model = _resolve(provider, "model", model)
    chat = _cached_chat(provider, model, api_key, base_url) if cached else _build_chat(
        provider, model=model, api_key=api_key, base_url=base_url
    )

    def _complete(raw_text: str) -> dict[str, str]:
        text = raw_text.strip()
        # Delegate input validation to the pydantic model (raises on blank).
        LLMNodeResult(input=text, model=model, response="")
        response = chat.invoke(text).content
        result = LLMNodeResult(input=text, model=model, response=str(response))
        return result.model_dump()

    return RunnableLambda(_complete)