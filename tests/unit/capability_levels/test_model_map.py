"""Tests for the per-role capability-level model map (T010, US4, FR-010).

Resolution precedence: **code defaults < model-map.json < env**. Both role
axes (task simple/standard/complex; review shallow/standard/deep) and both
providers (opencode-go / openrouter, usable simultaneously) are covered.
Unknown role/level falls back to the default. Network never required.
"""

from __future__ import annotations

import pytest

from ai_factory.capability_levels.model_map import (
    ModelMapError,
    code_default,
    default_model_id,
    resolve_model_id,
)


class TestCodeDefaults:
    """Level-tier → documented default model id (no JSON, no env)."""

    def test_task_simple_is_fast_cheap(self) -> None:
        assert resolve_model_id("code_worker", "simple") == code_default("fast-cheap")

    def test_standard_maps_to_capable_tier(self) -> None:
        assert resolve_model_id("code_worker", "standard") == code_default("capable")

    def test_complex_maps_to_deep_tier(self) -> None:
        assert resolve_model_id("test_engineer", "complex") == code_default("deep")

    def test_review_shallow_is_fast_cheap(self) -> None:
        assert resolve_model_id("code_reviewer", "shallow") == code_default(
            "fast-cheap"
        )

    def test_review_deep_is_deep_tier(self) -> None:
        assert resolve_model_id("security_reviewer", "deep") == code_default("deep")

    def test_fixed_role_standard_is_capable(self) -> None:
        assert resolve_model_id("orchestrator", "standard") == code_default("capable")

    def test_defaults_are_provider_prefixed(self) -> None:
        # Every default is a provider-prefixed id (FR-010).
        for mid in (
            resolve_model_id("code_worker", "simple"),
            resolve_model_id("code_worker", "standard"),
            resolve_model_id("code_worker", "complex"),
        ):
            assert mid.split("/", 1)[0] in ("opencode-go", "openrouter")

    def test_default_model_id_is_prefixed(self) -> None:
        assert default_model_id().split("/", 1)[0] in ("opencode-go", "openrouter")


class TestJsonOverride:
    """modi-model-map.json beats code defaults (precedence: code < JSON < env)."""

    def _map(self) -> dict:
        return {
            "roles": {
                "code_worker": {
                    "simple": "openrouter/custom/simple-model",
                    "complex": "opencode-go/custom/complex",
                }
            },
            "default": "opencode-go/global-default",
        }

    def test_js_module_overrides_simple(self) -> None:
        m = self._map()
        assert resolve_model_id("code_worker", "simple", model_map=m) == (
            "openrouter/custom/simple-model"
        )
    def test_js_unlisted_level_uses_code_default(self) -> None:
        # 'standard' is not in the JSON for code_worker → falls back to code default.
        m = self._map()
        assert resolve_model_id("code_worker", "standard", model_map=m) == code_default(
            "capable"
        )

    def test_js_global_default_for_unknown_role(self) -> None:
        m = self._map()
        assert resolve_model_id("nonexistent_role", "standard", model_map=m) == (
            "opencode-go/global-default"
        )

    def test_js_empty_garbage_id_fails_closed(self) -> None:
        m = {"roles": {"code_worker": {"simple": "   "}}, "default": ""}
        with pytest.raises(ModelMapError):
            resolve_model_id("code_worker", "simple", model_map=m)


ENV_KEYS = ("MODEL_FAST_CHEAP", "MODEL_CAPABLE", "MODEL_DEEP", "MODEL_DEFAULT")


class TestEnvOverride:
    """Env (flattened by level tier) beats both JSON and code defaults."""

    @pytest.fixture(autouse=True)
    def _clean_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in ENV_KEYS:
            monkeypatch.delenv(key, raising=False)

    def test_fast_cheap_env_wins_for_simple(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MODEL_FAST_CHEAP", "openrouter/mine/fast")
        assert resolve_model_id("code_worker", "simple") == "openrouter/mine/fast"

    def test_capable_env_wins_for_standard(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MODEL_CAPABLE", "opencode-go/mine/capable")
        assert resolve_model_id("code_worker", "standard") == "opencode-go/mine/capable"

    def test_deep_env_wins_for_complex_and_deep(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MODEL_DEEP", "openrouter/mine/deep")
        assert resolve_model_id("test_engineer", "complex") == "openrouter/mine/deep"
        assert resolve_model_id("security_reviewer", "deep") == "openrouter/mine/deep"

    def test_env_beats_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MODEL_FAST_CHEAP", "opencode-go/env/override")
        m = {"roles": {"code_worker": {"simple": "openrouter/json/val"}}}
        assert resolve_model_id("code_worker", "simple", model_map=m) == (
            "opencode-go/env/override"
        )

    def test_model_default_fallback_for_unknown_level(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MODEL_DEFAULT", "opencode-go/fallback")
        assert resolve_model_id("code_worker", "bogus-level") == "opencode-go/fallback"


class TestUnknownFallback:
    """Unknown role/level falls back to the global default, never a bad id."""

    def test_unknown_role_returns_default(self) -> None:
        assert resolve_model_id("nope", "standard") == default_model_id()

    def test_unknown_level_returns_default(self) -> None:
        assert resolve_model_id("code_worker", "nope") == default_model_id()
