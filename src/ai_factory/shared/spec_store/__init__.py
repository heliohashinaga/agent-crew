"""Versioned, local persistence of approved specs (FR-025) and the hand-off seam."""

from ai_factory.shared.spec_store.handoff import (
    PublicationError,
    load_spec_by_ref,
    publish_approved,
)
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
    "PublicationError",
    "SpecVersion",
    "StoreError",
    "generate_version_id",
    "load_spec_by_ref",
    "publish_approved",
]
