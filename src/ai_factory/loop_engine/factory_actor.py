"""Concrete factory actor binding (T080, Q1=A, FR-012).

``FactoryActor`` binds a loop iteration to the factory's **folder-driven dev
pipeline** (approved spec folder → orchestrated execution). It is shipped as a
**library seam** — deliberately NOT wired inside ``dev_workflow`` nodes in v1
(FR-010); any caller may compose it into a ``loop_engine`` run.

The real end-to-end execution path is network/container-bound and exercised
under ``-m integration``; a lightweight deterministic runner is used in unit
tests so the binding itself is testable network-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ai_factory.loop_engine.actor import Actor
from ai_factory.loop_engine.models import ActorOutput, LoopConfig, RepairContext


@dataclass
class FolderRunner:
    """Injected seam that runs the factory pipeline for a folder (FR-012).

    A real implementation calls ``ai_factory.cli.dev_run.main([folder])`` and
    reports the produced artifact refs (integration-gated). Tests inject a fake.
    """

    folder: str
    runs: list[str] = field(default_factory=list)

    def __call__(self, repair: RepairContext) -> list[str]:
        """Run the pipeline; return produced artifact reference(s)."""
        self.runs.append(self.folder)
        return [self.folder]


class FactoryActor(Actor):
    """Loop actor over the folder-driven dev pipeline (Q1=A)."""

    def __init__(
        self, run_pipeline: FolderRunner | None = None, folder: str = "spec_folder"
    ) -> None:
        self.runner = run_pipeline or FolderRunner(folder=folder)

    def invoke(self, context: RepairContext) -> ActorOutput:
        refs = self.runner(context)
        return ActorOutput(
            status=True,  # actor's *report* only; the gate decides (FR-002)
            artifact_refs=refs,
            description="factory folder-driven pipeline run",
            summary=",".join(refs),
        )


def build_factory_loop_config(
    folder: str, *, run_id: str, max_iterations: int, gate: object
) -> LoopConfig:
    """Build a :class:`LoopConfig` for a ``FactoryActor`` loop (library seam)."""
    return LoopConfig(
        actor=FactoryActor(run_pipeline=FolderRunner(folder=folder)),
        gate=gate,
        max_iterations=max_iterations,
        run_id=run_id,
    )


__all__ = ["FactoryActor", "FolderRunner", "build_factory_loop_config"]