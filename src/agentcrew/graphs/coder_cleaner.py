"""Coder->Cleaner graph: a fixed linear LangGraph pipeline.

Orchestrates the two agents (coder -> cleaner) as a LangGraph ``StateGraph``:
``START -> coder -> cleaner -> END``. The graph is the composition seam: it wires
the standalone coder/cleaner library nodes together and never holds business
logic.

For offline testing, ``coder_chat`` / ``cleaner_chat`` inject stubbed chat
functions so no network/credentials are needed.
"""

from __future__ import annotations

from collections.abc import Callable

from langgraph.graph import END, START, StateGraph

from agentcrew.agents.cleaner import build_cleaner_node
from agentcrew.agents.coder import build_coder_node
from agentcrew.nodes.models import TaskState

Chat = Callable[[str], str]


def build_coder_cleaner_graph(
    *,
    coder_chat: Chat | None = None,
    cleaner_chat: Chat | None = None,
    provider: str = "openrouter",
    model: str | None = None,
    cleaner_policy: str | None = None,
):
    """Return a compiled ``StateGraph`` running coder before cleaner.

    ``cleaner_policy`` (optional) is injected into the cleaner's LLM prompt;
    when None the cleaner uses its bundled clean-code skill policy.
    """
    g = StateGraph(TaskState)
    cleaner = build_cleaner_node(
        chat=cleaner_chat, provider=provider, model=model, policy=cleaner_policy
    )
    g.add_node(
        "coder", build_coder_node(chat=coder_chat, provider=provider, model=model)
    )
    g.add_node("cleaner", cleaner)
    g.add_edge(START, "coder")
    g.add_edge("coder", "cleaner")
    g.add_edge("cleaner", END)
    return g.compile()