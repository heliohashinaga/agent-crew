"""Integration tests for the Development Workflow graph (T063/T065/T067/T069).

End-to-end: approved ``spec_version_id`` → planner → orchestrator →
code worker → code reviewer → (rework loop) → test engine → test runner
(in sandbox) → security reviewer → deliver (open PR, never merged, FR-012).

Runs network/container-free with :class:`FakeSandbox` and
:class:`FakeGitHost`. Test hooks (``hooks=[node_id]``) inject deterministic
failures to drive the rework and reject paths.
"""

from __future__ import annotations

import pytest

from ai_factory.dev_workflow.graph import build_dev_graph
from ai_factory.shared.git_host.client import FakeGitHost, PullRequest
from ai_factory.shared.sandbox.runner import FakeSandbox, SandboxResult
from ai_factory.shared.spec_store.handoff import publish_approved
from ai_factory.shared.spec_store.models import (
    AcceptanceCriterion,
    SpecVersion,
)
from ai_factory.shared.spec_store.store import FileSpecStore

pytestmark = pytest.mark.integration

APPROVABLE_SPEC = [
    ("Search returns the index of a found element", "test"),
]


def _store_with_approved_spec(tmp_path) -> tuple[FileSpecStore, str]:
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


def _run(
    tmp_path,
    *,
    sandbox_results=None,
    hooks=None,
    budget_cost=10.0,
    store=None,
    spec_version_id=None,
    run_id="dev-run-1",
):
    store, version_id = _store_with_approved_spec(tmp_path)
    spec_store = store or store
    version_id = spec_version_id or version_id
    sandbox = FakeSandbox(
        SandboxResult(exit_code=0, stdout="1 passed"),
        results=sandbox_results,
    )
    git_host = FakeGitHost()
    repo = tmp_path / "repo"
    app = build_dev_graph(
        spec_store,
        sandbox,
        git_host,
        repo_root=repo,
        run_dir=tmp_path / "runstate",
        budget=__import__("ai_factory").dev_workflow.models.Budget(
            cost_usd=budget_cost, tokens=None, time=None
        ),
        hooks=hooks,
    )
    initial = {
        "run_id": run_id,
        "spec_version_id": version_id,
        "spec_run_id": "spec-run-1",
        "repo": str(repo),
        "outcome": "planned",
        "dev_attempt": 0,
    }
    result = app.invoke(initial)
    return result, git_host, repo


def test_happy_path_delivers_pr(tmp_path) -> None:
    """T063: approved spec flows to a delivered, non-merged PR."""
    result, git_host, repo = _run(tmp_path)
    assert result["outcome"] == "delivered"
    assert isinstance(result["pr"], PullRequest)
    assert git_host.last_pr is not None
    assert git_host.last_pr.base == "main"  # merged only by a human (FR-012)
    assert (repo / "test_suite.py").exists()
    assert any(str(p).endswith(".py") for p in (repo).iterdir())


def test_rework_loop_fails_then_delivers(tmp_path) -> None:
    """T065: failing tests drive a bounded rework; then it delivers."""
    result, git_host, repo = _run(
        tmp_path,
        sandbox_results=[
            SandboxResult(exit_code=1, stdout="FAILED test_suite.py::test_ac_1 - boom"),
            SandboxResult(exit_code=0, stdout="1 passed"),
        ],
    )
    assert result["outcome"] == "delivered"
    assert result["dev_attempt"] == 1  # one rework happened
    assert git_host.last_pr is not None


def test_security_reject_blocks_pr(tmp_path) -> None:
    """T067/FR-014: a security finding means NO PR until fixed/re-audited."""

    def sabotage(update, state):
        secret_file = state["repo"] + "/leak.py"
        with open(secret_file, "w", encoding="utf-8") as fh:
            fh.write("token='ghp_abcdef0123456789'\n")
        return update

    result, git_host, _ = _run(tmp_path, hooks={"code_worker": sabotage})
    assert result["outcome"] in ("failed", "stopped_human")
    assert git_host.last_pr is None
    assert result.get("security_verdict") is not None
    assert result["security_verdict"].approved is False
    assert any("security" in i.category for i in (result.get("issues") or []))


def test_persistent_failure_reaches_stopped_human(tmp_path) -> None:
    """T079/080/FR-015: bounded re-planning exhausts ⇒ stopped-human (exit 5)."""
    result, git_host, _ = _run(
        tmp_path,
        sandbox_results=[
            SandboxResult(
                exit_code=1, stdout="FAILED test_suite.py::test_ac_1 - boom " * 5
            ),
        ],
    )
    assert result["outcome"] == "stopped_human"
    assert git_host.last_pr is None
    assert (result.get("replan_count") or 0) >= 1


def test_soft_budget_never_blocks_delivery(tmp_path) -> None:
    """T069/FR-019: overspending warns and sets the flag but still delivers."""
    result, _, _ = _run(tmp_path, budget_cost=0.000001)
    assert result["outcome"] == "delivered"
    assert result.get("overspend") is True


def test_resume_skips_completed_checkpoints(tmp_path) -> None:
    """T067/FR-020: a resume skips phases already checkpointed."""
    from ai_factory.dev_workflow.graph import build_dev_graph
    from ai_factory.shared.git_host.client import FakeGitHost
    from ai_factory.shared.sandbox.runner import FakeSandbox, SandboxResult
    from ai_factory.shared.state.checkpointer import CheckpointStore

    store, version_id = _store_with_approved_spec(tmp_path)
    repo = tmp_path / "repo"
    run_dir = tmp_path / "runstate"
    sandbox = FakeSandbox(SandboxResult(exit_code=0, stdout="1 passed"))
    git_host = FakeGitHost()

    app = build_dev_graph(
        store, sandbox, git_host, repo_root=repo, run_dir=run_dir, resume=True
    )
    initial = {
        "run_id": "resume-run",
        "spec_version_id": version_id,
        "spec_run_id": "spec-run-1",
        "repo": str(repo),
        "outcome": "planned",
        "dev_attempt": 0,
    }
    assert app.invoke(initial)["outcome"] == "delivered"

    ckpts = CheckpointStore(run_dir / "checkpoints")
    assert ckpts.is_completed("resume-run", "deliver")
    # A second resume run replays from checkpoints and still lands delivered.
    again = app.invoke(initial)
    assert again["outcome"] == "delivered"


def test_transient_failure_retries_then_delivers(tmp_path) -> None:
    """T075/FR-014: transient/infra failures are retried with backoff."""
    from ai_factory.shared.sandbox.runner import SandboxResult

    fail = SandboxResult(
        exit_code=1, stdout="FAILED test_suite.py::test_ac_1 - docker network timeout"
    )
    result, git_host, _ = _run(
        tmp_path,
        sandbox_results=[
            fail,
            fail,
            fail,
            SandboxResult(exit_code=0, stdout="1 passed"),
        ],
    )
    assert result["outcome"] == "delivered"
    assert git_host.last_pr is not None
    categories = [i.category for i in (result.get("issues") or [])]
    assert any("infrastructure" in c or "third_party" in c for c in categories)
