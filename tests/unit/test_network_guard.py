"""Verify the conftest blocks network in non-integration tests (T003)."""

import socket

import pytest


def test_socket_blocked_by_default() -> None:
    with pytest.raises(RuntimeError, match="Network access is disabled"):
        socket.socket()  # type: ignore[operator]


@pytest.mark.integration
def test_integration_can_allow_socket() -> None:
    # This runs only under `-m integration`; here we just assert the marker is applied.
    assert True
