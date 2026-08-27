#!/usr/bin/env python3
"""Deterministic Preservation Capsule and portability-manifest builders."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone


class PreservationError(ValueError):
    pass


def _utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _aggregate_integrity(entries):
    states = [entry.get("integrityVerified") for entry in entries]
    if any(state is False for state in states):
        return "failed"
    if states and all(state is True for state in states):
        return "verified"
    return "unknown"


def build_capsule(capsule_id, resources, preservation_tier="archive", created_at=None, policy_refs=None):
    if preservation_tier not in {"protected", "archive", "permanent"}:
        raise PreservationError("unsupported preservation tier")
    if not resources:
        raise PreservationError("a preservation capsule requires at least one resource")

    entries = []
    evidence_refs = set()
    for resource in sorted(resources, key=lambda item: item["resourceId"]):
        digest = resource.get("contentDigest") or {}
        if not digest.get("algorithm") or not digest.get("value"):
            raise PreservationError(f"resource {resource['resourceId']} lacks a content digest")
        entry_evidence = sorted(set(resource.get("evidenceRefs", [])))
        evidence_refs.update(entry_evidence)
        entries.append({
            "resourceId": resource["resourceId"],
            "contentDigest": {"algorithm": digest["algorithm"], "value": digest["value"]},
            "mediaType": resource.get("mediaType"),
            "sizeBytes": resource.get("sizeBytes"),
            "provenanceRefs": sorted(set(resource.get("provenanceRefs", []))),
            "relationshipRefs": sorted(set(resource.get("relationshipRefs", []))),
            "evidenceRefs": entry_evidence,
            "integrityVerified": resource.get("integrityVerified"),
        })

    digest_input = {
        "formatVersion": "everkeep-capsule/1",
        "preservationTier": preservation_tier,
        "entries": entries,
        "policyRefs": sorted(set(policy_refs or [])),
    }
    capsule_digest = hashlib.sha256(_canonical(digest_input).encode("utf-8")).hexdigest()
    return {
        "schemaVersion": "1.0",
        "capsuleId": capsule_id,
        "createdAt": created_at or _utc_now(),
        "preservationTier": preservation_tier,
        "formatVersion": "everkeep-capsule/1",
        "entries": entries,
        "integrityState": _aggregate_integrity(entries),
        "capsuleDigest": {"algorithm": "sha256", "value": capsule_digest},
        "policyRefs": sorted(set(policy_refs or [])),
        "evidenceRefs": sorted(evidence_refs),
    }


def build_export_manifest(export_id, capsule, export_format, authority_evidence, created_at=None):
    state = authority_evidence.get("state", "unknown")
    if state not in {"pass", "fail", "unknown"}:
        state = "unknown"
    integrity_state = capsule.get("integrityState", "unknown")
    portable = state == "pass" and integrity_state == "verified"
    evidence_refs = set(capsule.get("evidenceRefs", []))
    authority_ref = authority_evidence.get("evidenceRef")
    if authority_ref:
        evidence_refs.add(authority_ref)

    if portable:
        reason = None
    elif state != "pass":
        reason = "Export authority is not explicitly permitted by current evidence."
    else:
        reason = "Capsule integrity is not currently verified."

    return {
        "schemaVersion": "1.0",
        "exportId": export_id,
        "capsuleId": capsule["capsuleId"],
        "createdAt": created_at or _utc_now(),
        "exportFormat": export_format,
        "authorityState": state,
        "integrityState": integrity_state,
        "portable": portable,
        "entries": [
            {"resourceId": entry["resourceId"], "contentDigest": entry["contentDigest"]}
            for entry in capsule["entries"]
        ],
        "evidenceRefs": sorted(evidence_refs),
        "reason": reason,
    }
