"""Shared pytest configuration.

Enforces the test hierarchy (constitution Principles III & IV):

- **unit** and **contract** tests must never touch the network. Network
  access is blocked for any test that is NOT marked ``integration``.
- **integration** tests are opt-in (``pytest -m integration``) and require
  network plus a container runtime.

The autouse fixture below patches ``socket.socket`` so that any attempt to
open a socket from a non-integration test raises instead of connecting.
"""

from __future__ import annotations

import socket

import pytest


@pytest.fixture(autouse=True)
def _block_network(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Block outbound network access unless the test is marked ``integration``."""
    if "integration" in request.keywords:
        yield
        return

    def _deny(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError(
            "Network access is disabled in non-integration tests. "
            "Mark the test with @pytest.mark.integration if it must reach the network."
        )

    # Socket creation from Python goes through socket.socket(); deny it.
    monkeypatch.setattr(socket, "socket", _deny)
    monkeypatch.setattr(socket, "create_connection", _deny)  # type: ignore[arg-type]
    try:
        yield
    finally:
        pass
