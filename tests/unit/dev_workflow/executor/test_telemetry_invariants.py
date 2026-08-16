"""T031 — live-mode telemetry invariants (FR-016/FR-017, SC-005).

Live-mode role emissions must record the role, capability level, resolved real
model id, tokens, cost and latency — and never leak an API key into any
telemetry/log surface (reusing the shared redaction path).
"""

from __future__ import annotations

import json

import pytest

from ai_factory.dev_workflow.executor.runner import run_role
from ai_factory.shared.llm.provider import LLMMessage, LLMProvider, LLMResult
from ai_factory.shared.telemetry.record import DevRoleInvocation, TelemetryRecord
from ai_factory.shared.telemetry.store import FileTelemetryStore


class _TelemetryLive(LLMProvider):
    """Returns an LLMResult with real token/cost/latency-able fields."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def complete(self, messages: list[LLMMessage], **kwargs) -> LLMResult:  # type: ignore[override]
        self.calls.append({"model": kwargs.get("model")})
        return LLMResult(
            content="telemetry-ok",
            model=str(kwargs.get("model", "opencode-go/deepseek-v4-flash")),
            tokens_in=15,
            tokens_out=8,
        )


class TestTelemetryFields:
    """T031 — a live role run carries the full observability record."""

    def test_live_run_carries_telemetry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENCODE_GO_API_KEY", "sk-telemetry-key")
        rec = _TelemetryLive()
        result = run_role(
            "code_worker",
            level="standard",
            offline_fn=lambda **_: "done",
            offline_kwargs={},
            live=True,
            provider=rec,
        )
        assert result.live_used is True
        assert result.model == "openrouter/qwen/qwen3.8-max"
        assert result.tokens_in == 15
        assert result.tokens_out == 8
        assert result.latency >= 0.0
        assert result.cost >= 0.0

    def test_telemetry_record_populates_all_fields(self) -> None:
        record = TelemetryRecord(
            tokens_in=15,
            tokens_out=8,
            cost=0.0042,
            latency=1.2,
            result="pass",
        )
        inv = DevRoleInvocation(
            role="code_worker",  # type: ignore[arg-type]
            model="openrouter/qwen/qwen3.8-max",
            capability_level="standard",
            telemetry=record,
        )
        data = inv.model_dump()
        assert data["role"] == "code_worker"
        assert data["capability_level"] == "standard"
        assert data["model"] == "openrouter/qwen/qwen3.8-max"
        assert data["telemetry"]["tokens_in"] == 15
        assert data["telemetry"]["tokens_out"] == 8
        assert data["telemetry"]["cost"] == pytest.approx(0.0042)
        assert data["telemetry"]["latency"] == pytest.approx(1.2)


class TestNoSecretLeak:
    """T031/SC-005 — no API key appears in any telemetry serialization."""

    def test_telemetry_store_content_has_no_api_key(
        self, tmp_path, monkeypatch
    ) -> None:
        secret = "sk-super-secret-telemetry-value"
        monkeypatch.setenv("OPENCODE_GO_API_KEY", secret)
        rec = _TelemetryLive()
        result = run_role(
            "code_worker",
            level="simple",
            offline_fn=lambda **_: "done",
            offline_kwargs={},
            live=True,
            provider=rec,
        )
        # Serialize the invocation exactly as the store would.
        inv = DevRoleInvocation(
            role="code_worker",  # type: ignore[arg-type]
            model=result.model,
            capability_level=result.capability_level,
            telemetry=TelemetryRecord(
                tokens_in=result.tokens_in,
                tokens_out=result.tokens_out,
                cost=result.cost,
                latency=result.latency,
            ),
        )
        raw = json.dumps(inv.model_dump())
        assert secret not in raw, "API key leaked into telemetry serialization"

        # Round-trip through the store on disk (which also redacts on read).
        store = FileTelemetryStore(tmp_path / "telemetry")
        store.add("dev-run-sec", inv)
        ondisk_records = store.get("dev-run-sec")
        assert ondisk_records
        for rec in ondisk_records:
            assert secret not in json.dumps(rec)
