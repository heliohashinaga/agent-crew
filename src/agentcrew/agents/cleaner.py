"""Cleaner agent: applies semantic clean code standards (LLM-backed, opt-in).

The node is a plain LangGraph node function: it receives the shared ``TaskState``
and returns a partial update setting ``cleaner_output``. It is explicitly NOT
responsible for formatting (FR-005) — formatting stays in Black/ruff, outside the
cleaner.

Semantics (language-agnostic):
- With an injected/configured ``chat``: prompt the LLM for semantic clean code
  (descriptive naming, small functions, removing redundant comments).
- If the LLM call fails, or no chat is configured, fall back gracefully to the
  input code unchanged (``cleaner_output = coder_output``).
"""

from __future__ import annotations

from collections.abc import Callable

from agentcrew.agents.clean_code_policy import CLEAN_CODE_POLICY
from agentcrew.nodes.llm import build_llm_node
from agentcrew.nodes.models import CleanerOutput, TaskState

Chat = Callable[[str], str]

# Generic semantic clean-code instruction; not tied to any language.
_PROMPT_TEMPLATE = (
    "You are a code-cleaner. Improve the code below with semantic clean-code "
    "standards. Do NOT reformat or change behavior. Keep the same language. "
    "Return ONLY the improved code.\n\n"
    "Standards:\n{policy}\n\n"
    "Code:\n```\n{code}\n```"
)


def default_chat(provider: str, model: str | None) -> Chat:
    """Build the default semantic-clean-code chat callable (prompt -> text).

    Backed by ``agentcrew.nodes.llm.build_llm_node``. The CLI passes this in for
    real refinement; when no chat is configured the cleaner passes code through
    unchanged (offline/graceful).
    """
    node = build_llm_node(provider, model=model)

    def chat(prompt: str) -> str:
        return str(node.invoke(prompt)["response"])

    return chat


def build_cleaner_node(
    *,
    chat: Chat | None = None,
    provider: str = "openrouter",
    model: str | None = None,
    policy: str = CLEAN_CODE_POLICY,
) -> Callable[[TaskState], dict[str, str]]:
    """Return a LangGraph node that fills ``cleaner_output`` via semantic clean code.

    ``chat=None`` means no LLM is configured -> code passes through unchanged.
    ``policy`` is the semantic clean-code standards text injected into the prompt
    (default: the bundled clean-code skill policy).
    """

    effective = chat if chat is not None else default_chat(provider, model)

    def cleaner_node(state: TaskState) -> dict[str, str]:
        code = state["coder_output"]
        refined = code
        applied = False
        if chat is not None:  # only attempt LLM when explicitly configured
            try:
                prompt = _PROMPT_TEMPLATE.format(policy=policy, code=code)
                refined = effective(prompt)
                applied = True
            except Exception:  # noqa: BLE001 - graceful fallback per spec
                refined = code
        CleanerOutput(code=code, refined=refined, llm_refine_applied=applied)
        return {"cleaner_output": refined}

    return cleaner_node