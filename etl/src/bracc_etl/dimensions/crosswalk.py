"""Validate dimension references against a supplied versioned crosswalk."""

import hashlib
import json
from typing import Any

from .materialize import materialize


class CrosswalkError(ValueError):
    """A crosswalk lacks provenance or contains conflicting records."""


def validate_crosswalk(
    observations: list[dict[str, Any]], crosswalk: dict[str, Any] | None
) -> list[dict[str, str]]:
    """Return matched/pending outcomes; caller supplies the evidence table.

    Entries use the same explicit identifiers as materialize, with provenance
    for each release. Absence is pending, not evidence that a code is invalid.
    """
    if crosswalk is None:
        return [{"status": "pending", "reason": "crosswalk_unavailable"} for _ in observations]
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
    allowed = {tuple(sorted(item.items())) for item in catalog}
    outcomes = []
    for observation in observations:
        dimensions = materialize([observation])["dimensions"]
        if not dimensions or any(tuple(sorted(item.items())) not in allowed for item in dimensions):
            outcomes.append({"status": "pending", "reason": "crosswalk_entry_missing"})
        else:
            outcomes.append({"status": "matched_local", "reason": ""})
    return outcomes
