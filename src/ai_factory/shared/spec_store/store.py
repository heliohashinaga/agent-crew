"""Local-filesystem spec store (T011, FR-025).

Persists approved :class:`SpecVersion` records to disk with:

- **Versioning** — versions are monotonic per feature.
- **Stable ids** — ``spec_version_id`` is deterministic for a given
  feature+version, so re-saving (amendment, repro) never flakes the id.
- **Atomic writes** — a temp-file-then-rename so a crash mid-write never
  leaves a corrupt ``.json`` behind.

Layout under the root::

    root/{feature_slug}/{spec_version_id}.json
    root/{feature_slug}/latest.json        # points at the current version
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from ai_factory.shared.spec_store.models import SpecVersion


class StoreError(RuntimeError):
    """Raised when a spec cannot be read back or persisted cleanly."""


def generate_version_id(feature_slug: str, version: int) -> str:
    """Deterministic, stable ``spec_version_id`` for a feature + version."""
    digest = hashlib.sha256(f"{feature_slug}::v{version}".encode()).hexdigest()[:8]
    return f"{feature_slug}-v{version}-{digest}"


class FileSpecStore:
    """A local-filesystem, versioned store for :class:`SpecVersion` records."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    # -- paths -----------------------------------------------------------------
    def _feature_dir(self, feature_slug: str) -> Path:
        return self.root / feature_slug

    def _spec_path(self, feature_slug: str, spec_version_id: str) -> Path:
        return self._feature_dir(feature_slug) / f"{spec_version_id}.json"

    # -- persistence -----------------------------------------------------------
    def save(self, spec: SpecVersion) -> SpecVersion:
        """Persist ``spec`` and return it with a final stable id/version."""
        feature_slug = spec.feature_slug
        latest = self.latest(feature_slug)
        version = (
            spec.version if spec.version else (latest.version + 1 if latest else 1)
        )
        if not spec.spec_version_id:
            spec.spec_version_id = generate_version_id(feature_slug, version)

        feature_dir = self._feature_dir(feature_slug)
        feature_dir.mkdir(parents=True, exist_ok=True)
        path = self._spec_path(feature_slug, spec.spec_version_id)

        payload = spec.model_dump_json(indent=2)
        self._atomic_write(path, payload)
        self._atomic_write(self._latest_path(feature_slug), spec.spec_version_id)
        return spec

    def load(self, spec_version_id: str) -> SpecVersion | None:
        """Load a spec by its stable id, or ``None`` if absent."""
        feature_slug = self._feature_from_id(spec_version_id)
        if feature_slug is None:
            return None
        path = self._spec_path(feature_slug, spec_version_id)
        if not path.exists():
            return None
        try:
            return SpecVersion.model_validate_json(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:  # pydantic ValidationError is a ValueError
            raise StoreError(
                f"Cannot parse spec {spec_version_id!r} at {path}: {exc}"
            ) from exc

    def list_feature_versions(self, feature_slug: str) -> list[SpecVersion]:
        """Return all persisted versions for a feature, ascending by version."""
        feature_dir = self._feature_dir(feature_slug)
        if not feature_dir.exists():
            return []
        specs: list[SpecVersion] = []
        for path in sorted(feature_dir.glob("*.json")):
            if path.name == "latest.json":
                continue
            try:
                specs.append(
                    SpecVersion.model_validate_json(path.read_text(encoding="utf-8"))
                )
            except ValueError, OSError:
                # Skip unreadable files rather than failing the whole listing.
                continue
        specs.sort(key=lambda s: s.version)
        return specs

    def latest(self, feature_slug: str) -> SpecVersion | None:
        """Return the highest-versioned spec for a feature, or ``None``."""
        versions = self.list_feature_versions(feature_slug)
        return versions[-1] if versions else None

    # -- internals -------------------------------------------------------------
    def _latest_path(self, feature_slug: str) -> Path:
        return self._feature_dir(feature_slug) / "latest.json"

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    @staticmethod
    def _feature_from_id(spec_version_id: str) -> str | None:
        """Recover the feature slug embedded in a ``spec_version_id``."""
        marker = "-v"
        if marker not in spec_version_id:
            return None
        # Format: {feature_slug}-v{version}-{hash}. The slug itself may
        # contain hyphens, so locate the LAST ``-v<digit>`` segment.
        head = spec_version_id[: spec_version_id.rfind(marker)]
        if not head:
            return None
        # Trim a trailing hyphen that preceded the version marker.
        return head.rstrip("-")


__all__ = ["FileSpecStore", "StoreError", "generate_version_id"]
