"""Unit tests for the coder node (stubbed model, no network)."""

from agentcrew.agents.coder import build_coder_node


def _node():
    code = "def add(a, b):\n    return a + b"
    return build_coder_node(chat=lambda _p: code, model="stub")


def test_coder_wires_task_to_coder_output():
    node = _node()
    out = node({"task": "write an add function"})
    assert out["coder_output"] == "def add(a, b):\n    return a + b"


def test_coder_is_language_agnostic():
    # A non-Python task is just text passed through the stub -> no language assumption.
    node = _node()
    out = node({"task": "export a React form component"})
    assert out["coder_output"].startswith("def add")


def test_coder_rejects_blank_task():
    node = _node()
    try:
        node({"task": "   "})
    except ValueError:
        return
    raise AssertionError("blank task should raise ValueError")


def test_coder_returns_partial_update_only():
    node = _node()
    out = node({"task": "x", "coder_output": "", "cleaner_output": "", "error": None})
    # Node returns only the key it changes.
    assert set(out.keys()) == {"coder_output"}