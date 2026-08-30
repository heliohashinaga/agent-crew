"""Unit tests for the FactoryActor binding (T080, Q1=A, FR-012)."""

from __future__ import annotations

from ai_factory.loop_engine.factory_actor import (
    FactoryActor,
    FolderRunner,
    build_factory_loop_config,
)
from ai_factory.loop_engine.models import LoopStatus, RepairContext
from tests.unit.loop_engine.fakes import FakeGate


def test_factory_actor_binds_to_actor_protocol() -> None:
    runner = FolderRunner(folder="spec_folder")
    actor = FactoryActor(run_pipeline=runner)
    out = actor.invoke(RepairContext())
    assert out.status is True
    assert out.artifact_refs == ["spec_folder"]  # pipeline seam produced ref
    assert runner.runs == ["spec_folder"]


def test_build_factory_loop_config_composes() -> None:
    gate = FakeGate(pass_calls=[0])
    config = build_factory_loop_config(
        "folder", run_id="factory-1", max_iterations=3, gate=gate
    )
    assert config.max_iterations == 3
    assert config.run_id == "factory-1"


def test_build_factory_loop_config_is_run_ready() -> None:
    from ai_factory.loop_engine.engine import run_loop

    gate = FakeGate(pass_calls=[0])
    config = build_factory_loop_config(
        "folder", run_id="factory-2", max_iterations=3, gate=gate
    )
    result = run_loop(config)
    assert result.status == LoopStatus.PASSED
    assert result.artifact_refs == ["folder"]


def test_factory_actor_never_self_grades() -> None:
    # actor reports success, but the gate fails -> not `passed` (FR-002)
    from ai_factory.loop_engine.engine import run_loop

    gate = FakeGate(never_pass=True)
    config = build_factory_loop_config(
        "folder", run_id="factory-3", max_iterations=3, gate=gate
    )
    result = run_loop(config)
    assert result.status == LoopStatus.EXHAUSTED  # no self-grading