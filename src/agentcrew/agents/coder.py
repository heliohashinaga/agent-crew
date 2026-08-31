"""Coder agent: produces candidate code from a task (language-agnostic, LLM-backed).

The node is a plain LangGraph node function: it receives the shared ``TaskState``
and returns a partial update setting ``coder_output``. The underlying chat is
injectable (``chat=...``) so tests can stub it without network; by default it is
built from the existing ``agentcrew.nodes.llm`` provider infra.
"""

from __future__ import annotations

from collections.abc import Callable

from agentcrew.nodes.llm import build_llm_node
from agentcrew.nodes.models import CoderOutput, TaskState

Chat = Callable[[str], str]

# Language-agnostic: the task itself names the desired language; the prompt does
# not assume one.
_PROMPT = (
    "You are a coding agent. Write candidate code for the task below in the "
    "language the task requests. Return ONLY the code with no explanation.\n\n"
    "Task:\n{task}"
)


def default_chat(provider: str, model: str | None) -> Chat:
    """Build the default chat callable (prompt -> code/response text).

    Backed by ``agentcrew.nodes.llm.build_llm_node`` (OpenRouter/OpenCode Go).
    Used by the CLI for real runs; tests inject stubs instead.
    """
    node = build_llm_node(provider, model=model)

    def chat(prompt: str) -> str:
        return str(node.invoke(prompt)["response"])

    return chat


def build_coder_node(
    *,
    chat: Chat | None = None,
    provider: str = "openrouter",
    model: str | None = None,
) -> Callable[[TaskState], dict[str, str]]:
    """Return a LangGraph node that fills ``coder_output`` from ``task``."""

    effective = chat if chat is not None else default_chat(provider, model)

    def coder_node(state: TaskState) -> dict[str, str]:
        task = state["task"]
        # Validate input (raises ValueError on blank task).
        CoderOutput(task=task, model=model or provider, code="")
        code = effective(_PROMPT.format(task=task))
        return {"coder_output": code}

    return coder_node