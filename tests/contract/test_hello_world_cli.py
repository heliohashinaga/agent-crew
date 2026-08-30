"""Contract tests for the hello-world CLI (offline library<->CLI seam).

These are marked @pytest.mark.contract so they run under plain `uv run pytest`
and are not excluded by the default `-m 'not integration'` filter.
"""

import json
import subprocess
import sys

import pytest

from agentcrew import cli

pytestmark = pytest.mark.contract


def test_cli_returns_greeting_on_stdout_with_exit_zero(monkeypatch, capsys):
    code = cli.main(["hello", "world"])
    assert code == 0
    assert capsys.readouterr().out == "Hello, world!\n"


def test_cli_json_output(monkeypatch, capsys):
    code = cli.main(["hello", "world", "--format", "json"])
    out = capsys.readouterr().out
    assert code == 0
    assert json.loads(out) == {"input": "world", "greeting": "Hello, world!"}


@pytest.mark.parametrize(
    "argv",
    [
        [],  # missing text
        ["hello"],  # hello verb but no text
        ["hello", ""],  # empty text
        ["hello", "   "],  # whitespace-only text
    ],
)
def test_cli_usage_errors_exit_one(argv, monkeypatch, capsys):
    code = cli.main(argv)
    assert code == 1
    assert capsys.readouterr().out == ""


def test_cli_runtime_failure_exit_four(monkeypatch, capsys):
    class _ExplodingNode:
        def invoke(self, text):
            raise RuntimeError("boom")

    monkeypatch.setattr(cli, "build_hello_world_node", lambda: _ExplodingNode())
    code = cli.main(["hello", "world"])
    assert code == 4
    assert capsys.readouterr().out == ""


def test_console_module_smoke_end_to_end():
    """Run the real `python -m agentcrew.cli` entry point end-to-end."""
    result = subprocess.run(
        [sys.executable, "-m", "agentcrew.cli", "hello", "world"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == "Hello, world!\n"