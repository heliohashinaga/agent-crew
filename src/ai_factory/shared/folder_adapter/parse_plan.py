"""plan.md parsing (002-folder-dev-run, T012/T013, US-2).

Imports ``plan.md`` decisions into a :class:`TechnicalAssessment` rather than
re-deriving from ``spec.md`` (FR-004, SC-005). When sections are absent, the
parser degrades to deterministic defaults and records an inference note so the
result is reproducible and auditable. Purely deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ai_factory.dev_workflow.technical_planner.planner import TechnicalAssessment

SECURITY_KEYWORDS = (
    "auth", "password", "pii", "secret", "token", "credential", "hash", "encrypt"
)
ARCHITECTURE_KEYWORDS = (
    "postgres",
    "microservice",
    "event bus",
    "queue",
    "message broker",
    "graphql",
    "kafka",
    "redis",
    "cache",
    "service mesh",
    "kubernetes",
    "db",
    "migration",
    "webhook",
)
DOC_KEYWORDS = (
    "docs",
    "documentation",
    "runbook",
    "quickstart",
    "architecture decision",
    "adr",
    "changelog",
)

_SECTION = re.compile(r"^##\s*(.+)$")


@dataclass(frozen=True)
class PlanAssessment:
    """Assessment data parsed from ``plan.md`` with a fallback note."""

    assessment: TechnicalAssessment
    inferred: tuple[str, ...] = field(default_factory=tuple)


def _collect_section(lines: list[str], title: str) -> list[str]:
    """Collect the body of the ``## <title>`` section (case-insensitive)."""
    start = -1
    for i, line in enumerate(lines):
        m = _SECTION.match(line)
        if m and m.group(1).strip().lower() == title.lower():
            start = i + 1
            break
    if start < 0:
        return []
    body: list[str] = []
    for line in lines[start:]:
        if _SECTION.match(line.strip()):
            break
        body.append(line.strip())
    return [b for b in body if b]


def _has_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(k in low for k in keywords)


def parse_plan(content: str) -> PlanAssessment:
    """Parse ``plan.md`` content into a TechnicalAssessment."""
    lines = content.splitlines() if content else []

    tech = "\n".join(_collect_section(lines, "Tech Stack"))
    adr = "\n".join(_collect_section(lines, "Architecture Decisions"))
    sec = "\n".join(_collect_section(lines, "Security"))
    risk = "\n".join(_collect_section(lines, "Risks"))
    docs_section = "\n".join(_collect_section(lines, "Documentation"))

    inferred: list[str] = []
    if content and not tech and not adr:
        inferred.append(
            "plan.md absent or without Tech Stack/Architecture sections; "
            "assessment inferred from defaults."
        )

    security_surface = [k for k in SECURITY_KEYWORDS if _has_keyword(sec or tech, (k,))]
    architecture_impact = _has_keyword(f"{adr} {tech}", ARCHITECTURE_KEYWORDS)
    documentation_required = _has_keyword(
        (docs_section or tech or adr), DOC_KEYWORDS
    ) or "documentation" in docs_section.lower()

    # Risk: high only when Security/Risks sections flag a known risk.
    risk_level = "high" if _has_keyword(risk, ("high", "critical", "breaker")) else (
        "medium" if security_surface else "low"
    )

    test_scope = _collect_section(lines, "Test Strategy")
    if not test_scope:
        inferred.append("Test Strategy section absent; test_scope = [].")
        test_scope = []

    assessment = TechnicalAssessment(
        complexity="complex" if architecture_impact else "standard",
        risk=risk_level,  # type: ignore[arg-type]
        architecture_impact=architecture_impact,
        test_scope=[s.strip("- ") for s in test_scope],
        security_surface=security_surface,
        documentation_required=documentation_required,
        plan_summary=(tech or adr)[:250],
    )
    return PlanAssessment(assessment=assessment, inferred=tuple(inferred))


def degrade_assessment(missing_content: str = "") -> PlanAssessment:
    """Return a default assessment when plan.md is entirely absent (FR-004/SC-005)."""
    assessment = TechnicalAssessment(
        complexity="standard",
        risk="low",  # type: ignore[arg-type]
        architecture_impact=False,
        test_scope=[],
        security_surface=[],
        documentation_required=False,
        plan_summary="",
    )
    return PlanAssessment(
        assessment=assessment,
        inferred=(
            "plan.md missing; assessment degraded to deterministic defaults "
            "(FR-004, SC-005).",
        ),
    )


__all__ = ["PlanAssessment", "degrade_assessment", "parse_plan"]
