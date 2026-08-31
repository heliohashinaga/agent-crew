"""Contract tests for the agentcrew-code CLI (graph mocked, no network)."""

import json

import pytest

from agentcrew import coder_cli
from agentcrew.nodes import llm as llm_nodes

pytestmark = pytest.mark.contract


@pytest.fixture
def fake_key(monkeypatch):
    monkeypatch.setattr(llm_nodes, "provider_api_key", lambda provider: "sk-dummy")


@pytest.fixture
def fake_graph(monkeypatch):
    class _FakeGraph:
        def invoke(self, state):
            return {"coder_output": "raw", "cleaner_output": "cleaned"}

    monkeypatch.setattr(coder_cli, "_build_graph", lambda *a, **k: _FakeGraph())


def test_cli_prints_cleaned_code_exit_zero(fake_key, fake_graph, capsys):
    assert coder_cli.main(["write an add function"]) == 0
    assert capsys.readouterr().out == "cleaned\n"


def test_cli_json_output(fake_key, fake_graph, capsys):
    assert coder_cli.main(["x", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["coder_output"] == "raw"
    assert payload["cleaner_output"] == "cleaned"


@pytest.mark.parametrize(
    "argv",
    [
        [],  # missing task
        ["--provider", "bogus", "x"],  # unsupported provider
    ],
)
def test_cli_usage_errors_exit_one(argv, capsys):
    assert coder_cli.main(argv) == 1
    assert capsys.readouterr().out == ""


def test_cli_missing_key_returns_hint_exit_four(monkeypatch, capsys):
    monkeypatch.setattr(llm_nodes, "provider_api_key", lambda provider: "")
    assert coder_cli.main(["x"]) == 4
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "OPENROUTER_API_KEY" in captured.err


def test_cli_node_failure_exit_four(fake_key, monkeypatch, capsys):
    class _Boom:
        def invoke(self, state):
            raise RuntimeError("boom")

    monkeypatch.setattr(coder_cli, "_build_graph", lambda *a, **k: _Boom())
    assert coder_cli.main(["x"]) == 4
    assert capsys.readouterr().out == ""