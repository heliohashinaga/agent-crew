"""Structured data model for agentcrew nodes."""

from pydantic import BaseModel, Field, field_validator


class HelloWorldNodeResult(BaseModel):
    """Structured output of the hello-world node.

    Fields:
        input: The user-supplied, trimmed text (must be non-empty).
        greeting: The deterministic greeting derived from ``input``.
    """

    input: str = Field(description="User-provided text (trimmed, non-empty).")
    greeting: str = Field(description="Deterministic greeting derived from input.")

    @field_validator("input")
    @classmethod
    def _input_must_be_non_empty(cls, value: str) -> str:
        """Reject empty or whitespace-only input.

        Per the data model, ``input`` must be non-empty (trimmed) text. A blank
        string (including surrounding whitespace) is an input error.
        """
        if not value.strip():
            raise ValueError("input must be non-empty text")
        return value


class LLMNodeResult(BaseModel):
    """Structured output of the LLM-backed node.

    Fields:
        input: The user-supplied, trimmed prompt (must be non-empty).
        model: The Anthropic model identifier used for the completion.
        response: The model's text completion for ``input``.
    """

    input: str = Field(description="User-provided prompt (trimmed, non-empty).")
    model: str = Field(description="Anthropic model identifier used.")
    response: str = Field(description="Model text completion for input.")

    @field_validator("input")
    @classmethod
    def _input_must_be_non_empty(cls, value: str) -> str:
        """Reject empty or whitespace-only input."""
        if not value.strip():
            raise ValueError("input must be non-empty text")
        return value