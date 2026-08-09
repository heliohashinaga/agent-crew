"""Test Runner role library (T055, FR-011, FR-021).

Runs the generated test suites INSIDE the sandbox and maps the sandbox's
exit/output to a structured result with evidence. The sandbox is injected
(:class:`~ai_factory.shared.sandbox.runner.Sandbox`) so tests run without a
container; production uses the isolated docker sandbox (FR-021).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ai_factory.shared.sandbox.runner import Sandbox

DEFAULT_SUITE = "test_suite.py"


class TestRunResult(BaseModel):
    """Outcome of running the suites inside the sandbox."""

    passed: bool
    failures: list[str] = Field(default_factory=list)
    suites: list[str] = Field(default_factory=list)
    evidence: dict = Field(default_factory=dict)


def run_tests(
    repo: Path,
    sandbox: Sandbox,
    suites: list[str] | None = None,
    timeout: float = 300.0,
) -> TestRunResult:
    """Run ``suites`` (default ``test_suite.py``) inside ``sandbox`` on ``repo``."""
    suites = list(suites or [DEFAULT_SUITE])
    result = sandbox.run(
        ["pytest", "-q", *suites], cwd=str(Path(repo)), timeout=timeout
    )

    failures: list[str] = []
    if result.exit_code != 0:
        combined = f"{result.stdout}\n{result.stderr}"
        failures = [
            ln.strip()
            for ln in combined.splitlines()
            if "FAILED" in ln or "Error" in ln
        ][:10]
        if not failures:
            failures = [f"tests failed with exit code {result.exit_code}"]

    return TestRunResult(
        passed=result.exit_code == 0,
        failures=failures,
        suites=suites,
        evidence={
            "exit_code": result.exit_code,
            "stdout_tail": result.stdout[-2000:],
            "stderr_tail": result.stderr[-2000:],
            "duration": result.duration,
        },
    )


__all__ = ["DEFAULT_SUITE", "TestRunResult", "run_tests"]
