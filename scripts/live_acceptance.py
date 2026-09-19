#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

REQUIRED_CHECKS = {
    "everkeep.readiness",
    "postgres.migrations",
    "identity.authenticated-flow",
    "privacy.deliberate-denial",
    "wardveil.deliberate-denial",
    "mesh.delivery-retry",
    "adapter.cursor-restart",
    "runtime.durable-restart",
}
EXPECTED_PROVIDERS = {
    "everkeep.readiness": "everkeep",
    "postgres.migrations": "postgresql",
    "identity.authenticated-flow": "goreecloud-identity",
    "privacy.deliberate-denial": "privacy-shield",
    "wardveil.deliberate-denial": "wardveil-security",
    "mesh.delivery-retry": "goreecloud-mesh",
    "adapter.cursor-restart": "everkeep",
    "runtime.durable-restart": "everkeep",
}
MAX_EVIDENCE_AGE_SECONDS = 3600
MAX_FUTURE_SKEW_SECONDS = 60
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
VALID_ENVIRONMENTS = {"staging", "production"}


@dataclass(frozen=True)
class AcceptanceCheck:
    name: str
    status: str
    authoritative: bool
    evidence: dict[str, Any]


def _exact_revision(value: Any) -> bool:
    return isinstance(value, str) and REVISION_RE.fullmatch(value) is not None


def _common_evidence_is_bound(check: AcceptanceCheck, *, environment: str, source_revision: str, captured_at: datetime) -> bool:
    evidence = check.evidence
    if not isinstance(evidence, dict):
        return False
    if evidence.get("provider") != EXPECTED_PROVIDERS.get(check.name):
        return False
    if evidence.get("environment") != environment:
        return False
    if not _exact_revision(source_revision) or evidence.get("everkeep_revision") != source_revision:
        return False
    if not str(evidence.get("evidence_id", "")).strip():
        return False
    observed_at = str(evidence.get("observed_at", "")).strip()
    try:
        parsed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        return False
    observed_utc = parsed.astimezone(timezone.utc)
    captured_utc = captured_at.astimezone(timezone.utc)
    if observed_utc > captured_utc + timedelta(seconds=MAX_FUTURE_SKEW_SECONDS):
        return False
    if captured_utc - observed_utc > timedelta(seconds=MAX_EVIDENCE_AGE_SECONDS):
        return False
    return True


def _check_specific_evidence_is_authoritative(check: AcceptanceCheck) -> bool:
    evidence = check.evidence
    match check.name:
        case "everkeep.readiness":
            return evidence.get("ready") is True and _exact_revision(evidence.get("deployed_revision")) and evidence.get("deployed_revision") == evidence.get("everkeep_revision")
        case "postgres.migrations":
            return evidence.get("database_reachable") is True and evidence.get("migrations_current") is True
        case "identity.authenticated-flow":
            return evidence.get("service_id") == "everkeep" and evidence.get("authenticated_request_succeeded") is True and evidence.get("unauthorized_request_rejected") is True and _exact_revision(evidence.get("provider_revision"))
        case "privacy.deliberate-denial":
            return evidence.get("denial_observed") is True and evidence.get("mutation_committed") is False and bool(str(evidence.get("decision_id", "")).strip()) and _exact_revision(evidence.get("provider_revision"))
        case "wardveil.deliberate-denial":
            return evidence.get("denial_observed") is True and evidence.get("mutation_committed") is False and bool(str(evidence.get("audit_reference", "")).strip()) and _exact_revision(evidence.get("provider_revision"))
        case "mesh.delivery-retry":
            return evidence.get("delivery_succeeded") is True and evidence.get("transient_failure_observed") is True and evidence.get("retry_preserved") is True and bool(str(evidence.get("event_id", "")).strip()) and _exact_revision(evidence.get("provider_revision"))
        case "adapter.cursor-restart":
            return evidence.get("restart_observed") is True and evidence.get("cursor_resumed") is True and evidence.get("duplicate_detected") is False and evidence.get("skip_detected") is False and bool(str(evidence.get("adapter_id", "")).strip())
        case "runtime.durable-restart":
            return evidence.get("restart_observed") is True and evidence.get("durable_state_preserved") is True and evidence.get("idempotency_preserved") is True and evidence.get("pending_outbox_preserved") is True
        case _:
            return False


def evidence_is_authoritative(check: AcceptanceCheck, *, environment: str, source_revision: str, captured_at: datetime | None = None) -> bool:
    captured = captured_at or datetime.now(timezone.utc)
    if captured.tzinfo is None:
        return False
    return _common_evidence_is_bound(check, environment=environment, source_revision=source_revision, captured_at=captured) and _check_specific_evidence_is_authoritative(check)


def evaluate(checks: Iterable[AcceptanceCheck], environment: str, source_revision: str, *, captured_at: datetime | None = None) -> dict[str, Any]:
    captured = captured_at or datetime.now(timezone.utc)
    if captured.tzinfo is None:
        raise ValueError("captured_at must be timezone-aware")
    captured = captured.astimezone(timezone.utc)
    checks = list(checks)
    by_name = {check.name: check for check in checks}
    unique = len(by_name) == len(checks)
    complete = set(by_name) == REQUIRED_CHECKS
    environment_valid = environment in VALID_ENVIRONMENTS
    required_evidence_ids = [str(by_name[name].evidence.get("evidence_id", "")).strip() if isinstance(by_name[name].evidence, dict) else "" for name in REQUIRED_CHECKS] if complete else []
    evidence_ids_unique = complete and all(required_evidence_ids) and len(set(required_evidence_ids)) == len(required_evidence_ids)
    accepted = environment_valid and _exact_revision(source_revision) and unique and complete and evidence_ids_unique and all(
        by_name[name].status == "pass" and by_name[name].authoritative and evidence_is_authoritative(by_name[name], environment=environment, source_revision=source_revision, captured_at=captured)
        for name in REQUIRED_CHECKS
    )
    return {
        "schemaVersion": "1.1",
        "environment": environment,
        "capturedAt": captured.isoformat(),
        "sourceRevision": source_revision,
        "checks": [asdict(check) for check in checks],
        "accepted": accepted,
    }


def failed_or_unknown(name: str, reason: str) -> AcceptanceCheck:
    return AcceptanceCheck(name=name, status="unknown", authoritative=False, evidence={"reason": reason})
