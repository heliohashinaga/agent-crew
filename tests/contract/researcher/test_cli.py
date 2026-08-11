"""Contract tests for the ``ai-factory-researcher`` CLI (T020-T022).

Covers: JSON to stdout (parseable ResearchResult), human format, missing-arg
usage errors, and repo-scope resolution against a temp repo.
"""

from __future__ import annotations

import pytest

from ai_factory.researcher.cli import main
from ai_factory.researcher.models import ResearchResult
from ai_factory.shared.cli_util import EXIT_ERROR, EXIT_OK, run


@pytest.fixture
def tmp_repo(tmp_path):
    (tmp_path / "service.py").write_text("def foo():\n    return b\n", encoding="utf-8")
    return tmp_path


def test_cli_repo_json_stdout(tmp_repo, capsys) -> None:
    code = run(
        main,
        [
            "--scope", "repo", "--query", "foo",
            "--roots", str(tmp_repo), "--format", "json",
        ],
    )
    out, _err = capsys.readouterr()
    assert code == EXIT_OK
    parsed = ResearchResult.model_validate_json(out)
    assert parsed.role == "researcher"
    assert parsed.sources
    assert any("service.py" in s.path for s in parsed.sources)


def test_cli_missing_query_usage_error(tmp_repo, capsys) -> None:
    code = run(main, ["--scope", "repo", "--roots", str(tmp_repo)])
    out, err = capsys.readouterr()
    assert code == EXIT_ERROR
    assert "query" in (out + err).lower()


def test_cli_missing_roots_usage_error(capsys) -> None:
    code = run(main, ["--scope", "repo", "--query", "foo"])
    _out, _err = capsys.readouterr()
    assert code == EXIT_ERROR


def test_cli_human_format(tmp_repo, capsys) -> None:
    code = run(
        main,
        [
            "--scope", "repo", "--query", "foo",
            "--roots", str(tmp_repo), "--format", "human",
        ],
    )
    out, _err = capsys.readouterr()
    assert code == EXIT_OK
    assert "service.py" in out.lower() or "foo" in out.lower()
