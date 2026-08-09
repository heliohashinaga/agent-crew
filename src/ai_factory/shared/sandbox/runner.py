"""Isolated sandbox runner (T059, FR-021, SC-013).

Test execution happens inside an isolated container sandbox (FR-021).
:class:`DockerSandbox` fails EARLY with :class:`SandboxUnavailable` when no
container runtime is present (SC-013). :class:`FakeSandbox` returns
deterministic canned results so unit/contract/integration tests run
network- and container-free.
"""

from __future__ import annotations

import shutil
import time
from typing import Protocol

from pydantic import BaseModel


class SandboxError(RuntimeError):
    """Base class for sandbox failures."""


class SandboxUnavailable(SandboxError):
    """Raised when the sandbox runtime is unavailable (SC-013)."""


class SandboxResult(BaseModel):
    """The structured outcome of one sandboxed command."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


class Sandbox(Protocol):
    """Contract every sandbox runnable satisfies."""

    def run(
        self, command: list[str], cwd: str | None = None, timeout: float = 120.0
    ) -> SandboxResult:
        """Execute ``command`` in the sandbox and return its outcome."""
        ...


class FakeSandbox:
    """Deterministic stand-in returning canned results (tests/dry runs).

    Pass a single :class:`SandboxResult`, or a list of results that are
    returned in order (the last one repeats) — handy for driving rework
    loops deterministically.
    """

    def __init__(
        self, result: SandboxResult, results: list[SandboxResult] | None = None
    ) -> None:
        self._result = result
        self._results = list(results or [])
        self._calls = 0

    def run(
        self, command: list[str], cwd: str | None = None, timeout: float = 120.0
    ) -> SandboxResult:
        if self._results:
            idx = min(self._calls, len(self._results) - 1)
            self._calls += 1
            return self._results[idx]
        return self._result


class DockerSandbox:
    """Runs commands inside a Docker container over ``docker exec`` (FR-021).

    Fails early (:class:`SandboxUnavailable`) if the docker CLI is missing.
    """

    def __init__(
        self, container: str, image: str = "python:3.14", volume: str = ""
    ) -> None:
        self.container = container
        self.image = image
        self.volume = volume

    def run(
        self, command: list[str], cwd: str | None = None, timeout: float = 120.0
    ) -> SandboxResult:
        import subprocess

        if shutil.which("docker") is None:
            raise SandboxUnavailable(
                "docker CLI not found; cannot execute in an isolated sandbox (SC-013)"
            )

        argv = ["docker", "exec"]
        if cwd:
            argv += ["-w", cwd]
        argv += [self.container, *command]
        start = time.monotonic()
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
            return SandboxResult(
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration=time.monotonic() - start,
            )
        except subprocess.TimeoutExpired as exc:
            raise SandboxError(f"sandboxed command timed out after {timeout}s") from exc


def create_sandbox(provider: str, **kwargs) -> Sandbox:
    """Instantiate a sandbox by name: fake/fake-fail (tests) or docker."""
    if provider == "fake":
        return FakeSandbox(
            kwargs.get("result", SandboxResult(exit_code=0, stdout="", stderr=""))
        )
    if provider == "fake-fail":
        return FakeSandbox(
            SandboxResult(
                exit_code=1, stdout="FAILED test_suite.py::test_ac_1 - boom", stderr=""
            )
        )
    if provider == "docker":
        return DockerSandbox(
            container=kwargs.get("container", "ai-factory-runner"),
            image=kwargs.get("image", "python:3.14"),
            volume=kwargs.get("volume", ""),
        )
    raise ValueError(f"unknown sandbox provider: {provider!r}")


__all__ = [
    "DockerSandbox",
    "FakeSandbox",
    "Sandbox",
    "SandboxError",
    "SandboxResult",
    "SandboxUnavailable",
    "create_sandbox",
]
