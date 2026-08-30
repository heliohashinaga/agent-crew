"""Loop Engineering role library.

A standalone, Library-First control-loop capability: run an **actor → external
gate → repair → repeat** loop until the gate passes or termination conditions
are met, persisting a durable ledger/spine so a run can be paused/resumed.
The deterministic core is network-free; review/LLM work is behind injectable
seams and integration-gated. Deliberately **not** wired inside workflow nodes;
workflows/CLIs compose it (FR-010).
"""

from ai_factory.loop_engine.engine import LoopConfigError, LoopGateError, run_loop
from ai_factory.loop_engine.factory_actor import FactoryActor, FolderRunner
from ai_factory.loop_engine.models import (
    ActorOutput,
    BudgetDelta,
    CheckResult,
    CheckStage,
    EscalationSummary,
    GateVerdict,
    LoopBudget,
    LoopConfig,
    LoopResult,
    LoopStatus,
    RatchetConfig,
    RepairContext,
)
from ai_factory.loop_engine.profile import (
    LOOP_ENGINE_PROFILE,
    LOOP_ENGINE_ROLE,
    LoopEngineProfile,
)

__all__ = [
    "ActorOutput",
    "BudgetDelta",
    "CheckResult",
    "CheckStage",
    "EscalationSummary",
    "FactoryActor",
    "FolderRunner",
    "GateVerdict",
    "LOOP_ENGINE_PROFILE",
    "LOOP_ENGINE_ROLE",
    "LoopBudget",
    "LoopConfig",
    "LoopConfigError",
    "LoopEngineProfile",
    "LoopGateError",
    "LoopResult",
    "LoopStatus",
    "RatchetConfig",
    "RepairContext",
    "run_loop",
]