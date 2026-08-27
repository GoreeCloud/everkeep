"""Validated Everkeep evidence handoff for GoreeCloud Mesh refresh responses.

This module only emits a completed handling receipt when a separately produced,
current Everkeep Mesh Evidence Envelope is exactly bound to the original refresh
intent and producer revision. It performs no backup, restore, failover,
preservation, export, succession, or recovery effect.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re

from runtime.mesh_evidence import validate_mesh_evidence_refresh_intent
from runtime.mesh_refresh_response import create_mesh_evidence_refresh_response

EVIDENCE_VERSION = "goreecloud.evidence-envelope.v1"
EVERKEEP_REPOSITORY = "GoreeCloud/goreecloud-everkeep"
EVERKEEP_CONTRACT_PREFIX = "contracts/everkeep."
REVISION = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
DATA_CLASSES = {"public", "operational", "derived"}
EVIDENCE_FIELDS = {
    "version", "id", "producer", "authority_domain", "subject", "assertion",
    "outcome", "source", "observed_at", "valid_until", "data_class", "summary",
    "payload_digest", "contains_user_content", "contains_secret_material",
}


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


def _subject(subject: object, field: str) -> tuple[str, str, str]:
    if not isinstance(subject, dict) or set(subject) - {"kind", "id", "scope"}:
        raise ValueError(f"{field} is invalid")
    return (
        _bounded(subject.get("kind"), f"{field}.kind", 64, required=True),
        _bounded(subject.get("id"), f"{field}.id", 256, required=True),
        _bounded(subject.get("scope"), f"{field}.scope", 256),
    )


def _validate_produced_evidence(
    accepted: dict,
    envelope: dict,
    *,
    revision: str,
    response_time: datetime,
    evaluated_at: datetime,
) -> str:
    if not isinstance(envelope, dict):
        raise ValueError("evidence_envelope must be an object")
    unknown = set(envelope) - EVIDENCE_FIELDS
    if unknown:
        raise ValueError(f"unexpected evidence envelope fields: {', '.join(sorted(unknown))}")
    if envelope.get("version") != EVIDENCE_VERSION:
        raise ValueError("unsupported evidence envelope version")
    envelope_id = _bounded(envelope.get("id"), "evidence_envelope.id", 128, required=True)

    producer = envelope.get("producer")
    if not isinstance(producer, dict) or set(producer) != {"system", "repository", "revision", "contract"}:
        raise ValueError("evidence producer identity is invalid")
    if not REVISION.fullmatch(str(revision or "")):
        raise ValueError("revision must be an exact 40-character lowercase Git revision")
    if (
        producer.get("system") != "everkeep"
        or producer.get("repository") != EVERKEEP_REPOSITORY
        or producer.get("revision") != revision
    ):
        raise ValueError("evidence producer provenance must match the Everkeep refresh response")
    contract = _bounded(producer.get("contract"), "evidence producer contract", 512, required=True)
    if not contract.startswith(EVERKEEP_CONTRACT_PREFIX):
        raise ValueError("evidence producer contract must belong to Everkeep")

    if envelope.get("authority_domain") != accepted.get("authority_domain"):
        raise ValueError("evidence authority domain does not match the refresh intent")
    if _subject(envelope.get("subject"), "evidence.subject") != _subject(accepted.get("subject"), "intent.subject"):
        raise ValueError("evidence subject does not match the refresh intent")
    if _bounded(envelope.get("assertion"), "evidence assertion", 128, required=True) != _bounded(
        accepted.get("assertion"), "intent assertion", 128, required=True
    ):
        raise ValueError("evidence assertion does not match the refresh intent")

    _bounded(envelope.get("outcome"), "evidence outcome", 128, required=True)
    _bounded(envelope.get("source"), "evidence source", 512, required=True)
    _bounded(envelope.get("summary"), "evidence summary", 512)
    if envelope.get("data_class") not in DATA_CLASSES:
        raise ValueError("invalid evidence data class")
    digest = str(envelope.get("payload_digest") or "")
    if digest and not DIGEST.fullmatch(digest):
        raise ValueError("evidence payload_digest must use sha256:<64 lowercase hex characters>")
    if envelope.get("contains_user_content") is not False or envelope.get("contains_secret_material") is not False:
        raise ValueError("evidence envelope must exclude user content and secret material")

    requested_at = _parse(accepted.get("requested_at"), "intent.requested_at")
    observed_at = _parse(envelope.get("observed_at"), "evidence.observed_at")
    valid_until = _parse(envelope.get("valid_until"), "evidence.valid_until")
    if observed_at < requested_at:
        raise ValueError("refresh evidence observation predates the refresh request")
    if observed_at > response_time:
        raise ValueError("refresh response cannot reference evidence observed after the response")
    if valid_until <= observed_at:
        raise ValueError("evidence valid_until must be after observed_at")
    if valid_until < evaluated_at:
        raise ValueError("refresh response cannot reference expired evidence")
    return envelope_id


def create_mesh_evidence_refresh_response_for_evidence(
    intent: dict,
    *,
    response_id: str,
    revision: str,
    evidence_envelope: dict,
    reason_code: str = "evidence-issued",
    responded_at: datetime | None = None,
    now: datetime | None = None,
) -> dict:
    """Create a completed Everkeep receipt only after exact evidence binding."""
    evaluated_at = _utc(now or datetime.now(timezone.utc), "now")
    accepted = validate_mesh_evidence_refresh_intent(intent, now=evaluated_at)
    response_time = _utc(responded_at or evaluated_at, "responded_at")
    evidence_id = _validate_produced_evidence(
        accepted,
        evidence_envelope,
        revision=revision,
        response_time=response_time,
        evaluated_at=evaluated_at,
    )
    return create_mesh_evidence_refresh_response(
        accepted,
        response_id=response_id,
        revision=revision,
        status="completed",
        reason_code=reason_code,
        responded_at=response_time,
        evidence_envelope_id=evidence_id,
        now=evaluated_at,
    )
