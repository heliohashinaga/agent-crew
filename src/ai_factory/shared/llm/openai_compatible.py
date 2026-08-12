"""OpenAI-compatible live LLM provider (T005-T007, US1/US2, FR-018).

An :class:`LLMProvider` speaking the OpenAI ``/chat/completions`` wire format
over stdlib ``urllib`` (no external SDK dependency). It supports the two
vendors used by the factory — ``opencode-go`` and ``openrouter`` — which both
expose OpenAI-compatible endpoints. Both can be wired up **simultaneously**:
an operator points each provider at its own base URL / API key / model.

Security & configuration (FR-018):

- API keys load **only** from the environment or an injected secret source —
  never from committed config.
- The constructor performs **no network I/O** and is safe to build with **no
  environment variables** (documented default ``base_url`` / ``model``).
  Credentials fail fast (typed error) only when a live call requires them.
- Every error message is run through :func:`redact_secret_like` so no API key
  value leaks into an exception surface (SC-005).

Per-call overrides: ``complete(..., model=, temperature=, max_tokens=)`` win
over the provider-configured defaults, so an operator can switch models per
call (e.g. cheap rank/summarize vs capable) without code changes.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from ai_factory.shared.llm.provider import LLMMessage, LLMProvider, LLMResult
from ai_factory.shared.secrets.loader import (
    REDACTED,
    SecretSource,
    load_credential,
    redact,
    redact_secret_like,
)

# Documented per-vendor base URLs (defaults when env vars are absent). Must
# not be required to build the provider; a live call resolves the real URL.
_DEFAULT_BASE_URLS = {
    "opencode-go": "https://opencode-go.example.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}

_DEFAULT_MODELS = {
    "opencode-go": "opencode-go/deepseek-v4-flash",
    "openrouter": "openrouter/qwen/qwen3.8-max",
}

# Default temperature / max_tokens when a call provides no override.
_DEFAULT_TEMPERATURE = 0.2
_DEFAULT_MAX_TOKENS = 1024


class OpenAICompatibleError(RuntimeError):
    """Raised for any live-call failure on the OpenAI-compatible provider.

    The message is secret-redacted (SC-005/FR-018): an API key never appears.
    """


class OpenAICompatibleProvider(LLMProvider):
    """A stdlib-only OpenAI-compatible ``/chat/completions`` provider."""

    model_name = "openai-compatible"

    def __init__(
        self,
        *,
        credentials: SecretSource | None = None,
        api_key_name: str = "OPENCODE_GO_API_KEY",
        base_url_env: str = "OPENCODE_GO_BASE_URL",
        default_model: str | None = None,
        vendor: str | None = None,
    ) -> None:
        self._credentials = credentials
        self._api_key_name = api_key_name
        self._base_url_env = base_url_env
        # Documented default model/key-vendor (opencode-go unless otherwise set).
        if vendor is None:
            vendor = (
                "opencode-go"
                if api_key_name == "OPENCODE_GO_API_KEY"
                else "openrouter"
            )
        self._vendor = vendor
        self.default_model = default_model or _DEFAULT_MODELS.get(
            vendor, _DEFAULT_MODELS["opencode-go"]
        )
        # No network I/O here and nothing required: defaults are safe.
        self._resolved_key: str | None = None

    @property
    def api_key_name(self) -> str:
        return self._api_key_name

    @property
    def api_key(self) -> str:
        """The resolved API key; raises a typed error when missing."""
        if self._resolved_key is None:
            try:
                key = load_credential(
                    self._api_key_name, source=self._credentials, required=True
                )
            except RuntimeError as exc:
                raise OpenAICompatibleError(
                    f"{REDACTED}: live call requires '{self._api_key_name}' but it is "
                    "not set in the environment or secret store (set it, or run "
                    "offline / with --live off)"
                ) from exc
            if not key:
                raise OpenAICompatibleError(
                    f"{REDACTED}: '{self._api_key_name}' is empty"
                )
            self._resolved_key = key
        return self._resolved_key

    @property
    def base_url(self) -> str:
        """The resolved base URL (env override or documented default)."""
        url = load_credential(
            self._base_url_env, source=self._credentials, required=False
        )
        if url:
            return url.rstrip("/")
        return _DEFAULT_BASE_URLS.get(self._vendor, _DEFAULT_BASE_URLS["opencode-go"])

    def _endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"

    def _redact(self, text: str) -> str:
        """Redact the known API key value AND secret-like material."""
        key_value = self._resolved_key
        if key_value:
            text = redact(text, [key_value])
        return redact_secret_like(text)

    def complete(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResult:
        """POST ``/chat/completions`` and parse an :class:`LLMResult`.

        ``model`` / ``temperature`` / ``max_tokens`` kwargs override the
        provider-configured defaults.
        """
        # Fails fast (typed) if the credential is missing for this live call.
        key = self.api_key
        model = kwargs.get("model", self.default_model)
        body: dict[str, Any] = {"model": model}
        body["messages"] = [
            {"role": m.role, "content": m.content} for m in messages
        ]
        temperature = kwargs.get("temperature")
        if temperature is not None:
            body["temperature"] = temperature
        else:
            body["temperature"] = _DEFAULT_TEMPERATURE
        max_tokens = kwargs.get(
            "max_tokens", kwargs.get("max_completion_tokens")
        )
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        else:
            body["max_tokens"] = _DEFAULT_MAX_TOKENS

        request = urllib.request.Request(
            self._endpoint(),
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request) as response:  # noqa: S310 (stdlib, no SSL pinning needed for tests)
                payload = response.read()
        except urllib.error.HTTPError as http_error:
            detail = ""
            try:
                detail = http_error.read().decode("utf-8", errors="replace")
            except OSError:
                detail = ""
            if not detail:
                detail = f"HTTP {http_error.code} {http_error.reason}"
            raise OpenAICompatibleError(
                f"OpenAI-compatible call failed: {self._redact(detail)}"
            ) from http_error
        except OSError as exc:
            raise OpenAICompatibleError(
                f"OpenAI-compatible call failed: {self._redact(str(exc))}"
            ) from exc

        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OpenAICompatibleError(
                f"OpenAI-compatible response was not valid JSON: "
                f"{self._redact(payload.decode('utf-8', errors='replace')[:200])}"
            ) from exc

        try:
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage") or {}
            tokens_in = int(usage.get("prompt_tokens", 0))
            tokens_out = int(usage.get("completion_tokens", 0))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise OpenAICompatibleError(
                f"OpenAI-compatible response missing expected fields "
                f"(choices/message/content/usage): {self._redact(str(data)[:200])}"
            ) from exc

        content = content or ""
        return LLMResult(
            content=content,
            model=str(data.get("model") or model),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            raw=data,
        )
