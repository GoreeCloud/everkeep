"""Everkeep producer adapters for GoreeCloud Mesh evidence coordination."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import copy
import json
import re

MESH_EVIDENCE_VERSION = "goreecloud.evidence-envelope.v1"
MESH_REFRESH_INTENT_VERSION = "goreecloud.evidence-refresh-intent.v1"
MESH_REFRESH_CONTRACT = "contracts/mesh.evidence-refresh-intent.schema.json"
MESH_REPOSITORY = "GoreeCloud/goreecloud-mesh"
EVERKEEP_REPOSITORY = "GoreeCloud/goreecloud-everkeep"
REVISION = re.compile(r"^[0-9a-f]{40}$")
REFRESH_REASONS = {"stale", "empty", "manual"}
EVERKEEP_AUTHORITY_DOMAINS = {"resilience", "recovery", "preservation", "continuity"}
REFRESH_FIELDS = {
    "version", "id", "coordinator", "producer", "authority_domain", "subject",
    "assertion", "reason", "requested_at", "latest_observed_at",
    "contains_user_content", "contains_secret_material", "authority_transferred",
    "execution_authorized",
}


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


def validate_mesh_evidence_refresh_intent(intent: dict, *, now: datetime | None = None) -> dict:
    """Validate a Mesh refresh intent addressed to an Everkeep authority domain.

    A valid intent may cause an Everkeep runtime adapter to consider collecting
    new evidence in a future integration. Validation itself performs no backup,
    restore, failover, preservation, export, or recovery action and creates no
    continuity or recovery outcome.
    """
    if not isinstance(intent, dict):
        raise ValueError("refresh intent must be an object")
    unknown = set(intent) - REFRESH_FIELDS
    if unknown:
        raise ValueError(f"unexpected refresh intent fields: {', '.join(sorted(unknown))}")
    if intent.get("version") != MESH_REFRESH_INTENT_VERSION:
        raise ValueError("unsupported refresh intent version")

    coordinator = intent.get("coordinator")
    if not isinstance(coordinator, dict) or set(coordinator) != {"system", "repository", "revision", "contract"}:
        raise ValueError("canonical Mesh coordinator identity is required")
    if coordinator.get("system") != "goreecloud-mesh" or coordinator.get("repository") != MESH_REPOSITORY:
        raise ValueError("refresh intent must be coordinated by GoreeCloud Mesh")
    if not REVISION.fullmatch(str(coordinator.get("revision") or "")):
        raise ValueError("Mesh coordinator revision must be exact")
    if coordinator.get("contract") != MESH_REFRESH_CONTRACT:
        raise ValueError("refresh intent must use the canonical Mesh contract")

    if intent.get("producer") != "everkeep" or intent.get("authority_domain") not in EVERKEEP_AUTHORITY_DOMAINS:
        raise ValueError("refresh intent is not targeted to an Everkeep authority domain")
    subject = intent.get("subject")
    if not isinstance(subject, dict) or set(subject) - {"kind", "id", "scope"}:
        raise ValueError("refresh intent subject is invalid")
    if not str(subject.get("kind") or "").strip() or not str(subject.get("id") or "").strip():
        raise ValueError("refresh intent subject kind and id are required")
    if not str(intent.get("id") or "").strip() or not str(intent.get("assertion") or "").strip():
        raise ValueError("refresh intent id and assertion are required")

    reason = intent.get("reason")
    if reason not in REFRESH_REASONS:
        raise ValueError("invalid refresh reason")
    evaluated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    requested_at = _time(intent.get("requested_at"), "requested_at")
    if requested_at > evaluated_at:
        raise ValueError("requested_at cannot be in the future")
    latest_value = intent.get("latest_observed_at")
    latest = _time(latest_value, "latest_observed_at") if latest_value is not None else None
    if latest is not None and latest > requested_at:
        raise ValueError("latest_observed_at cannot be after requested_at")
    if reason == "stale" and latest is None:
        raise ValueError("stale refresh requires latest_observed_at")
    if reason == "empty" and latest is not None:
        raise ValueError("empty refresh cannot claim an existing observation")

    if intent.get("contains_user_content") is not False or intent.get("contains_secret_material") is not False:
        raise ValueError("refresh intent must not contain user content or secret material")
    if intent.get("authority_transferred") is not False or intent.get("execution_authorized") is not False:
        raise ValueError("refresh intent cannot transfer Everkeep authority or authorize execution")
    return copy.deepcopy(intent)


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
