"""Bounded Everkeep response adapter for GoreeCloud Mesh evidence refresh intents.

A response reports continuity/recovery evidence-handling state only. It performs
no backup, restore, failover, preservation, export, or recovery effect and cannot
substitute for a separately validated producer-authoritative evidence envelope.
"""
from __future__ import annotations

from datetime import datetime, timezone
import copy
import re

from runtime.mesh_evidence import validate_mesh_evidence_refresh_intent

MESH_REFRESH_RESPONSE_VERSION = "goreecloud.evidence-refresh-response.v1"
EVERKEEP_REPOSITORY = "GoreeCloud/goreecloud-everkeep"
REVISION = re.compile(r"^[0-9a-f]{40}$")
STATUSES = {"received", "completed", "declined", "unavailable"}


def _utc(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{field} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _parse(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be RFC3339/ISO8601") from exc
    return _utc(parsed, field)


def _bounded(value: object, field: str, maximum: int, *, required: bool = False) -> str:
    normalized = str(value or "").strip()
    if required and not normalized:
        raise ValueError(f"{field} is required")
    if len(normalized) > maximum:
        raise ValueError(f"{field} must be at most {maximum} characters")
    return normalized


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def create_mesh_evidence_refresh_response(
    intent: dict,
    *,
    response_id: str,
    revision: str,
    status: str,
    reason_code: str = "",
    responded_at: datetime | None = None,
    evidence_envelope_id: str = "",
    now: datetime | None = None,
) -> dict:
    """Create a minimized Everkeep handling receipt for a valid Mesh intent."""
    evaluated_at = _utc(now or datetime.now(timezone.utc), "now")
    accepted = validate_mesh_evidence_refresh_intent(intent, now=evaluated_at)
    response_id = _bounded(response_id, "response_id", 128, required=True)
    if not REVISION.fullmatch(str(revision or "")):
        raise ValueError("revision must be an exact 40-character lowercase Git revision")
    if status not in STATUSES:
        raise ValueError("invalid refresh response status")
    reason_code = _bounded(reason_code, "reason_code", 64)
    evidence_envelope_id = _bounded(evidence_envelope_id, "evidence_envelope_id", 128)

    response_time = _utc(responded_at or evaluated_at, "responded_at")
    requested_at = _parse(accepted.get("requested_at"), "intent.requested_at")
    if response_time < requested_at or response_time > evaluated_at:
        raise ValueError("responded_at must be between requested_at and now")
    if evidence_envelope_id and status != "completed":
        raise ValueError("only a completed refresh response may reference produced evidence")

    response = {
        "version": MESH_REFRESH_RESPONSE_VERSION,
        "id": response_id,
        "intent": {
            "id": accepted["id"],
            "coordinator_revision": accepted["coordinator"]["revision"],
            "reason": accepted["reason"],
            "requested_at": _iso(requested_at),
        },
        "producer": {
            "system": "everkeep",
            "repository": EVERKEEP_REPOSITORY,
            "revision": revision,
        },
        "authority_domain": accepted["authority_domain"],
        "subject": copy.deepcopy(accepted["subject"]),
        "assertion": accepted["assertion"],
        "status": status,
        "responded_at": _iso(response_time),
        "evidence_produced": bool(evidence_envelope_id),
        "contains_user_content": False,
        "contains_secret_material": False,
        "authority_transferred": False,
        "execution_authorized": False,
    }
    if reason_code:
        response["reason_code"] = reason_code
    if evidence_envelope_id:
        response["evidence_envelope_id"] = evidence_envelope_id
    return response
