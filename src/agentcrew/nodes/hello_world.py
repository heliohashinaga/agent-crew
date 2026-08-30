"""Hello-world node — a standalone, offline, deterministic LangChain Runnable."""

from langchain_core.runnables import Runnable, RunnableLambda

from agentcrew.nodes.models import HelloWorldNodeResult


def _greet(raw_text: str) -> dict[str, str]:
    """Derive the deterministic greeting for a non-empty text input.

    Trims surrounding whitespace, then validates the trimmed input against
    ``HelloWorldNodeResult``. Empty/whitespace-only input raises ``ValueError``
    so callers can surface a usage error.
    """
    text = raw_text.strip()
    result = HelloWorldNodeResult(input=text, greeting=f"Hello, {text}!")
    return result.model_dump()


def build_hello_world_node() -> Runnable:
    """Return an offline, deterministic LangChain ``Runnable`` greeting node.

    This is the library seam later nodes (including LLM-backed ones) will use —
    same ``invoke()``/``stream()`` semantics, no model, network, or credentials.
    """
    return RunnableLambda(_greet)