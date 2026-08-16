"""Pluggable LLM provider abstraction (T013, R5, FR-018).

Libraries and workflows talk to a provider through :class:`LLMProvider` and
:class:`LLMResult`; they never hard-code a vendor SDK. Providers are selected
by name through :func:`create_provider` and registered in :data:`PROVIDERS`.

A deterministic :class:`FakeProvider` is included so unit/contract tests run
with **no network** (constitution + conftest). Live providers load their
credentials through the env/secret-store path (:func:`_resolve_credential`)
per FR-018 — never from committed config.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ai_factory.shared.secrets.loader import SecretSource, load_credential


class LLMMessage:
    """A single chat message sent to a provider."""

    __slots__ = ("role", "content")

    def __init__(self, role: str, content: str) -> None:
        self.role = role
        self.content = content


class LLMResult:
    """The structured outcome of a single completion (feeds FR-016 telemetry)."""

    __slots__ = ("content", "model", "tokens_in", "tokens_out", "raw")

    def __init__(
        self,
        content: str,
        model: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        raw: dict[str, Any] | None = None,
    ) -> None:
        self.content = content
        self.model = model
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.raw = raw or {}


class LLMProvider(ABC):
    """The provider contract. Implementations are network-free by default."""

    model_name = "abstract"

    @abstractmethod
    def complete(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResult:
        """Run a completion over ``messages``; return a structured result."""
        raise NotImplementedError

    def close(self) -> None:
        """Release any held resources."""
        raise NotImplementedError


class FakeProvider(LLMProvider):
    """Deterministic, network-free stand-in for tests and dry runs."""

    model_name = "fake"

    def complete(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResult:
        instruction = kwargs.get("instruction")
        echo = f"[{instruction}] " if instruction else ""
        content = echo + " ".join(f"{m.role}:{m.content}" for m in messages)
        return LLMResult(
            content=content,
            model=self.model_name,
            tokens_in=sum(len(m.content) for m in messages),
            tokens_out=len(content),
        )


class UnknownProviderError(ValueError):
    """Raised when :func:`create_provider` cannot find a registered name."""


PROVIDERS: dict[str, type[LLMProvider]] = {
    "fake": FakeProvider,
}


def _resolve_credential(name: str, source: SecretSource | None = None) -> str | None:
    """Resolve a provider credential via env, falling back to a secret source."""
    return load_credential(name, source=source, required=False)


def register_provider(name: str, provider_cls: type[LLMProvider]) -> None:
    """Add or replace a provider class under ``name``."""
    PROVIDERS[name] = provider_cls


def create_provider(
    name: str, *, credentials: SecretSource | None = None
) -> LLMProvider:
    """Instantiate the provider registered as ``name``.

    ``credentials`` (an env/secret-store source) is passed through for
    providers that need it at construction; the base contract resolves its
    own keys lazily. Raises :class:`UnknownProviderError` for an unregistered
    name.
    """
    cls = PROVIDERS.get(name)
    if cls is None:
        raise UnknownProviderError(
            f"Unknown LLM provider {name!r}; registered: {sorted(PROVIDERS)}"
        )
    try:
        provider = cls()
    except TypeError:
        provider = cls(credentials=credentials)  # type: ignore[call-arg]
    return provider


__all__ = [
    "FakeProvider",
    "LLMMessage",
    "LLMProvider",
    "LLMResult",
    "PROVIDERS",
    "UnknownProviderError",
    "create_provider",
    "register_provider",
]

# Register the live OpenAI-compatible provider at the END of module
# initialization, after the base classes are fully defined, to avoid a
# circular import: ``openai_compatible`` imports from this module.
from ai_factory.shared.llm.openai_compatible import (  # noqa: E402
    OpenAICompatibleProvider,
)

PROVIDERS["openai-compatible"] = OpenAICompatibleProvider
