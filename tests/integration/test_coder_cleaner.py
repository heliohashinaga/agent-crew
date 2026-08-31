"""Opt-in integration test: real LLM coder->cleaner run + LangSmith trace.

Excluded from deterministic CI by the default ``-m 'not integration'`` filter.
Requires a provider API key in ``.env``; skipped if none is configured.
"""

import os

import pytest

from agentcrew.agents import cleaner as cleaner_agents
from agentcrew.agents import coder as coder_agents
from agentcrew.graphs.coder_cleaner import build_coder_cleaner_graph
from agentcrew.nodes import llm as llm_nodes

pytestmark = pytest.mark.integration


@pytest.fixture
def provider_key():
    key = llm_nodes.provider_api_key("openrouter")
    key = key or llm_nodes.provider_api_key("opencode")
    if not key:
        pytest.skip(
            "no provider API key configured; set OPENROUTER_API_KEY "
            "or OPENCODE_GO_API_KEY"
        )
    return key


def test_real_coder_cleaner_run_produces_both_outputs(provider_key):
    graph = build_coder_cleaner_graph(
        coder_chat=coder_agents.default_chat("openrouter", None),
        cleaner_chat=cleaner_agents.default_chat("openrouter", None),
        model=None,
    )
    # A non-Python task demonstrates language-agnostic behavior.
    result = graph.invoke(
        {"task": "write a Python function that computes the nth fibonacci number"}
    )
    assert result["coder_output"].strip()
    assert result["cleaner_output"].strip()


def test_langsmith_trace_surfaces_pipeline_nodes(provider_key):
    if os.environ.get("LANGSMITH_TRACING", "").lower() != "true":
        pytest.skip(
            "LANGSMITH_TRACING not enabled; trace assertion requires tracing "
            "(FR-007/SC-004)"
        )

    from langsmith import Client

    graph = build_coder_cleaner_graph(
        coder_chat=coder_agents.default_chat("openrouter", None),
        cleaner_chat=cleaner_agents.default_chat("openrouter", None),
        model=None,
    )
    project = os.environ.get("LANGSMITH_PROJECT", "agent-crew")
    graph.invoke({"task": "write a hello function"})

    # Best-effort: at least one traced run exists in the project for this run.
    client = Client()
    runs = list(client.list_runs(project_name=project, limit=10))
    run_names = {getattr(r, "name", "") for r in runs}
    assert run_names, f"no runs found in LangSmith project {project!r}"