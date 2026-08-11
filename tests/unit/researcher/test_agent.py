"""Unit tests for the researcher role core (deterministic, network-free).

The researcher is a mono-capacity, fixed lookup role used by the
planner/coder/tester to query the repository for context and receive a
**concise summary** instead of loading whole files into the invoking role's
context (Library-First, deterministic core, no network).
"""

from __future__ import annotations

from pathlib import Path

from ai_factory.researcher.agent import lookup
from ai_factory.researcher.models import ResearchResult


def _write_file(root: str, rel: str, content: str) -> str:
    import os

    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def _mini_repo(tmp_path) -> tuple[str, str]:
    """An auth-like micro repo; returns (root, login_file)."""
    root = str(tmp_path)
    login = _write_file(
        root,
        "src/auth/service.py",
        (
            "def login(email, password):\n"
            "    user = db.find_by_email(email)\n"
            "    if user and check_password(password, user.hash):\n"
            "        return issue_jwt(user, ttl_hours=24)\n"
            "    raise AuthError('invalid credentials')\n"
        ),
    )
    _write_file(
        root,
        "src/auth/middleware.py",
        "def require_auth(req):\n    assert req.headers.get('Authorization')\n",
    )
    _write_file(
        root,
        "tests/test_auth.py",
        "def test_login_ok(client):\n    r = client.post('/login',...)\n",
    )
    return root, login


def test_lookup_returns_deterministic_result(tmp_path) -> None:
    """Repo lookup resolves relevant sources and a summary (no voice/LLM)."""
    root, _ = _mini_repo(tmp_path)
    res = lookup("login authentication password", roots=[root])
    assert isinstance(res, ResearchResult)
    assert res.role == "researcher"
    assert res.sources
    # The login service file must be surfaced by the library terms.
    assert any("service.py" in s.path for s in res.sources)
    assert res.summary  # concise brief, fits context window, not a full-file dump


def test_lookup_scopes_default_to_repo(tmp_path) -> None:
    root, _ = _mini_repo(tmp_path)
    res = lookup("login", roots=[root])
    assert res.scopes_used == ["repo"]


def test_lookup_empty_query_returns_no_sources(tmp_path) -> None:
    root, _ = _mini_repo(tmp_path)
    res = lookup("", roots=[root])
    assert res.sources == []
    assert not res.summary


def test_lookup_ignores_unrelated_directories(tmp_path) -> None:
    root, _ = _mini_repo(tmp_path)
    _write_file(root, "docs/CHANGELOG.md", "not related to login at all\n")
    res = lookup("login", roots=[root])
    assert not any("CHANGELOG" in s.path for s in res.sources)


def test_lookup_summary_is_concise_not_a_dump(tmp_path) -> None:
    """Summary is concise and does not dump whole file content (fits context)."""
    root, login = _mini_repo(tmp_path)
    res = lookup("login password token", roots=[root])
    full_login = Path(login).read_text(encoding="utf-8")
    # The summary is prose, not a verbatim replica of a matched source file.
    assert res.summary
    assert full_login.strip() not in res.summary
    assert not res.summary.startswith(full_login.strip())
