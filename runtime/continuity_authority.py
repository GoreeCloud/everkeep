#!/usr/bin/env python3
"""Read-only runtime authority adapter boundary for Everkeep continuity gates.

Providers are injected by deployment and are queried only through read_decision.
The adapter does not mint authority, alter provider state, store credentials, or
extend producer validity windows.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class ContinuityAuthorityError(ValueError):
    pass


def _parse_time(value: str | None):
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_authority_evidence(
    provider: Any,
    *,
    gate: str,
    expected_authority: str,
    subject_ref: str,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Read and normalize one authoritative gate without mutating the provider."""
    if not gate or not expected_authority or not subject_ref:
        raise ContinuityAuthorityError("gate, expected_authority, and subject_ref are required")
    now = _parse_time(observed_at) if observed_at else datetime.now(timezone.utc)
    if now is None:
        raise ContinuityAuthorityError("observed_at must be an ISO 8601 date-time")

    try:
        result = provider.read_decision(gate=gate, subject_ref=subject_ref)
    except Exception as exc:
        return {
            "state": "unknown",
            "authority": expected_authority,
            "evidenceRef": None,
            "observedAt": now.isoformat().replace("+00:00", "Z"),
            "validUntil": None,
            "reason": f"authority read failed: {type(exc).__name__}",
            "readOnly": True,
            "credentialsEmbedded": False,
        }

    if not isinstance(result, dict):
        result = {}
    state = result.get("state") if result.get("state") in {"pass", "fail", "unknown"} else "unknown"
    authority = result.get("authority")
    evidence_ref = result.get("evidenceRef")
    valid_until = _parse_time(result.get("validUntil"))
    reason = result.get("reason")
    if authority != expected_authority or not evidence_ref or valid_until is None or valid_until <= now:
        state = "unknown"
    return {
        "state": state,
        "authority": expected_authority,
        "evidenceRef": evidence_ref if isinstance(evidence_ref, str) and evidence_ref else None,
        "observedAt": now.isoformat().replace("+00:00", "Z"),
        "validUntil": valid_until.isoformat().replace("+00:00", "Z") if valid_until else None,
        "reason": reason if isinstance(reason, str) and reason else None,
        "readOnly": True,
        "credentialsEmbedded": False,
    }
