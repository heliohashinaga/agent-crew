"""Tests for the secret/redaction library (T008).

Covers the credential loaders and secret-value redaction required by FR-018:
credentials load ONLY from the environment or a secret store (never committed
config) and secret-looking values are auto-redacted from logs/telemetry before
emission.
"""

from __future__ import annotations

import pytest

from ai_factory.shared.secrets.loader import (
    EnvSecretSource,
    SecretSource,
    load_credential,
    redact,
    redact_mapping,
    redact_secret_like,
)


class _DictSecretSource(SecretSource):
    """Minimal in-memory secret store (a stand-in, not committed config)."""

    def __init__(self, data: dict[str, str]) -> None:
        self._data = dict(data)

    def get(self, name: str) -> str | None:  # noqa: D102
        return self._data.get(name)


def test_load_credential_reads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "sk-super-secret-123")
    assert load_credential("LLM_API_KEY") == "sk-super-secret-123"


def test_load_credential_reads_from_secret_store() -> None:
    store = _DictSecretSource({"github_token": "ghp_12345"})
    assert load_credential("github_token", source=store) == "ghp_12345"


def test_load_credential_prefers_env_over_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _DictSecretSource({"TOKEN": "from-store"})
    monkeypatch.setenv("TOKEN", "from-env")
    assert load_credential("TOKEN", source=store) == "from-env"


def test_load_credential_missing_optional_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MISSING_VAR", raising=False)
    assert load_credential("MISSING_VAR", required=False) is None


def test_load_credential_missing_required_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MISSING_VAR", raising=False)
    with pytest.raises(RuntimeError, match="MISSING_VAR"):
        load_credential("MISSING_VAR", required=True)


def test_env_source_returns_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NOTHING_HERE", raising=False)
    assert EnvSecretSource().get("NOTHING_HERE") is None


def test_redact_replaces_secret_values() -> None:
    out = redact("conn = postgres://usr:SUPERSECRET@db", ["SUPERSECRET"])
    assert out == "conn = postgres://usr:[REDACTED]@db"
    assert "SUPERSECRET" not in out


def test_redact_only_known_secrets() -> None:
    out = redact("token=abc password=xyz", ["abc"])
    assert "abc" not in out
    assert "xyz" in out


def test_redact_no_secrets_is_identity() -> None:
    assert redact("hello world", []) == "hello world"


def test_redact_mapping_recurses() -> None:
    obj = {
        "role": "code_worker",
        "creds": {"key": "secret-1"},
        "tags": ["secret-1", "ok"],
    }
    out = redact_mapping(obj, ["secret-1"])
    assert out["creds"]["key"] == "[REDACTED]"
    assert out["tags"][0] == "[REDACTED]"
    assert out["tags"][1] == "ok"
    assert out["role"] == "code_worker"


def test_redact_mapping_recurses_lists() -> None:
    assert redact_mapping(["a", {"b": "boom"}], ["boom"]) == ["a", {"b": "[REDACTED]"}]


def test_redact_secret_like_catches_bearer_and_password_assignments() -> None:
    text = "Authorization: Bearer xyz123token pw=topsecret"
    out = redact_secret_like(text)
    assert "xyz123token" not in out
    assert "topsecret" not in out
    assert "Bearer" in out


def test_redact_secret_like_leaves_plain_text() -> None:
    out = redact_secret_like("Add a password reset flow to auth")
    assert out == "Add a password reset flow to auth"
