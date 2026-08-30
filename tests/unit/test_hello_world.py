"""Unit tests for the hello-world node (deterministic, offline)."""

import pytest
from pydantic import ValidationError

from agentcrew.nodes.hello_world import build_hello_world_node
from agentcrew.nodes.models import HelloWorldNodeResult

pytestmark = pytest.mark.unit


def test_returns_deterministic_greeting_dict():
    node = build_hello_world_node()
    assert node.invoke("Ada") == {"input": "Ada", "greeting": "Hello, Ada!"}


def test_same_input_produces_same_output():
    node = build_hello_world_node()
    assert node.invoke("Ada") == node.invoke("Ada")


def test_strips_surrounding_whitespace():
    node = build_hello_world_node()
    assert node.invoke("  Ada  ") == {"input": "Ada", "greeting": "Hello, Ada!"}


def test_node_rejects_empty_input():
    node = build_hello_world_node()
    with pytest.raises(ValueError):
        node.invoke("")


def test_node_rejects_whitespace_only_input():
    node = build_hello_world_node()
    with pytest.raises(ValueError):
        node.invoke("   ")


def test_model_rejects_empty_input():
    with pytest.raises(ValidationError):
        HelloWorldNodeResult(input="", greeting="Hello, !")


def test_model_rejects_whitespace_only_input():
    with pytest.raises(ValidationError):
        HelloWorldNodeResult(input="   ", greeting="Hello,   !")