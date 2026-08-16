"""T030 — the default offline suite never touches HTTP (SC-002, SC-006).

The deterministic dev workflow must run to delivery with every HTTP call
frozen to an immediate failure. This proves offline parity (US3) and that
nothing outside ``-m integration`` reaches the network.
"""

from __future__ import annotations

import urllib.request

import pytest

from ai_factory.dev_workflow.graph import build_dev_graph
from ai_factory.dev_workflow.models import Budget
from ai_factory.shared.git_host.client import FakeGitHost, PullRequest
from ai_factory.shared.sandbox.runner import FakeSandbox, SandboxResult
from ai_factory.shared.spec_store.handoff import publish_approved
from ai_factory.shared.spec_store.models import AcceptanceCriterion, SpecVersion
from ai_factory.shared.spec_store.store import FileSpecStore


def _freeze_http(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace ``urllib.request.urlopen`` to raise if any deterministic role
    tries to make an HTTP call."""
    seen: list[str] = []

    def _blocked(request, *args, **kwargs):  # type: ignore[no-untyped-def]
        seen.append(getattr(request, "full_url", "<request>"))
        raise RuntimeError("network blocked by T030 offline suite")

    monkeypatch.setattr(urllib.request, "urlopen", _blocked)
    return seen


def _store_with_approved_spec(tmp_path):
    spec = SpecVersion(
        spec_run_id="spec-run-1",
        version=1,
        intent="Add a binary search helper",
        acceptance_criteria=[
            AcceptanceCriterion(statement="returns index", verified_by="test")
        ],
        definition_of_done="done",
        edge_cases=[],
        approval_status="approved",
        human_approved=True,
    )
    store = FileSpecStore(tmp_path / "specs")
    published = publish_approved(spec, store)
    return store, published.spec_version_id


def _run_offline(tmp_path):
    store, version_id = _store_with_approved_spec(tmp_path)
    sandbox = FakeSandbox(SandboxResult(exit_code=0, stdout="1 passed"))
    git_host = FakeGitHost()
    repo = tmp_path / "repo"
    app = build_dev_graph(
        store,
        sandbox,
        git_host,
        repo_root=repo,
        run_dir=tmp_path / "runstate",
        budget=Budget(cost_usd=10.0),
    )
    return (
        app,
        {
            "run_id": "dev-run-offline",
            "spec_version_id": version_id,
            "spec_run_id": "spec-run-1",
            "repo": str(repo),
            "outcome": "planned",
            "dev_attempt": 0,
        },
        git_host,
    )


class TestOfflineBlocksNetwork:
    """T030 — deterministic offline path completes with http frozen."""

    def test_full_offline_run_with_http_frozen(self, tmp_path, monkeypatch) -> None:
        http_calls = _freeze_http(monkeypatch)
        app, initial, git_host = _run_offline(tmp_path)
        result = app.invoke(initial)
        assert result["outcome"] == "delivered"
        assert isinstance(result["pr"], PullRequest)
        # No deterministic role reached out to the network.
        assert http_calls == [], f"offline run touched HTTP: {http_calls}"
