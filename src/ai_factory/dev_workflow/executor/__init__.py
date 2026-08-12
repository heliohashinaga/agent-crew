"""Dual-mode executor for the dev workflow (US3/US4, FR-007).

Sits between ``dev_workflow/graph`` and the role libraries: in offline mode it
delegates to the deterministic role functions (identical to today), and in live
mode it resolves each role's real model id and dispatches through a registered
provider. See :mod:`ai_factory.dev_workflow.executor.runner`.
"""

from __future__ import annotations

from ai_factory.dev_workflow.executor.runner import (
    RoleRunResult,
    live_enabled,
    run_role,
)

__all__ = ["RoleRunResult", "live_enabled", "run_role"]
