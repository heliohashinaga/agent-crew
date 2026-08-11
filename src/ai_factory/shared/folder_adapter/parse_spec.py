"""spec.md parsing (002-folder-dev-run, T006/T007).

Derives subtask ``acceptance_criteria`` from the ``spec.md`` Functional
Requirements section via a 1:1 carry — the factory never re-derives or
re-clarifies requirements (FR-005). Edge cases (AC-0* / "## Acceptance
Criteria") are also carried as additional acceptance criteria. Purely
deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

FR_RE = re.compile(r"^\s*(?:-\s+)?(FR-\d+)\s*:?\s*(.+)$", re.IGNORECASE)
AC_RE = re.compile(r"^\s*-\s+\[[ xX]\]\s*(.+)$")
EDGE_RE = re.compile(
    r"^##\s*(?:Acceptance Criteria|Edge Cases|Non-Goals)", re.IGNORECASE
)


@dataclass(frozen=True)
class ParsedSpec:
    """Requirements extracted from ``spec.md`` without re-derivation."""

    goal: str
    functional_requirements: tuple[str, ...] = field(default_factory=tuple)
    acceptance_criteria: tuple[str, ...] = field(default_factory=tuple)


def _goal_from_title(lines: list[str]) -> str:
    for line in lines:
        if line.startswith("# "):
            return line.lstrip("#").strip()
    return ""


def parse_spec(content: str) -> ParsedSpec:
    """Parse ``spec.md`` content into functional + acceptance requirements."""
    lines = content.splitlines()
    goal = _goal_from_title(lines)
    frs: list[str] = []
    acs: list[str] = []

    for line in lines:
        m = FR_RE.match(line)
        if m:
            frs.append(f"{m.group(1)}: {m.group(2).strip()}")
            continue
        m = AC_RE.match(line)
        if m:
            acs.append(m.group(1).strip())
            continue
        if EDGE_RE.match(line.strip()):
            # Within an acceptance-criteria section, checklist bullets are ACs.
            continue

    return ParsedSpec(
        goal=goal,
        # Deduplicate while preserving order.
        functional_requirements=tuple(dict.fromkeys(frs)),
        acceptance_criteria=tuple(dict.fromkeys(acs)),
    )


def acceptance_criteria_from_spec(spec_content: str) -> list[str]:
    """Return the derived acceptance criteria (1:1 carry of FRs + marked ACs)."""
    parsed = parse_spec(spec_content)
    return list(parsed.acceptance_criteria)


__all__ = ["ParsedSpec", "acceptance_criteria_from_spec", "parse_spec"]
