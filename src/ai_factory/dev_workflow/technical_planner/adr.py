"""Conditional Architecture Decision Records (T043, FR-008).

An ADR is recorded ONLY when a significant architectural decision is
present — never for simple fixes or obvious optimizations. Each ADR MUST
record decision, rationale, trade-offs, and alternatives considered
(FR-008). The planner decides *when* an ADR is warranted via
:func:`should_create_adr`; this module fixes the record shape and its
mandatory fields.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

ADRStatus = Literal["proposed", "accepted", "deprecated"]


class ArchitectureDecisionRecord(BaseModel):
    """One recorded architectural decision (FR-008)."""

    adr_id: str = ""
    title: str
    status: ADRStatus = "accepted"
    context: str
    decision: str
    rationale: str
    trade_offs: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _record_tradeoffs_and_alternatives(self) -> ArchitectureDecisionRecord:
        """FR-008: trade-offs and alternatives are mandatory on an ADR."""
        if not self.trade_offs or not self.alternatives:
            raise ValueError(
                "ADR must record trade_offs and alternatives considered (FR-008)"
            )
        return self


def should_create_adr(architecture_impact: bool) -> bool:
    """FR-008: only significant architectural decisions get an ADR."""
    return architecture_impact


__all__ = ["ADRStatus", "ArchitectureDecisionRecord", "should_create_adr"]
