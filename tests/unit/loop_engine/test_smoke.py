"""Scaffold smoke test for the ``loop_engine`` package (T002, T020)."""

from __future__ import annotations

import ai_factory.loop_engine as pkg
from ai_factory.loop_engine import (
    FactoryActor,
    LoopConfig,
    LoopResult,
    LoopStatus,
    run_loop,
)
from ai_factory.loop_engine.actor import Actor, Gate
from ai_factory.loop_engine.engine import LoopConfigError
from ai_factory.loop_engine.gate import LoopGateError
from ai_factory.loop_engine.models import GateVerdict, RepairContext


def test_package_imports() -> None:
    assert pkg.LOOP_ENGINE_ROLE == "loop_engine"
    assert LoopStatus.PASSED.value == "passed"


def test_public_api_surface() -> None:
    # Key objects importable from the package root (Library-First, FR-001).
    assert callable(run_loop)
    assert LoopConfig and LoopResult and FactoryActor


def test_seam_imports() -> None:
    # Actor/Gate protocols and error types importable (FR-002/FR-009).
    assert RepairContext and GateVerdict
    for exc in (LoopConfigError, LoopGateError):
        assert issubclass(exc, Exception)


def test_actor_and_gate_are_importable_seams() -> None:
    # Actor/Gate are abstract seams (importable classes, not instantiable models).
    assert Actor is not None
    assert Gate is not None