"""Contract tests for the LLM CLI (library<->CLI seam).

The LLM CLI reaches the network, so these tests assert the CLI<->library
contract without making real API calls: the node and the key check are
mocked/stubbed. The real end-to-end call is exercised manually / via the
``live`` marker.
"""

import json
import subprocess
import sys

import pytest

from agentcrew import llm_cli
from agentcrew.nodes import llm as llm_nodes

pytestmark = pytest.mark.contract


@pytest.fixture
def fake_key(monkeypatch):
    """Pretend the openrouter provider has a key configured."""
    monkeypatch.setattr(llm_nodes, "provider_api_key", lambda provider: "sk-dummy")


def test_cli_emits_response_on_stdout_with_exit_zero(monkeypatch, capsys, fake_key):
    class _FakeNode:
        def invoke(self, text):
            return {"input": text, "model": "m", "response": "Hello there!"}

    monkeypatch.setattr(llm_cli, "build_llm_node", lambda *a, **k: _FakeNode())
    code = llm_cli.main(["hello"])
    assert code == 0
    assert capsys.readouterr().out == "Hello there!\n"


def test_cli_json_output(monkeypatch, capsys, fake_key):
    class _FakeNode:
        def invoke(self, text):
            return {"input": text, "model": "claude-x", "response": "hi"}

    monkeypatch.setattr(llm_cli, "build_llm_node", lambda *a, **k: _FakeNode())
    code = llm_cli.main(["hello", "--format", "json"])
    assert code == 0
    assert json.loads(capsys.readouterr().out) == {
        "input": "hello",
        "model": "claude-x",
        "response": "hi",
    }


@pytest.mark.parametrize(
    "argv",
    [
        [],  # missing text
        ["--provider", "bogus", "x"],  # unsupported provider
    ],
)
def test_cli_usage_errors_exit_one(argv, capsys):
    code = llm_cli.main(argv)
    assert code == 1
    assert capsys.readouterr().out == ""


def test_cli_missing_key_returns_helpful_error_exit_four(monkeypatch, capsys):
    # No key configured for openrouter -> fail before any network call.
    monkeypatch.setattr(llm_nodes, "provider_api_key", lambda provider: "")
    code = llm_cli.main(["hello"])
    assert code == 4
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "OPENROUTER_API_KEY" in captured.err


def test_cli_runtime_failure_exit_four(monkeypatch, capsys, fake_key):
    class _ExplodingNode:
        def invoke(self, text):
            raise RuntimeError("boom")

    monkeypatch.setattr(llm_cli, "build_llm_node", lambda *a, **k: _ExplodingNode())
    code = llm_cli.main(["hello"])
    assert code == 4
    assert capsys.readouterr().out == ""


def test_console_module_smoke_end_to_end_missing_key():
    """Real entry point: without a key it should exit 4 with a clear hint."""
    result = subprocess.run(
        [sys.executable, "-m", "agentcrew.llm_cli", "hello"],
        capture_output=True,
        text=True,
        check=False,
        # Hermetic: force keys empty so the real .env cannot make this test
        # attempt a real (networked) call.
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": "",
            "OPENROUTER_API_KEY": "",
            "OPENCODE_GO_API_KEY": "",
        },
    )
    assert result.returncode == 4
    assert "OPENROUTER_API_KEY" in result.stderr