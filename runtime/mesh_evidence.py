"""Everkeep producer adapter for GoreeCloud Mesh Evidence Envelope v1."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import re

MESH_EVIDENCE_VERSION = "goreecloud.evidence-envelope.v1"
EVERKEEP_REPOSITORY = "GoreeCloud/goreecloud-everkeep"
REVISION = re.compile(r"^[0-9a-f]{40}$")


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _time(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be RFC3339/ISO8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include timezone")
    return parsed.astimezone(timezone.utc)


def create_restore_verification_envelope(
    evidence: dict,
    *,
    valid_until: str,
    observed_at: datetime | None = None,
) -> dict:
    """Emit minimized restore-verification evidence for Mesh transport.

    Recovery payloads, backup/archive contents, evidenceRef targets, free-form
    notes, credentials, and private resource content are not transported.
    """
    if not isinstance(evidence, dict):
        raise ValueError("restore verification evidence must be an object")
    if evidence.get("authoritative") is not True:
        raise ValueError("restore verification evidence must be authoritative")

    revision = str(evidence.get("everkeepSourceRevision") or "").strip()
    if not REVISION.fullmatch(revision):
        raise ValueError("everkeepSourceRevision must be an exact 40-character lowercase Git revision")

    verification_id = str(evidence.get("verificationId") or "").strip()
    target = evidence.get("target") or {}
    resource_id = str(target.get("resourceId") or "").strip()
    component = str(target.get("component") or "").strip()
    status = str(evidence.get("status") or "").strip()
    if not verification_id or not resource_id or status not in {"pass", "fail", "unknown"}:
        raise ValueError("verificationId, target.resourceId, and valid status are required")

    captured_at = _time(evidence.get("capturedAt"), "capturedAt")
    evaluated_at = (observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if captured_at > evaluated_at:
        raise ValueError("capturedAt cannot be in the future")
    expires = _time(valid_until, "valid_until")
    if expires <= captured_at:
        raise ValueError("valid_until must be after capturedAt")
    if expires < evaluated_at:
        raise ValueError("cannot emit expired Everkeep evidence")

    exercise = evidence.get("exercise") or {}
    integrity = bool(exercise.get("integrityVerified"))
    restored = bool(exercise.get("restoredStateVerified"))
    summary = f"Everkeep restore verification: {status}; integrity_verified={str(integrity).lower()}; restored_state_verified={str(restored).lower()}."

    return {
        "version": MESH_EVIDENCE_VERSION,
        "id": f"everkeep-{verification_id}",
        "producer": {
            "system": "everkeep",
            "repository": EVERKEEP_REPOSITORY,
            "revision": revision,
            "contract": "contracts/everkeep.restore-verification.schema.json",
        },
        "authority_domain": "recovery",
        "subject": {
            "kind": "resource",
            "id": resource_id,
            "scope": component,
        },
        "assertion": "restore-verification",
        "outcome": status,
        "source": f"everkeep://restore-verification/{verification_id}",
        "observed_at": captured_at.isoformat().replace("+00:00", "Z"),
        "valid_until": expires.isoformat().replace("+00:00", "Z"),
        "data_class": "derived",
        "summary": summary,
        "payload_digest": "sha256:" + sha256(_canonical(evidence)).hexdigest(),
        "contains_user_content": False,
        "contains_secret_material": False,
    }
