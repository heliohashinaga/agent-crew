"""Structured data model for agentcrew nodes."""

from typing import TypedDict

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


class CoderOutput(BaseModel):
    """Structured output of the coder agent.

    Fields:
        task: The user-supplied, trimmed task (must be non-empty).
        model: The provider model id used to generate the code.
        code: The candidate code produced from ``task`` (any language).
    """

    task: str = Field(description="User-provided task (trimmed, non-empty).")
    model: str = Field(description="Provider model id used.")
    code: str = Field(description="Candidate code produced by the coder.")

    @field_validator("task")
    @classmethod
    def _task_must_be_non_empty(cls, value: str) -> str:
        """Reject empty or whitespace-only task."""
        if not value.strip():
            raise ValueError("task must be non-empty text")
        return value


class CleanerOutput(BaseModel):
    """Structured output of the cleaner agent.

    Fields:
        code: The input code passed through to the cleaner.
        refined: The code after applying semantic clean code standards.
        llm_refine_applied: Whether the LLM semantic refinement ran.
    """

    code: str = Field(description="The input code passed through.")
    refined: str = Field(description="Semantic-clean-code result.")
    llm_refine_applied: bool = Field(description="Whether LLM refinement ran.")


class TaskState(TypedDict):
    """Shared state passed between the coder and cleaner graph nodes.

    Keys:
        task: The user-supplied task text (non-empty).
        coder_output: Candidate code produced by the coder node.
        cleaner_output: Code after the cleaner node (semantic clean code).
        error: Optional failure message propagated to the CLI.
    """

    task: str
    coder_output: str
    cleaner_output: str
    error: str | None