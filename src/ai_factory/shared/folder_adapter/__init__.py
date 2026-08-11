"""Speckit folder → factory TechnicalPlan adapter (002-folder-dev-run).

The :mod:`ai_factory.shared.folder_adapter` package turns a speckit spec folder
(``spec.md``, ``plan.md``, ``tasks.md``) into the factory's existing
:class:`~ai_factory.dev_workflow.technical_planner.planner.TechnicalPlan`
without re-deriving or re-clarifying the requirements (FR-005). It is a pure,
deterministic, network-free library (library-first).
"""

from ai_factory.shared.folder_adapter.resolve import (
    FolderResolutionError,
    MissingArtifactError,
    resolve_folder,
    validate_artifacts,
)

__all__ = [
    "FolderResolutionError",
    "MissingArtifactError",
    "resolve_folder",
    "validate_artifacts",
]
