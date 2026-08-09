"""Tests for conditional ADR production (T042, FR-008).

An ADR is created ONLY for significant architectural decisions; never for
simple fixes or obvious optimizations. Each ADR must record decision,
rationale, trade-offs and alternatives considered.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_factory.dev_workflow.technical_planner.adr import (
    ArchitectureDecisionRecord,
    should_create_adr,
)


def test_should_create_adr_only_for_architecture_impact() -> None:
    """FR-008: no ADR for simple fixes; ADR when a significant decision exists."""
    assert should_create_adr(architecture_impact=True) is True
    assert should_create_adr(architecture_impact=False) is False


def test_full_adr_records_all_fr008_fields() -> None:
    adr = ArchitectureDecisionRecord(
        title="Use Postgres for durable task queue",
        context="Background tasks must survive restarts.",
        decision="Adopt Postgres-backed worker queue.",
        rationale="Survives restarts; team already runs Postgres.",
        trade_offs=["Higher ops cost", "More moving parts than in-memory queue"],
        alternatives=["In-memory queue", "Redis"],
    )
    assert adr.status == "accepted"
    assert len(adr.trade_offs) == 2
    assert len(adr.alternatives) == 2


def test_adr_requires_tradeoffs_and_alternatives() -> None:
    """FR-008: trade-offs and alternatives are mandatory on an ADR."""
    with pytest.raises(ValidationError):
        ArchitectureDecisionRecord(
            title="t",
            context="c",
            decision="d",
            rationale="r",
            trade_offs=[],
            alternatives=[],
        )


def test_adr_serialization_round_trip() -> None:
    adr = ArchitectureDecisionRecord(
        title="t",
        context="c",
        decision="d",
        rationale="r",
        trade_offs=["a"],
        alternatives=["b"],
    )
    loaded = ArchitectureDecisionRecord.model_validate_json(adr.model_dump_json())
    assert loaded == adr
