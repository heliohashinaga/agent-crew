"""Versioned, local persistence of approved specs (FR-025)."""

from ai_factory.shared.spec_store.models import (
    AcceptanceCriterion,
    Approval,
    Assumption,
    Clarification,
    EdgeCase,
    FeatureRequest,
    SpecVersion,
)
from ai_factory.shared.spec_store.store import (
    FileSpecStore,
    StoreError,
    generate_version_id,
)

__all__ = [
    "AcceptanceCriterion",
    "Approval",
    "Assumption",
    "Clarification",
    "EdgeCase",
    "FeatureRequest",
    "FileSpecStore",
    "SpecVersion",
    "StoreError",
    "generate_version_id",
]