"""Tests for the isolated sandbox runner (T058, FR-021, SC-013).

ExecutionContext runs in an isolated container sandbox; the runner MUST
fail early with :class:`SandboxUnavailable` when the runtime is missing
(SC-013). A fake sandbox provides deterministic results for unit tests.
"""

from __future__ import annotations

import pytest

from ai_factory.shared.sandbox.runner import (
    FakeSandbox,
    SandboxError,
    SandboxResult,
    SandboxUnavailable,
    create_sandbox,
)


def test_fake_sandbox_returns_canned_result() -> None:
    fake = FakeSandbox(SandboxResult(exit_code=0, stdout="ok", stderr="", duration=0.1))
    result = fake.run(["pytest", "-q"])
    assert result.exit_code == 0
    assert result.stdout == "ok"
    assert result.duration == 0.1


def test_create_sandbox_picks_fake() -> None:
    sandbox = create_sandbox("fake")
    assert isinstance(sandbox, FakeSandbox)


def test_create_sandbox_unknown_raises() -> None:
    with pytest.raises(ValueError):
        create_sandbox("weird")


def test_docker_sandbox_fails_early_without_runtime(monkeypatch) -> None:
    """SC-013: no container runtime ⇒ SandboxUnavailable, immediately."""
    import shutil

    monkeypatch.setattr(shutil, "which", lambda _name: None)
    from ai_factory.shared.sandbox.runner import DockerSandbox

    sandbox = DockerSandbox(container="x", volume="unused", image="python:3.14")
    with pytest.raises(SandboxUnavailable):
        sandbox.run(["pytest", "-q"])


def test_sandbox_result_shape() -> None:
    r = SandboxResult(exit_code=2, stdout="fail", stderr="boom", duration=1.0)
    assert r.ok is False  # non-zero exit
    assert SandboxResult(exit_code=0, stdout="", stderr="", duration=0.0).ok is True


def test_sandbox_error_is_runtime_error() -> None:
    assert issubclass(SandboxError, RuntimeError)
    assert issubclass(SandboxUnavailable, SandboxError)
