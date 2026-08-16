"""Tests for the dual-mode role executor/scheduler and live dispatcher (T020-T022).

The executor is the single seam between the deterministic offline path and the
opt-in live LLM path:

- **US3**: offline by default; nothing goes live unless the operator opts in.
- **US4**: each role runs offline (deterministic, no network, no creds) or live
  (resolved real model id through a registered provider).
- **T021**: credentials alone never enable live mode — ``AI_FACTORY_LIVE=1`` (or
  an explicit flag) **and** an API key are both required.
- **T022**: an unresolvable model id fails closed (deterministic path or a typed
  error) — the provider is never called with an empty/garbage id.
"""

from __future__ import annotations

import os

import pytest

from ai_factory.capability_levels.model_map import ModelMapError
from ai_factory.dev_workflow.executor.runner import live_enabled, run_role
from ai_factory.shared.llm.provider import LLMMessage, LLMProvider, LLMResult


class _RecordingProvider(LLMProvider):
    """Stand-in provider that records every ``complete`` call."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def complete(self, messages: list[LLMMessage], **kwargs) -> LLMResult:  # type: ignore[override]
        self.calls.append({"messages": messages, "kwargs": kwargs})
        return LLMResult(
            content="live-dispatch-ok",
            model=str(kwargs.get("model", "opencode-go/deepseek-v4-flash")),
            tokens_in=1,
            tokens_out=1,
        )


class TestOptInGate:
    """T021 — credentials alone never go live."""

    def test_creds_without_optin_is_offline(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AI_FACTORY_LIVE", raising=False)
        monkeypatch.setenv("OPENCODE_GO_API_KEY", "sk-key-present")
        assert live_enabled() is False

    def test_optin_without_creds_is_offline(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_FACTORY_LIVE", "1")
        monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        assert live_enabled() is True
        # run_role still refuses to go live without a credential.
        rec = _RecordingProvider()
        result = run_role(
            "code_worker",
            level="standard",
            offline_fn=lambda plan=None, repo=None: "deterministic",
            offline_kwargs={},
            live=True,
            provider=rec,
        )
        assert result.live_used is False
        assert result.mode == "offline"
        assert rec.calls == []

    def test_optin_and_creds_is_live(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_FACTORY_LIVE", "1")
        monkeypatch.setenv("OPENCODE_GO_API_KEY", "sk-key-present")
        assert live_enabled() is True

    def test_explicit_flag_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # No env opt-in, but an explicit --live flag with creds present.
        monkeypatch.delenv("AI_FACTORY_LIVE", raising=False)
        monkeypatch.setenv("OPENCODE_GO_API_KEY", "sk-key-present")
        rec = _RecordingProvider()
        result = run_role(
            "code_worker",
            level="standard",
            offline_fn=lambda: "deterministic",
            offline_kwargs={},
            live=True,
            provider=rec,
        )
        assert result.live_used is True
        assert rec.calls, "live mode must dispatch through the provider"


class TestOfflineSameOutput:
    """T020 — offline mode is byte-identical to the deterministic function."""

    def test_offline_delegates_to_deterministic_function(self) -> None:
        calls = []

        def _det(plan=None, repo=None):
            calls.append((plan, repo))
            return "deterministic-output"

        result = run_role(
            "code_worker",
            level="standard",
            offline_fn=_det,
            offline_kwargs={"plan": "P", "repo": "/repo"},
            live=False,
        )
        assert result.output == "deterministic-output"
        assert calls == [("P", "/repo")]
        assert result.mode == "offline"
        assert result.live_used is False


class TestLiveDispatch:
    """T020 — live mode with a stubbed transport calls provider.complete with the
    correct resolved model id for the role+level."""

    def test_live_dispatches_with_resolved_model_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENCODE_GO_API_KEY", "sk-key-present")
        rec = _RecordingProvider()
        result = run_role(
            "code_worker",
            level="simple",
            offline_fn=lambda **_: "deterministic",
            offline_kwargs={},
            live=True,
            provider=rec,
            env=os.environ,
        )
        assert result.live_used is True
        assert result.model == "opencode-go/deepseek-v4-flash"
        assert rec.calls, "live dispatch must issue a provider call"
        assert rec.calls[0]["kwargs"]["model"] == "opencode-go/deepseek-v4-flash"
        # The deterministic output is still preserved for downstream state.
        assert result.output == "deterministic"

    def test_live_uses_role_capability_level_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-key-present")
        rec = _RecordingProvider()
        result = run_role(
            "security_reviewer",
            level="deep",
            offline_fn=lambda **_: "deterministic",
            offline_kwargs={},
            live=True,
            provider=rec,
            env=os.environ,
        )
        assert result.model == "opencode-go/kimi-k3"
        assert rec.calls[0]["kwargs"]["model"] == "opencode-go/kimi-k3"


class TestFailClosed:
    """T022 — an unresolvable model id never reaches the provider."""

    def test_unmapped_level_fails_closed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENCODE_GO_API_KEY", "sk-key-present")
        rec = _RecordingProvider()
        with pytest.raises(ModelMapError):
            run_role(
                "code_worker",
                level="no-such-level",
                offline_fn=lambda **_: "deterministic",
                offline_kwargs={},
                live=True,
                provider=rec,
                env=os.environ,
            )
        assert rec.calls == [], "provider must not be called with a bad model id"
