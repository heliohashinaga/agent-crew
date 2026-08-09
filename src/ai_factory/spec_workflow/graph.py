"""Specification Workflow StateGraph (T021, FR-002/004/005/024).

The spec workflow is its own LangGraph ``StateGraph`` — a distinct
observable run (FR-024). Flow::

    START → spec_agent → requirements_reviewer ─(approved)→ human_approval
                              │  (amend, bounded)                 │
                              └──→ spec_agent
                                    ├─(approve)→ publish → END
                                    └─(defer)  → needs_clarification → END

- :func:`spec_agent` drafts a :class:`SpecVersion`; on reviewer rejection it
  amends with the reviewer's feedback (bounded cycles, FR-006).
- :func:`requirements_reviewer` validates (FR-004) and routes back to the
  agent, or on to the human gate.
- **human_approval** is a LangGraph ``interrupt()`` gate (FR-005): the run is
  ``under_review`` until a human approves; only then is it published.

The graph takes a :class:`FileSpecStore` so the approved spec is persisted
with a stable ``spec_version_id`` (FR-025). Nodes are network-free
(deterministic role cores).
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from ai_factory.shared.spec_store.handoff import publish_approved
from ai_factory.shared.spec_store.models import (
    ApprovalStatus,
    FeatureRequest,
    SpecVersion,
)
from ai_factory.shared.spec_store.store import FileSpecStore
from ai_factory.shared.state.checkpointer import build_in_memory_checkpointer
from ai_factory.spec_workflow.requirements_reviewer.reviewer import review
from ai_factory.spec_workflow.spec_agent.agent import draft_spec

# Bounded re-draft cycles per run (FR-006): never loop forever.
MAX_REVIEW_ROUNDS = 2

Outcome = str  # "approved" | "rejected" | "needs_clarification" | "drafting"


class SpecState(TypedDict):
    """Shared state flowing between spec-workflow nodes."""

    request: FeatureRequest
    spec: SpecVersion | None
    feedback: str
    review_rounds: int
    spec_run_id: str
    outcome: Outcome


def _spec_agent_node(state: SpecState) -> dict:
    assert state["request"] is not None
    feedback = state.get("feedback", "")
    spec = draft_spec(state["request"], feedback=feedback)
    spec.spec_run_id = state["spec_run_id"]
    return {
        "spec": spec,
        "feedback": "",
        "review_rounds": state["review_rounds"] + 1,
        "outcome": "drafting",
    }


def _requirements_reviewer_node(state: SpecState) -> dict:
    assert state["spec"] is not None
    verdict = review(state["spec"])
    return {"feedback": verdict.feedback}


def _route_after_review(state: SpecState) -> str:
    assert state["spec"] is not None
    verdict = review(state["spec"])
    if verdict.approved:
        return "human_approval"
    if state["review_rounds"] >= MAX_REVIEW_ROUNDS:
        return "reject"
    return "spec_agent"  # amend loop


def _human_approval_node(state: SpecState) -> dict:
    """Gate on FR-005: pause and ask a human before marking approved."""
    approved: bool = interrupt("Approve this spec version? (continue to publish)")
    if approved:
        return {"outcome": "approve"}
    return {"outcome": "needs_clarification"}


def _approve_node(state: SpecState, store: FileSpecStore) -> dict:
    assert state["spec"] is not None
    spec = state["spec"]
    spec.human_approved = True
    spec.approval_status = ApprovalStatus.APPROVED
    published = publish_approved(spec, store)
    return {"spec": published, "outcome": "approved"}


def _reject_node(state: SpecState) -> dict:
    return {"outcome": "rejected"}


def _clarify_node(state: SpecState) -> dict:
    """The run is paused/under_review waiting on the user (FR-006)."""
    if state.get("spec") is not None:
        state["spec"].approval_status = ApprovalStatus.UNDER_REVIEW
    return {"outcome": "needs_clarification"}


def build_spec_graph(store: FileSpecStore):
    """Compile and return the spec workflow graph bound to ``store``."""

    def approve(state: SpecState) -> dict:
        return _approve_node(state, store)

    g = StateGraph(SpecState)
    g.add_node("spec_agent", _spec_agent_node)
    g.add_node("requirements_reviewer", _requirements_reviewer_node)
    g.add_node("human_approval", _human_approval_node)
    g.add_node("approve", approve)
    g.add_node("reject", _reject_node)
    g.add_node("needs_clarification", _clarify_node)

    g.add_edge(START, "spec_agent")
    g.add_edge("spec_agent", "requirements_reviewer")
    g.add_conditional_edges(
        "requirements_reviewer",
        _route_after_review,
        {
            "human_approval": "human_approval",
            "spec_agent": "spec_agent",
            "reject": "reject",
        },
    )
    g.add_conditional_edges(
        "human_approval",
        lambda s: s["outcome"],
        {"approve": "approve", "needs_clarification": "needs_clarification"},
    )
    g.add_edge("approve", END)
    g.add_edge("reject", END)
    g.add_edge("needs_clarification", END)
    # Checkpointer enables the human-in-the-loop interrupt gate (dev/tests),
    # with our Pydantic models registered for clean checkpoint (de)serialization.
    return g.compile(checkpointer=build_in_memory_checkpointer())


__all__ = ["MAX_REVIEW_ROUNDS", "SpecState", "build_spec_graph"]
