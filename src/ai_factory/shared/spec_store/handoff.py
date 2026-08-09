"""Spec → dev hand-off seam (T024, FR-025, SC-017).

The only thing a Development run inherits from a Specification run is a
*reference* — the stable ``spec_version_id`` (plus the originating
``spec_run_id``). This module is that seam: it publishes an approved
:class:`SpecVersion` with a stable id and exposes a read-by-reference loader.
The dev workflow must load by reference and never re-derive the requirements.
"""

from __future__ import annotations

from ai_factory.shared.spec_store.models import ApprovalStatus, SpecVersion
from ai_factory.shared.spec_store.store import FileSpecStore


class PublicationError(RuntimeError):
    """Raised when an unapproved spec is published."""


def publish_approved(spec: SpecVersion, store: FileSpecStore) -> SpecVersion:
    """Persist ``spec`` as an approved, versioned record.

    Marks the spec approved + human-approved (FR-005), assigns a stable
    ``spec_version_id`` via the store, and returns the persisted record —
    the join key a dev run carries.
    """
    if spec.approval_status != ApprovalStatus.APPROVED or not spec.human_approved:
        raise PublicationError(
            "Cannot publish a spec that is not human-approved (human_approved=True, "
            "approval_status='approved')"
        )
    return store.save(spec)


def load_spec_by_ref(spec_version_id: str, store: FileSpecStore) -> SpecVersion | None:
    """Load a spec by its stable ``spec_version_id`` reference.

    Returns ``None`` if the version is unknown. The dev workflow consumes the
    result by reference — it never re-derives requirements from prose.
    """
    return store.load(spec_version_id)


__all__ = ["PublicationError", "load_spec_by_ref", "publish_approved"]
