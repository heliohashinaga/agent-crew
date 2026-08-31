"""Semantic clean-code policy injected into the cleaner (and coder) LLM prompts.

Derived from the project's clean-code skill (pi-agent-skills
``skills/clean-code/SKILL.md``). Only the **semantic** judgments are included —
formatting is explicitly excluded (delegated to a formatter, FR-005). Keeping the
policy as a library constant (with an optional loader that reads the skill file,
when present) makes the agent genuinely "use the skill" without depending on a
`.pi` path at build time.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Canonical semantic clean-code policy (language-agnostic).
CLEAN_CODE_POLICY = """\
Clean-code standards to apply (keep the same language; do NOT
reformat or change behavior):
- Use descriptive, intent-revealing names; keep a consistent vocabulary.
- Keep functions small and doing one thing; extract the rest;
  prefer early returns.
- Keep comments for WHY (intent, trade-offs), not for restating code.
- Remove redundant comments, commented-out blocks, and dead code.
- If in doubt, prefer the smaller, safer change."""

# Candidate SKILL.md locations (project then user) so the live skill file is
# honored when present; otherwise the constant above is used.
_SKILL_CANDIDATES = (
    Path(__file__).resolve().parents[3] / ".pi" / "skills" / "clean-code" / "SKILL.md",
    Path.home() / ".pi" / "agent" / "skills" / "clean-code" / "SKILL.md",
)

_FRONTMATTER = re.compile(r"^---.*?---\s*", re.S)


def read_clean_code_policy(source: str | os.PathLike[str] | None = None) -> str:
    """Return the clean-code policy text to feed the LLM.

    With ``source`` (a path to a ``SKILL.md``): return its body with the YAML
    frontmatter stripped. With ``source=None``: look for the skill file at the
    known locations; if found, use it, otherwise return ``CLEAN_CODE_POLICY``.
    """
    if source is not None:
        raw = Path(source).read_text(encoding="utf-8")
        return _strip_frontmatter(raw)

    for candidate in _SKILL_CANDIDATES:
        if candidate.is_file():
            return _strip_frontmatter(candidate.read_text(encoding="utf-8"))
    return CLEAN_CODE_POLICY


def _strip_frontmatter(text: str) -> str:
    return _FRONTMATTER.sub("", text, count=1).strip()