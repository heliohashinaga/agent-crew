"""Development Workflow StateGraph (T064, FR-009/011/012/021/023).

Consumes an approved :class:`SpecVersion` BY REFERENCE (``spec_version_id``)
and drives the pipeline to a merge-ready, non-merged pull request
(FR-012)::

    START → load_spec → technical_planner → orchestrator → code_worker
      → code_reviewer ─(rework, bounded)→ code_worker ─(approved)→
      test_engineer → test_runner(sandbox) ─(rework loop)→ security_reviewer
      → deliver(PR) → END        ─(fail)→ failed → END

- No human gate between planning and execution (FR-023).
- Phase boundaries are checkpointed (FR-020); with ``resume=True`` completed
  phases are skipped.
- The budget is soft (FR-019): overspend is flagged, never aborts.
- Test hooks (``hooks[node_id]``) and a fake sandbox/git host keep every
  test deterministic and network-free.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ai_factory.dev_workflow.code_reviewer.reviewer import review as code_review
from ai_factory.dev_workflow.code_worker.worker import implement
from ai_factory.dev_workflow.issues.policy import (
    classify_issue,
    is_deterministic,
    issue_retry_policy,
)
from ai_factory.dev_workflow.models import Budget, RetryAttempt
from ai_factory.dev_workflow.orchestrator.budget import BudgetTracker
from ai_factory.dev_workflow.orchestrator.orchestrator import (
    bump_for_retry,
    plan_from_technical_plan,
)
from ai_factory.dev_workflow.orchestrator.orchestrator import plan as plan_execution
from ai_factory.dev_workflow.security_reviewer.reviewer import review as security_review
from ai_factory.dev_workflow.technical_planner.planner import produce_plan
from ai_factory.dev_workflow.test_engineer.engineer import build_test_suite
from ai_factory.dev_workflow.test_runner.runner import run_tests
from ai_factory.shared.git_host.client import GitHostClient, PullRequest
from ai_factory.shared.sandbox.runner import Sandbox
from ai_factory.shared.spec_store.handoff import load_spec_by_ref
from ai_factory.shared.state.checkpointer import CheckpointStore
from ai_factory.shared.telemetry.record import DevRoleInvocation, TelemetryRecord
from ai_factory.shared.telemetry.store import FileTelemetryStore

MAX_REWORK = 2
MAX_REPLAN = 2  # bound auto re-plans before escalating to a human (T079/080)

# role-name telemetry labels per graph node
_NODE_ROLE = {
    "technical_planner": "technical_planner",
    "orchestrator": "orchestrator",
    "code_worker": "code_worker",
    "code_reviewer": "code_reviewer",
    "test_engineer": "test_engineer",
    "test_runner": "test_runner",
    "security_reviewer": "security_reviewer",
    "deliver": "orchestrator",
}

# Dev roles that carry a valid `DevRoleInvocation.role` literal. Any node not
# in this set (e.g. `load_spec`, `fail`, `handle_failure`) is a control-flow
# node, not a capability; ``_telemetry`` skips it (FR-015).
_VALID_DEV_ROLES = frozenset(_NODE_ROLE.values())


class DevState(TypedDict):
    run_id: str
    spec_version_id: str
    spec_run_id: str
    repo: str
    spec: Any | None
    plan: Any | None
    exec_plan: Any | None
    code_product: Any | None
    code_verdict: Any | None
    test_product: Any | None
    test_result: Any | None
    security_verdict: Any | None
    pr: PullRequest | None
    outcome: str
    dev_attempt: int
    overspend: bool
    error: str | None
    issues: list
    issue_counts: dict
    replan_count: int
    last_error: str | None
    security_audit_count: int
    replanned: bool


def _identity(update: dict, _state: dict) -> dict:
    return update


def _attr(obj, name: str, default=None):
    """Read an attribute from a model OR a plain dict (resume snapshots)."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def build_dev_graph(
    spec_store,
    sandbox: Sandbox,
    git_host: GitHostClient,
    *,
    repo_root: str | Path,
    run_dir: str | Path | None = None,
    budget: Budget | None = None,
    telemetry_store: FileTelemetryStore | None = None,
    hooks: dict[str, Callable[[dict, dict], dict]] | None = None,
    resume: bool = False,
):
    """Compile the dev workflow graph bound to its adapters and seams."""
    repo_root = Path(repo_root)
    run_dir = Path(run_dir) if run_dir else repo_root.parent / "runstate"
    budget_tracker = BudgetTracker(budget or Budget())
    ckpts = CheckpointStore(run_dir / "checkpoints")
    hooks = hooks or {}

    def _telemetry(node_id: str, state: DevState, result: dict) -> None:
        if telemetry_store is None:
            return
        role = _NODE_ROLE.get(node_id, node_id)
        if role not in _VALID_DEV_ROLES:
            # control-flow node (load_spec/fail/handle_failure): no capability
            # telemetry.
            return
        ok = result.get("outcome") not in ("failed",) and not (
            isinstance(result.get("code_verdict"), object)
            and getattr(result.get("code_verdict"), "approved", True) is False
        )
        telemetry_store.add(
            state["run_id"],
            DevRoleInvocation(
                role=role,  # type: ignore[arg-type]
                model="fake",
                capability_level="standard",
                telemetry=TelemetryRecord(
                    result="pass" if ok else "fail",
                    overspend=budget_tracker.overspend_flag,
                ),
            ),
        )

    def _wrap(phase: str, fn: Callable[[DevState], dict]) -> Callable[[DevState], dict]:
        def node(state: DevState) -> dict:
            if resume and ckpts.is_completed(state["run_id"], phase):
                snap = ckpts.load(state["run_id"], phase) or {}
                return dict(snap)
            update = fn(state)
            update = hooks.get(phase, _identity)(update, state)
            _telemetry(phase, state, update)
            ckpts.save(state["run_id"], phase, _dump(update))
            return update

        return node

    def _dump(value: dict) -> dict:
        out: dict = {}
        for k, v in value.items():
            if hasattr(v, "model_dump"):
                out[k] = v.model_dump()
            elif isinstance(v, list) and v and hasattr(v[0], "model_dump"):
                out[k] = [i.model_dump() for i in v]
            else:
                out[k] = v
        return out

    # ---- node bodies -------------------------------------------------------
    def load_spec(state: DevState) -> dict:
        if state.get("plan") is not None:
            # Folder-driven run: the TechnicalPlan was injected at the start.
            return {}
        spec = load_spec_by_ref(state["spec_version_id"], spec_store)
        if spec is None:
            return {
                "outcome": "failed",
                "error": f"unknown spec_version_id {state['spec_version_id']!r}",
            }
        return {"spec": spec}

    def route_loaded(state: DevState) -> str:
        if state.get("plan") is not None:
            return "orchestrator"
        return "planner" if state.get("spec") is not None else "fail"

    def planner(state: DevState) -> dict:
        return {"plan": produce_plan(state["spec"])}

    def orchestrator(state: DevState) -> dict:
        if state.get("spec") is not None:
            return {"exec_plan": plan_execution(state["spec"], budget or Budget())}
        return {
            "exec_plan": plan_from_technical_plan(state["plan"], budget or Budget())
        }

    def code_worker(state: DevState) -> dict:
        product = implement(state["plan"], Path(state["repo"]))
        return {"code_product": product}

    def code_reviewer(state: DevState) -> dict:
        verdict = code_review(state["code_product"], state["plan"], Path(state["repo"]))
        return {
            "code_verdict": verdict,
            "last_error": verdict.feedback or "code review failed",
        }

    def rework(state: DevState) -> dict:
        # Raise the failing role's capability one step per retry (FR-015).
        bumped = bump_for_retry(state["exec_plan"], "code_worker")
        return {"exec_plan": bumped, "dev_attempt": state["dev_attempt"] + 1}

    def route_reviewed(state: DevState) -> str:
        if _attr(state["code_verdict"], "approved"):
            return "test_engineer"
        if state["dev_attempt"] < MAX_REWORK:
            return "rework"
        return "handle_failure"

    def test_engineer(state: DevState) -> dict:
        product = build_test_suite(state["plan"], Path(state["repo"]))
        return {"test_product": product}

    def test_runner(state: DevState) -> dict:
        budget_tracker.charge(cost=0.001, tokens=100, time=5)
        suites = None
        result = run_tests(Path(state["repo"]), sandbox, suites=suites)  # type: ignore[arg-type]
        return {
            "test_result": result,
            "last_error": ("; ".join(result.failures) or "tests failed")
            if not result.passed
            else "",
        }

    def route_tests(state: DevState) -> str:
        if _attr(state["test_result"], "passed"):
            return "security_reviewer"
        if state["dev_attempt"] < MAX_REWORK:
            return "rework"
        return "handle_failure"

    def security_reviewer(state: DevState) -> dict:
        verdict = security_review(Path(state["repo"]))
        return {
            "security_verdict": verdict,
            "last_error": ("; ".join(verdict.findings) or "security review failed")
            if not verdict.approved
            else "",
        }

    def route_security(state: DevState) -> str:
        if _attr(state["security_verdict"], "approved"):
            return "deliver"
        return "handle_failure"

    def deliver(state: DevState) -> dict:
        spec = state.get("spec")
        intent = spec.intent[:60] if spec else state.get("spec_version_id", "")
        adr_line = ""
        if state["plan"] is not None and state["plan"].adr is not None:
            adr_line = f"\nADR: {state['plan'].adr.title}"
        run_ref = (
            f" (from {state['spec_run_id']})"
            if state.get("spec_run_id")
            else ""
        )
        body = (
            f"AI Dev Factory delivery for folder {state['spec_version_id']}"
            f"{run_ref}.\n"
            f"Goal: {intent}{adr_line}\n"
            "Test result: "
            f"{'passed' if _attr(state['test_result'], 'passed') else 'failed'}\n"
            "Security: "
            f"{'passed' if _attr(state['security_verdict'], 'approved') else 'failed'}"
        )
        pr = git_host.open_pr(
            title=f"feat: {intent}",
            body=body,
            head=f"ai-factory/{state['run_id']}",
            base="main",
        )
        return {
            "pr": pr,
            "outcome": "delivered",
            "overspend": budget_tracker.overspend_flag,
        }

    def fail(state: DevState) -> dict:
        return {
            "outcome": "failed",
            "overspend": budget_tracker.overspend_flag,
            "error": None,
        }

    # ---- US3 runtime issue handling (FR-013/014/015) ------------------------
    def handle_failure(state: DevState) -> dict:
        """Classify the runtime failure and record a bounded Issue (FR-013)."""
        text = state.get("last_error") or "execution failure"
        issue = classify_issue(text)
        counts = dict(state.get("issue_counts") or {})
        counts[issue.category] = counts.get(issue.category, 0) + 1
        issues = list(state.get("issues") or []) + [issue]
        return {"issues": issues, "issue_counts": counts}

    def route_failure(state: DevState) -> str:
        issue = state["issues"][-1]
        cat = issue.category
        counts = (state.get("issue_counts") or {}).get(cat, 1)
        policy = issue_retry_policy(cat)
        if cat == "security":
            if (state.get("security_audit_count") or 0) < policy["max_retries"]:
                return "security_fix"
            return "replan"
        if counts <= policy["max_retries"]:
            return "rework" if is_deterministic(cat) else "retry_backoff"
        return "replan"

    def retry_backoff(state: DevState) -> dict:
        """Record an exponential-backoff retry for a transient issue (FR-014).

        No real sleep: the computed backoff interval is recorded on the issue
        for observability and test determinism.
        """
        issue = state["issues"][-1]
        policy = issue_retry_policy(issue.category)
        n = len(issue.retry_attempts)
        issue.retry_attempts.append(
            RetryAttempt(
                attempt=n + 1,
                outcome="retrying",
                note=f"backoff {policy['backoff_seconds'] * (2**n)}s",
            )
        )
        return {"issues": list(state["issues"])}

    def security_fix(state: DevState) -> dict:
        """CRITICAL security: halt, immediate fix, then full re-audit (FR-014)."""
        return {
            "security_audit_count": (state.get("security_audit_count") or 0) + 1,
            "pending_security_fix": True,
        }

    def replan(state: DevState) -> dict:
        """Auto re-plan via the Technical Planner (FR-015)."""
        try:
            plan = (
                produce_plan(state["spec"])
                if state.get("spec") is not None
                else state["plan"]
            )
            return {
                "plan": plan,
                "replan_count": (state.get("replan_count") or 0) + 1,
                "replanned": True,
                "dev_attempt": 0,
            }
        except Exception as exc:  # noqa: BLE001
            return {"replanned": False, "error": f"replan failed: {exc}"}

    def route_replanned(state: DevState) -> str:
        if state.get("replanned") and (state.get("replan_count") or 0) <= MAX_REPLAN:
            return "orchestrator"
        return "stop_human"

    def stop_human(state: DevState) -> dict:
        """Re-planning failed/limit reached: hand to a human (exit 5, FR-015)."""
        return {
            "outcome": "stopped_human",
            "overspend": budget_tracker.overspend_flag,
            "error": state.get("error") or "re-planning exhausted; human required",
            "replanned": False,
        }

    # ---- graph --------------------------------------------------------------
    g = StateGraph(DevState)
    for node_id in (
        "load_spec",
        "planner",
        "orchestrator",
        "code_worker",
        "code_reviewer",
        "rework",
        "test_engineer",
        "test_runner",
        "security_reviewer",
        "deliver",
        "fail",
        "handle_failure",
        "retry_backoff",
        "security_fix",
        "replan",
        "stop_human",
    ):
        fn = {
            "load_spec": load_spec,
            "planner": planner,
            "orchestrator": orchestrator,
            "code_worker": code_worker,
            "code_reviewer": code_reviewer,
            "rework": rework,
            "test_engineer": test_engineer,
            "test_runner": test_runner,
            "security_reviewer": security_reviewer,
            "deliver": deliver,
            "fail": fail,
            "handle_failure": handle_failure,
            "retry_backoff": retry_backoff,
            "security_fix": security_fix,
            "replan": replan,
            "stop_human": stop_human,
        }[node_id]
        g.add_node(node_id, _wrap(node_id, fn))

    g.add_edge(START, "load_spec")
    g.add_conditional_edges(
        "load_spec",
        route_loaded,
        {"planner": "planner", "orchestrator": "orchestrator", "fail": "fail"},
    )
    g.add_edge("planner", "orchestrator")
    g.add_edge("orchestrator", "code_worker")
    g.add_edge("rework", "code_worker")
    g.add_edge("code_worker", "code_reviewer")
    g.add_conditional_edges(
        "code_reviewer",
        route_reviewed,
        {
            "test_engineer": "test_engineer",
            "rework": "rework",
            "handle_failure": "handle_failure",
        },
    )
    g.add_edge("test_engineer", "test_runner")
    g.add_conditional_edges(
        "test_runner",
        route_tests,
        {
            "security_reviewer": "security_reviewer",
            "rework": "rework",
            "handle_failure": "handle_failure",
        },
    )
    g.add_conditional_edges(
        "security_reviewer",
        route_security,
        {"deliver": "deliver", "handle_failure": "handle_failure"},
    )
    g.add_conditional_edges(
        "handle_failure",
        route_failure,
        {
            "rework": "rework",
            "retry_backoff": "retry_backoff",
            "security_fix": "security_fix",
            "replan": "replan",
        },
    )
    g.add_edge("retry_backoff", "rework")
    g.add_edge("security_fix", "code_worker")
    g.add_conditional_edges(
        "replan",
        route_replanned,
        {"orchestrator": "orchestrator", "stop_human": "stop_human"},
    )
    g.add_edge("deliver", END)
    g.add_edge("fail", END)
    g.add_edge("stop_human", END)
    return g.compile()


__all__ = ["DevState", "MAX_REWORK", "build_dev_graph"]
