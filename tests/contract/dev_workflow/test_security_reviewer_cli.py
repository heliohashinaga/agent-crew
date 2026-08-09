"""Contract test for the security-reviewer role library CLI (T056, FR-020).

Scans the repo's produced files for secret-looking values (reusing the
FR-018 redactor), reports findings with file paths, and gates the PR.
"""

from __future__ import annotations

import json

from ai_factory.dev_workflow.security_reviewer.cli import main as cli_main
from ai_factory.dev_workflow.security_reviewer.reviewer import review
from ai_factory.shared.cli_util import EXIT_ERROR, EXIT_REJECTED, run


def _clean_repo(tmp_path) -> str:
    (tmp_path / "mod.py").write_text("x = 1\n", encoding="utf-8")
    return str(tmp_path)


def test_approves_clean_repo(tmp_path) -> None:
    verdict = review(tmp_path)
    assert verdict.approved is True
    assert verdict.findings == []


def test_rejects_secret_like_values(tmp_path) -> None:
    (tmp_path / "creds.py").write_text(
        "token = 'sk-abcdef1234567890'\n", encoding="utf-8"
    )
    verdict = review(tmp_path)
    assert verdict.approved is False
    assert any("creds.py" in f for f in verdict.findings)


def test_findings_include_file_paths(tmp_path) -> None:
    (tmp_path / "a.py").write_text("password=supersecret99\n", encoding="utf-8")
    verdict = review(tmp_path)
    assert verdict.findings
    assert all("a.py" in f for f in verdict.findings)


def test_recurses_into_subdirectories(tmp_path) -> None:
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "mod.py").write_text("Bearer abc12345secret\n", encoding="utf-8")
    verdict = review(tmp_path)
    assert verdict.approved is False


def test_cli_emits_verdict(tmp_path, capsys) -> None:
    code = run(cli_main, ["--repo", _clean_repo(tmp_path)])
    assert code == 0
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["approved"] is True


def test_cli_rejects_with_exit_code(tmp_path, capsys) -> None:
    (tmp_path / "bad.py").write_text("api_key=abcdef0123456789\n", encoding="utf-8")
    code = run(cli_main, ["--repo", str(tmp_path)])
    assert code == EXIT_REJECTED
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["approved"] is False


def test_cli_missing_repo_is_error(tmp_path) -> None:
    assert run(cli_main, ["--repo", str(tmp_path / "missing")]) == EXIT_ERROR
