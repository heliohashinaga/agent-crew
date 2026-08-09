"""Tests for the issue model and classification policy (T073, FR-013/014/015).

Runtime failures are classified into a category and severity; the retry
policy per category decides backoff (transient) vs deterministic-fix vs
re-plan vs security-halt, with bounded retries (FR-014) and re-planning on
limit exceeded (FR-015).
"""

from __future__ import annotations

from ai_factory.dev_workflow.issues.policy import (
    classify_issue,
    is_deterministic,
    issue_retry_policy,
)
from ai_factory.dev_workflow.models import Issue


def test_classify_security_issue() -> None:
    issue = classify_issue("Security review found a hardcoded token leak")
    assert issue.category == "security"
    assert issue.severity in ("critical", "high")


def test_classify_infrastructure_issue() -> None:
    issue = classify_issue("Docker container timed out; network unreachable")
    assert issue.category == "infrastructure"
    assert is_deterministic(issue.category) is False


def test_classify_logic_bug_default() -> None:
    issue = classify_issue("Index out of range in the search helper")
    assert issue.category in ("logic_bug", "data_edge_case")
    assert is_deterministic(issue.category) is True


def test_classify_technical_limitation() -> None:
    issue = classify_issue("Feature is not supported by the current platform")
    assert issue.category == "technical_limitation"


def test_issue_model_shape() -> None:
    issue = Issue(issue_id="i-1", category="logic_bug", severity="medium")
    assert issue.issue_id == "i-1"
    assert issue.retry_attempts == []
    assert issue.escalation_target is None


def test_policy_backoff_for_transient() -> None:
    policy = issue_retry_policy("infrastructure")
    assert policy["strategy"] == "backoff"
    assert policy["max_retries"] >= 1
    assert policy["backoff_seconds"] > 0


def test_policy_fix_for_deterministic() -> None:
    policy = issue_retry_policy("logic_bug")
    assert policy["strategy"] == "fix"


def test_policy_replan_for_limitation() -> None:
    assert issue_retry_policy("technical_limitation")["strategy"] == "replan"


def test_policy_security_halt() -> None:
    assert issue_retry_policy("security")["strategy"] == "fix_audit"


def test_retry_attempt_attachment() -> None:
    from datetime import datetime

    from ai_factory.dev_workflow.models import RetryAttempt

    issue = classify_issue("Flaky network call")
    issue.retry_attempts.append(
        RetryAttempt(attempt=1, note="retrying", datetime=None or datetime.now())
    )
    assert len(issue.retry_attempts) == 1
    assert issue.category in ("infrastructure", "third_party")
