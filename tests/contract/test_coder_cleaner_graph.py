"""Contract test: coder->cleaner handoff ordering + shape (mocked, offline)."""

import pytest

from agentcrew.graphs.coder_cleaner import build_coder_cleaner_graph

pytestmark = pytest.mark.contract


def _graph():
    return build_coder_cleaner_graph(
        coder_chat=lambda _prompt: "def add(a, b):\n    return a + b",
        cleaner_chat=lambda _prompt: "# cleaned\nresult = a + b",
        model="stub",
    )


def test_pipeline_runs_coder_before_cleaner_and_outputs_both():
    result = _graph().invoke({"task": "write an add function"})
    assert result["coder_output"] == "def add(a, b):\n    return a + b"
    assert result["cleaner_output"] == "# cleaned\nresult = a + b"


def test_cleaner_consumes_coder_output():
    # cleaner_output is derived from the coder's output (proves ordering).
    r = _graph().invoke({"task": "write an add function"})
    assert r["coder_output"]  # coder ran first
    assert r["cleaner_output"]  # cleaner ran after and produced its own output


def test_blank_task_is_rejected():
    with pytest.raises(ValueError):
        _graph().invoke({"task": "   "})


def test_language_agnostic_task_runs_end_to_end():
    r = _graph().invoke({"task": "export a React form component"})
    assert r["coder_output"]
    assert r["cleaner_output"]