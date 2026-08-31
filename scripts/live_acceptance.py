#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
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


@dataclass(frozen=True)
class AcceptanceCheck:
    name: str
    status: str
    authoritative: bool
    evidence: dict[str, Any]


def _common_evidence_is_bound(
    check: AcceptanceCheck,
    *,
    environment: str,
    source_revision: str,
) -> bool:
    evidence = check.evidence
    if not isinstance(evidence, dict):
        return False
    if evidence.get("provider") != EXPECTED_PROVIDERS.get(check.name):
        return False
    if evidence.get("environment") != environment:
        return False
    if evidence.get("everkeep_revision") != source_revision:
        return False
    if not str(evidence.get("evidence_id", "")).strip():
        return False
    observed_at = str(evidence.get("observed_at", "")).strip()
    try:
        parsed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _check_specific_evidence_is_authoritative(check: AcceptanceCheck) -> bool:
    evidence = check.evidence
    match check.name:
        case "everkeep.readiness":
            return (
                evidence.get("ready") is True
                and evidence.get("deployed_revision") == evidence.get("everkeep_revision")
            )
        case "postgres.migrations":
            return evidence.get("database_reachable") is True and evidence.get("migrations_current") is True
        case "identity.authenticated-flow":
            return (
                evidence.get("service_id") == "everkeep"
                and evidence.get("authenticated_request_succeeded") is True
                and evidence.get("unauthorized_request_rejected") is True
                and bool(str(evidence.get("provider_revision", "")).strip())
            )
        case "privacy.deliberate-denial":
            return (
                evidence.get("denial_observed") is True
                and evidence.get("mutation_committed") is False
                and bool(str(evidence.get("decision_id", "")).strip())
                and bool(str(evidence.get("provider_revision", "")).strip())
            )
        case "wardveil.deliberate-denial":
            return (
                evidence.get("denial_observed") is True
                and evidence.get("mutation_committed") is False
                and bool(str(evidence.get("audit_reference", "")).strip())
                and bool(str(evidence.get("provider_revision", "")).strip())
            )
        case "mesh.delivery-retry":
            return (
                evidence.get("delivery_succeeded") is True
                and evidence.get("transient_failure_observed") is True
                and evidence.get("retry_preserved") is True
                and bool(str(evidence.get("event_id", "")).strip())
                and bool(str(evidence.get("provider_revision", "")).strip())
            )
        case "adapter.cursor-restart":
            return (
                evidence.get("restart_observed") is True
                and evidence.get("cursor_resumed") is True
                and evidence.get("duplicate_detected") is False
                and evidence.get("skip_detected") is False
                and bool(str(evidence.get("adapter_id", "")).strip())
            )
        case "runtime.durable-restart":
            return (
                evidence.get("restart_observed") is True
                and evidence.get("durable_state_preserved") is True
                and evidence.get("idempotency_preserved") is True
                and evidence.get("pending_outbox_preserved") is True
            )
        case _:
            return False


def evidence_is_authoritative(
    check: AcceptanceCheck,
    *,
    environment: str,
    source_revision: str,
) -> bool:
    return _common_evidence_is_bound(
        check,
        environment=environment,
        source_revision=source_revision,
    ) and _check_specific_evidence_is_authoritative(check)


def evaluate(
    checks: Iterable[AcceptanceCheck],
    environment: str,
    source_revision: str,
) -> dict[str, Any]:
    checks = list(checks)
    by_name = {check.name: check for check in checks}
    unique = len(by_name) == len(checks)
    complete = REQUIRED_CHECKS.issubset(by_name)
    accepted = unique and complete and all(
        by_name[name].status == "pass"
        and by_name[name].authoritative
        and evidence_is_authoritative(
            by_name[name],
            environment=environment,
            source_revision=source_revision,
        )
        for name in REQUIRED_CHECKS
    )
    return {
        "schemaVersion": "1.1",
        "environment": environment,
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "sourceRevision": source_revision,
        "checks": [asdict(check) for check in checks],
        "accepted": accepted,
    }


def failed_or_unknown(name: str, reason: str) -> AcceptanceCheck:
    return AcceptanceCheck(
        name=name,
        status="unknown",
        authoritative=False,
        evidence={"reason": reason},
    )
