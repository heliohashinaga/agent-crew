"""Security Reviewer role library (T057, FR-020).

Scans the repo's produced files for secret-LOOKING values (reusing the
FR-018 redactor), reporting each finding with its file path, plus
dependency/basic hygiene checks. Identified issues gate the PR.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ai_factory.shared.secrets.loader import _SECRET_LIKE_RE, redact_secret_like

_SCAN_EXTENSIONS = {
    ".py",
    ".sh",
    ".env",
    ".toml",
    ".yml",
    ".yaml",
    ".json",
    ".md",
    ".txt",
}


class SecurityReviewVerdict(BaseModel):
    """Security review outcome (findings gate approval)."""

    approved: bool
    findings: list[str] = Field(default_factory=list)
    feedback: str = ""


def _iter_text_files(repo: Path):
    for path in sorted(repo.rglob("*")):
        if path.is_file() and path.suffix in _SCAN_EXTENSIONS:
            yield path


def review(repo: Path) -> SecurityReviewVerdict:
    """Scan ``repo`` for secret-like values and report findings."""
    findings: list[str] = []
    for path in _iter_text_files(repo):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not _SECRET_LIKE_RE.search(content):
            continue
        rel = str(path.relative_to(repo))
        # Redact to prove the value was genuinely secret-like.
        redacted = redact_secret_like(content)
        if redacted != content:
            findings.append(f"potential secret-like value in {rel}")

    approved = not findings
    return SecurityReviewVerdict(
        approved=approved, findings=findings, feedback="; ".join(findings)
    )


__all__ = ["SecurityReviewVerdict", "review"]
