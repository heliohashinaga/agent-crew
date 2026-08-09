"""Issue classification & retry policy (T074, FR-013/014/015).

Runtime failures are classified into a category + severity. The policy maps
each category to a bounded handling strategy (FR-014):

- ``backoff``  — transient/infrastructure/third-party: exponential backoff.
- ``fix``      — deterministic (logic bug, data edge case): route to the
                 code worker to fix.
- ``replan``   — technical limitation: auto re-plan via the Technical
                 Planner (FR-015); a human is involved ONLY when re-planning
                 fails (``stopped_human``, exit 5).
- ``fix_audit``— security: halt, immediate fix, then full re-audit before
                 merge (FR-014, SC-007).
"""

from __future__ import annotations

from ai_factory.dev_workflow.models import Issue

# Deterministic vs transient groupings (FR-014).
DETERMINISTIC = {"logic_bug", "data_edge_case", "technical_limitation"}
TRANSIENT = {"infrastructure", "third_party"}

_SECURITY = {
    "security",
    "secret",
    "token",
    "leak",
    "vulnerab",
    "injection",
    "xss",
    "csrf",
    "permission",
    "authz",
}
_INFRA = {
    "network",
    "docker",
    "container",
    "timeout",
    "connection",
    "resource",
    "disk",
    "memory",
    "infra",
    "503",
    "500",
    "unreachable",
}
_THIRD_PARTY = {
    "dependency",
    "library",
    "package",
    "api rate",
    "provider",
    "sdk",
    "pypi",
}
_LIMITATION = {
    "not supported",
    "unsupported",
    "limitation",
    "cannot",
    "impossible",
    "out of scope",
    "unfeasible",
    "not possible",
}
_EDGE = {
    "edge",
    "empty",
    "null",
    "duplicate",
    "boundary",
    "race",
    "concurrent",
    "index out of range",
}
_CRITICAL = {"critical", "leak", "vulnerab", "secret", "token", "break-in", "root"}


def classify_issue(raw: str) -> Issue:
    """Classify a failure message into an :class:`Issue` (category + severity)."""
    text = raw.lower()
    if any(k in text for k in _SECURITY):
        category, severity = (
            "security",
            ("critical" if any(k in text for k in _CRITICAL) else "high"),
        )
    elif any(k in text for k in _INFRA):
        category, severity = "infrastructure", "medium"
    elif any(k in text for k in _THIRD_PARTY):
        category, severity = "third_party", "low"
    elif any(k in text for k in _LIMITATION):
        category, severity = "technical_limitation", "low"
    elif any(k in text for k in _EDGE):
        category, severity = "data_edge_case", "medium"
    else:
        category, severity = "logic_bug", "medium"
    return Issue(
        issue_id=_gen_id(), category=category, severity=severity, message=raw.strip()
    )


def _gen_id() -> str:
    import uuid

    return f"issue-{uuid.uuid4().hex[:8]}"


def is_deterministic(category: str) -> bool:
    """Deterministic failures are fix-able by the code worker (FR-014)."""
    return category in DETERMINISTIC


def issue_retry_policy(category: str) -> dict:
    """Bounded retry policy for a category (FR-014)."""
    if category in ("infrastructure", "third_party"):
        return {"strategy": "backoff", "max_retries": 3, "backoff_seconds": 2}
    if category in ("logic_bug", "data_edge_case"):
        return {"strategy": "fix", "max_retries": 2}
    if category == "technical_limitation":
        return {"strategy": "replan", "max_retries": 1}
    if category == "security":
        return {"strategy": "fix_audit", "max_retries": 1}
    return {"strategy": "fix", "max_retries": 1}


__all__ = [
    "DETERMINISTIC",
    "TRANSIENT",
    "classify_issue",
    "is_deterministic",
    "issue_retry_policy",
]
