"""T023 — the dev workflow graph wired to the dual-mode executor.

Offline runs keep today's deterministic behavior (no network, no creds).
Live runs (``live=True``) resolve each capability role's real model id and
dispatch it through the injected provider, and the telemetry records the real
resolved model + capability level rather than the hardcoded ``fake``/``standard``.
"""

from __future__ import annotations

import pytest

from ai_factory.dev_workflow.graph import build_dev_graph
from ai_factory.dev_workflow.models import Budget
from ai_factory.shared.git_host.client import FakeGitHost, PullRequest
from ai_factory.shared.llm.provider import LLMMessage, LLMProvider, LLMResult
from ai_factory.shared.sandbox.runner import FakeSandbox, SandboxResult
from ai_factory.shared.spec_store.handoff import publish_approved
from ai_factory.shared.spec_store.models import (
    AcceptanceCriterion,
    SpecVersion,
)
from ai_factory.shared.spec_store.store import FileSpecStore
from ai_factory.shared.telemetry.store import FileTelemetryStore


class _RecordingProvider(LLMProvider):
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def complete(self, messages: list[LLMMessage], **kwargs) -> LLMResult:  # type: ignore[override]
        self.calls.append({"model": kwargs.get("model")})
        return LLMResult(
            content="ok",
            model=str(kwargs.get("model", "fake")),
            tokens_in=9,
            tokens_out=7,
        )


APPROVABLE_SPEC = [
    ("Search returns the index of a found element", "test"),
]


def _spec_store(tmp_path) -> tuple[FileSpecStore, str]:
    spec = SpecVersion(
        spec_run_id="spec-run-1",
        version=1,
        intent="Add a binary search helper",
        acceptance_criteria=[
            AcceptanceCriterion(statement=s, verified_by=v) for s, v in APPROVABLE_SPEC
        ],
        definition_of_done="done",
        edge_cases=[],
        approval_status="approved",
        human_approved=True,
    )
    store = FileSpecStore(tmp_path / "specs")
    published = publish_approved(spec, store)
    return store, published.spec_version_id


def _build(tmp_path, *, live=False, provider=None, telemetry_store=None):
    store, version_id = _spec_store(tmp_path)
    sandbox = FakeSandbox(
        SandboxResult(exit_code=0, stdout="1 passed"),
    )
    git_host = FakeGitHost()
    repo = tmp_path / "repo"
    app = build_dev_graph(
        store,
        sandbox,
        git_host,
        repo_root=repo,
        run_dir=tmp_path / "runstate",
        budget=Budget(cost_usd=10.0),
        live=live,
        provider=provider,
        telemetry_store=telemetry_store,
    )
    initial = {
        "run_id": "dev-run-1",
        "spec_version_id": version_id,
        "spec_run_id": "spec-run-1",
        "repo": str(repo),
        "outcome": "planned",
        "dev_attempt": 0,
    }
    return app, initial, git_host, repo


class TestOfflineStaysDeterministic:
    """T020/T023 — offline graph runs produce today's deterministic delivery."""

    def test_offline_delivers_pr(self, tmp_path) -> None:
        app, initial, git_host, repo = _build(tmp_path)
        result = app.invoke(initial)
        assert result["outcome"] == "delivered"
        assert isinstance(result["pr"], PullRequest)
        assert (repo / "test_suite.py").exists()


class TestLiveDispatch:
    """T023 — live graph dispatches each capability role through the provider."""

    @pytest.fixture(autouse=True)
    def _live_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # A live run requires the opt-in AND a credential (T021); simulate a
        # real operator who opted in with a key. The injected provider is the
        # transport, so no network is used here.
        monkeypatch.setenv("OPENCODE_GO_API_KEY", "sk-test-live-key")

    def test_live_dispatches_capability_roles(self, tmp_path) -> None:
        rec = _RecordingProvider()
        app, initial, _, _ = _build(tmp_path, live=True, provider=rec)
        result = app.invoke(initial)
        assert result["outcome"] == "delivered"
        assert rec.calls, "live run must dispatch capability roles through the provider"
        # Every resolved model is provider-prefixed (FR-010).
        for call in rec.calls:
            assert call["model"].split("/", 1)[0] in ("opencode-go", "openrouter")

    def test_live_telemetry_records_real_model(self, tmp_path) -> None:
        rec = _RecordingProvider()
        ts = FileTelemetryStore(tmp_path / "telemetry")
        app, initial, _, _ = _build(
            tmp_path, live=True, provider=rec, telemetry_store=ts
        )
        app.invoke(initial)
        invocations = ts.get("dev-run-1")
        assert invocations, "live run must emit telemetry"
        # At least one capability role should report a real (non-fake) model.
        assert any(
            inv["model"] != "fake" and inv["capability_level"] == "standard"
            for inv in invocations
        )
