"""Validate dimension references against a supplied versioned crosswalk."""

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .materialize import materialize


class CrosswalkError(ValueError):
    """A crosswalk lacks provenance or contains conflicting records."""


DimensionKey = tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class PreparedCrosswalk:
    """Immutable snapshot of validated evidence, reusable across observation batches.

    Prepare again when the source table changes; later mutations of that table do
    not affect this snapshot. A missing table yields pending outcomes.
    """

    _allowed: frozenset[DimensionKey] | None

    def validate(self, observations: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Return one matched or pending outcome per observation."""
        if self._allowed is None:
            return [{"status": "pending", "reason": "crosswalk_unavailable"} for _ in observations]
        outcomes = []
        for observation in observations:
            dimensions = materialize([observation])["dimensions"]
            if not dimensions or any(
                tuple(sorted(item.items())) not in self._allowed for item in dimensions
            ):
                outcomes.append({"status": "pending", "reason": "crosswalk_entry_missing"})
            else:
                outcomes.append({"status": "matched_local", "reason": ""})
        return outcomes


def prepare_crosswalk(crosswalk: dict[str, Any] | None) -> PreparedCrosswalk:
    """Check provenance and materialize the evidence table once for reuse.

    This checks internal integrity and membership, not official authenticity.
    """
    if crosswalk is None:
        return PreparedCrosswalk(None)
    provenance = crosswalk.get("provenance")
    if not isinstance(provenance, dict) or not all(
        isinstance(provenance.get(k), str) and provenance[k].strip()
        for k in ("source", "version", "artifact_sha256")
    ):
        raise CrosswalkError("crosswalk provenance requires source, version and artifact_sha256")
    checksum = provenance["artifact_sha256"]
    if len(checksum) != 64 or any(c not in "0123456789abcdef" for c in checksum):
        raise CrosswalkError("artifact_sha256 must be a lowercase SHA-256")
    entries = crosswalk.get("entries")
    if not isinstance(entries, list):
        raise CrosswalkError("crosswalk entries must be a list")
    serialized = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if hashlib.sha256(serialized.encode("utf-8")).hexdigest() != checksum:
        raise CrosswalkError("artifact_sha256 does not match canonical entries")
    try:
        catalog = materialize(entries)["dimensions"]
    except (ValueError, TypeError, AttributeError) as exc:
        raise CrosswalkError("invalid or conflicting crosswalk entries") from exc
    return PreparedCrosswalk(frozenset(tuple(sorted(item.items())) for item in catalog))


def validate_crosswalk(
    observations: list[dict[str, Any]], crosswalk: dict[str, Any] | None
) -> list[dict[str, str]]:
    """Return matched/pending outcomes using the supplied evidence table.

    For repeated batches, call prepare_crosswalk once and reuse its validate
    method. Absence is pending, not evidence that a code is invalid.
    """
    return prepare_crosswalk(crosswalk).validate(observations)
