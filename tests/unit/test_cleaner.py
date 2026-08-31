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


def test_cleaner_injects_policy_into_prompt():
    prompts: list[str] = []

    def spy(prompt: str) -> str:
        prompts.append(prompt)
        return "cleaned"

    node = build_cleaner_node(chat=spy, model="stub", policy="CUSTOM-POLICY")
    state = {"task": "x", "coder_output": "code", "cleaner_output": "", "error": None}
    node(state)
    assert prompts, "cleaner should call the LLM when a chat is provided"
    assert "CUSTOM-POLICY" in prompts[0]


def test_read_policy_strips_frontmatter(tmp_path):
    from agentcrew.agents.clean_code_policy import read_clean_code_policy

    f = tmp_path / "SKILL.md"
    f.write_text("---\nname: clean-code\n---\nApply good names.", encoding="utf-8")
    assert read_clean_code_policy(source=f) == "Apply good names."


def test_bundled_policy_excludes_formatting():
    from agentcrew.agents.clean_code_policy import CLEAN_CODE_POLICY

    lower = CLEAN_CODE_POLICY.lower()
    assert "descriptive, intent-revealing names" in lower
    assert "changes" not in lower.split("reformat")[0]  # no formatting duties