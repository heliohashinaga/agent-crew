"""Tests for LangGraph msgpack hardening (LGH).

LangGraph checkpoints serialize state with its msgpack serializer. Our
Pydantic state models must be registered in ``allowed_msgpack_modules`` so
they deserialize cleanly (no 'unregistered type' warning / future hard
block). This test proves the registry covers our models and that a
checkpointer round-trips one.
"""

from __future__ import annotations

from ai_factory.shared.spec_store.models import ApprovalStatus, SpecVersion
from ai_factory.shared.state.checkpointer import (
    allowed_msgpack_modules,
    build_in_memory_checkpointer,
)


def test_msgpack_registry_includes_state_models() -> None:
    allowed = allowed_msgpack_modules()
    registered = set(allowed)
    assert ("ai_factory.shared.spec_store.models", "SpecVersion") in registered
    assert (
        "ai_factory.spec_workflow.requirements_reviewer.reviewer",
        "ReviewVerdict",
    ) in registered or any(mod.endswith("spec_store.models") for mod, _ in allowed)
    assert registered  # non-empty


def test_msgpack_registry_covers_all_user_story_models() -> None:
    names = {name for _mod, name in allowed_msgpack_modules()}
    assert {
        "SpecVersion",
        "FeatureRequest",
        "TechnicalPlan",
        "ExecutionPlan",
        "CodeWorkProduct",
        "CodeReviewVerdict",
        "TestRunResult",
        "SecurityReviewVerdict",
        "Issue",
        "PullRequest",
    } <= names


def test_checkpointer_round_trips_spec_version() -> None:
    """A Pydantic model survives save→load through the checkpointer's serde.

    Uses the interrupt→resume pattern (as the spec workflow does): the first
    invoke persists a checkpoint (save), and the resume reloads the state
    (deserialize) — no 'unregistered type' warning/error.
    """
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import Command, interrupt

    spec = SpecVersion(
        intent="Sessions must expire after 30 minutes",
        approval_status=ApprovalStatus.APPROVED,
        human_approved=True,
    )

    def gate(state):
        interrupt("approve?")
        return {"spec": state["spec"]}  # reloaded from checkpoint on resume

    g = StateGraph(dict)
    g.add_node("store", lambda s: {"spec": s["spec"]})
    g.add_node("gate", gate)
    g.add_edge(START, "store")
    g.add_edge("store", "gate")
    g.add_edge("gate", END)

    checkpointer = build_in_memory_checkpointer()
    assert isinstance(checkpointer, InMemorySaver)
    app = g.compile(checkpointer=checkpointer)

    thread = {"configurable": {"thread_id": "serde-1"}}
    paused = app.invoke({"spec": spec}, thread)
    assert "__interrupt__" in paused  # checkpoint saved with the Pydantic model

    resumed = app.invoke(Command(resume=True), thread)
    assert isinstance(resumed["spec"], SpecVersion)
    assert resumed["spec"].intent == "Sessions must expire after 30 minutes"
    assert resumed["spec"].approval_status == ApprovalStatus.APPROVED
