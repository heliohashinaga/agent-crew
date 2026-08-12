"""Live LLM provider selection for the ``researcher`` web scope (T024, FR-007).

The ``web`` scope already takes an injected :class:`~ai_factory.shared.llm.
provider.LLMProvider` (Option D). This module is the **call-site #1** seam that
hands the researcher a provider built from the registered ``openai-compatible``
provider:

- When an API key is present (env/secret store), it returns a live
  ``openai-compatible`` provider built through ``create_provider`` (so a ``web``
  lookup can use a real model **without code edits**).
- Without credentials it falls back to the deterministic
  :class:`~ai_factory.shared.llm.provider.FakeProvider` (US1/scenario 2) —
  offline default is unchanged (US3).

Security: the provider carries **no committed secrets** (FR-018); keys resolve
from the env/secret-store path only. Network is inherent to live ``web``
lookups and stays integration-gated at the test level.
"""

from __future__ import annotations

import os

from ai_factory.shared.llm.provider import (
    LLMProvider,
    create_provider,
)

# Opt-in gate for a live researcher (``AI_FACTORY_LIVE=1``/true), plus the
# API keys that make a live provider usable.
_LIVE_ENV = "AI_FACTORY_LIVE"
_CRED_ENV = ("OPENCODE_GO_API_KEY", "OPENROUTER_API_KEY")
_TRUE_VALUES = {"1", "true", "yes", "on"}


def live_creds_present(*, env: dict[str, str] | None = None) -> bool:
    """Whether a usable live credential is configured (regardless of opt-in)."""
    env = env if env is not None else os.environ
    return any(bool(env.get(key)) for key in _CRED_ENV)


def live_opted_in(*, env: dict[str, str] | None = None) -> bool:
    """Whether ``AI_FACTORY_LIVE`` is set to a truthy value."""
    env = env if env is not None else os.environ
    return env.get(_LIVE_ENV, "").strip().lower() in _TRUE_VALUES


def build_researcher_llm(
    *,
    live: bool | None = None,
    env: dict[str, str] | None = None,
    provider: LLMProvider | None = None,
) -> LLMProvider:
    """Return an LLM provider for a researcher web lookup.

    - ``live=True`` **and** an API key present → the registered ``openai-compatible``
      provider (via ``create_provider``).
    - Otherwise → the deterministic :class:`FakeProvider` (US1/scenario 2).
    - An explicitly injected ``provider`` wins over both (testability seam).
    """
    env = env if env is not None else os.environ
    if provider is not None:
        return provider
    opted_in = live_opted_in(env=env) if live is None else bool(live)
    if opted_in and live_creds_present(env=env):
        return create_provider("openai-compatible")
    return create_provider("fake")


def run_web_lookup(
    query: str,
    *,
    fetcher,
    content_fetcher,
    live: bool | None = None,
    env: dict[str, str] | None = None,
    provider: LLMProvider | None = None,
    angles: list[str] | None = None,
    context_window: int | None = None,
):
    """Run a ``web``-scope lookup, wiring the shared live provider (T024).

    ``llm`` is chosen via :func:`build_researcher_llm` — the registered
    ``openai-compatible`` provider when live+creds, else ``FakeProvider``.
    """
    from ai_factory.researcher.web import web_lookup

    llm = build_researcher_llm(live=live, env=env, provider=provider)
    kwargs: dict = {"angles": angles}
    if context_window is not None:
        kwargs["context_window"] = context_window
    return web_lookup(
        query,
        llm=llm,
        fetcher=fetcher,
        content_fetcher=content_fetcher,
        **kwargs,
    )


__all__ = [
    "build_researcher_llm",
    "live_creds_present",
    "live_opted_in",
    "run_web_lookup",
]
