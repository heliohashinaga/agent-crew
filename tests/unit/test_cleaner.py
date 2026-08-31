"""Unit tests for the cleaner node (stubbed LLM, no network)."""

from agentcrew.agents.cleaner import build_cleaner_node


def test_cleaner_applies_semantic_rules_with_stub():
    cleaner = build_cleaner_node(
        chat=lambda _p: "# renamed\nresult = a + b", model="stub"
    )
    state = {
        "task": "x",
        "coder_output": "def add(a,b): return a+b",
        "cleaner_output": "",
        "error": None,
    }
    out = cleaner(state)
    assert out["cleaner_output"] == "# renamed\nresult = a + b"


def test_cleaner_fails_gracefully_on_model_error():
    def _boom(_prompt: str) -> str:
        raise RuntimeError("model down")

    node = build_cleaner_node(chat=_boom, model="stub")
    code = "def add(a, b):\n    return a + b"
    out = node({"task": "x", "coder_output": code, "cleaner_output": "", "error": None})
    # On model error the cleaner returns coder_output unchanged (graceful fallback).
    assert out["cleaner_output"] == code


def test_cleaner_without_llm_returns_code_unchanged():
    node = build_cleaner_node(model="stub")  # no chat injected -> no LLM
    code = "def f():\n    pass"
    out = node({"task": "x", "coder_output": code, "cleaner_output": "", "error": None})
    assert out["cleaner_output"] == code


def test_cleaner_returns_partial_update_only():
    node = build_cleaner_node(chat=lambda _p: "cleaned", model="stub")
    state = {"task": "x", "coder_output": "code", "cleaner_output": "", "error": None}
    out = node(state)
    assert set(out.keys()) == {"cleaner_output"}