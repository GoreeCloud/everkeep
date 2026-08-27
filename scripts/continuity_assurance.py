#!/usr/bin/env python3
"""Scheduled, evidence-bounded Everkeep continuity assurance projections.

This module computes when continuity evidence should be re-evaluated, when
recovery-topology evidence becomes stale, and bounded Monitoring/Notify
projections. It does not schedule jobs, probe infrastructure, deliver alerts,
or grant recovery/failover authority.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

ASSURANCE_STATES = {"ready", "attention", "degraded", "unknown"}
SCHEDULE_STATES = {"scheduled", "due", "overdue", "unknown"}
TOPOLOGY_STATES = {"current", "attention", "stale", "unknown"}


class ContinuityAssuranceError(ValueError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _positive_int(policy: dict[str, Any], key: str) -> int:
    value = policy.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ContinuityAssuranceError(f"{key} must be a positive integer")
    return value


def evaluate_assurance(
    policy: dict[str, Any],
    objective: dict[str, Any],
    posture: dict[str, Any],
    topology: dict[str, Any] | None,
    last_evaluated_at: str | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Evaluate continuity assurance freshness without performing external work."""
    policy_id = policy.get("policyId")
    objective_id = objective.get("objectiveId")
    if not policy_id:
        raise ContinuityAssuranceError("policyId is required")
    if not objective_id:
        raise ContinuityAssuranceError("objectiveId is required")
    if policy.get("objectiveId") != objective_id:
        raise ContinuityAssuranceError("assurance policy objective does not match objective")
    if posture.get("objectiveId") != objective_id:
        raise ContinuityAssuranceError("posture objective does not match objective")

    now = _parse_time(observed_at) if observed_at else _utc_now()
    if now is None:
        raise ContinuityAssuranceError("observed_at must be an ISO 8601 date-time")

    interval = _positive_int(policy, "evaluationIntervalSeconds")
    max_topology_age = _positive_int(policy, "maxTopologyAgeSeconds")
    warning_lead = policy.get("warningLeadSeconds", 0)
    if not isinstance(warning_lead, int) or isinstance(warning_lead, bool) or warning_lead < 0:
        raise ContinuityAssuranceError("warningLeadSeconds must be a non-negative integer")
    if warning_lead >= interval or warning_lead >= max_topology_age:
        raise ContinuityAssuranceError(
            "warningLeadSeconds must be smaller than evaluationIntervalSeconds and maxTopologyAgeSeconds"
        )

    blockers: list[str] = []
    warnings: list[str] = []
    evidence_refs = set(posture.get("evidenceRefs", []))

    last_evaluated = _parse_time(last_evaluated_at)
    if last_evaluated_at and last_evaluated is None:
        schedule_state = "unknown"
        next_due = None
        overdue_seconds = 0
        blockers.append("continuity-evaluation-time-unknown")
    elif last_evaluated is None:
        schedule_state = "due"
        next_due = now
        overdue_seconds = 0
        warnings.append("continuity-evaluation-never-run")
    else:
        next_due = last_evaluated + timedelta(seconds=interval)
        remaining = (next_due - now).total_seconds()
        if remaining < 0:
            schedule_state = "overdue"
            overdue_seconds = int(abs(remaining))
            blockers.append("continuity-evaluation-overdue")
        elif remaining <= warning_lead:
            schedule_state = "due"
            overdue_seconds = 0
            warnings.append("continuity-evaluation-due")
        else:
            schedule_state = "scheduled"
            overdue_seconds = 0

    topology_observed = None
    topology_expires = None
    topology_age = None
    topology_remaining = None
    topology_state = "unknown"

    if not isinstance(topology, dict):
        blockers.append("recovery-topology-unknown")
    elif topology.get("authoritative") is not True:
        blockers.append("recovery-topology-not-authoritative")
        evidence_refs.update(topology.get("evidenceRefs", []))
    else:
        evidence_refs.update(topology.get("evidenceRefs", []))
        topology_observed = _parse_time(topology.get("observedAt"))
        if topology_observed is None:
            blockers.append("recovery-topology-time-unknown")
        else:
            topology_age = max(0, int((now - topology_observed).total_seconds()))
            topology_expires = topology_observed + timedelta(seconds=max_topology_age)
            topology_remaining = int((topology_expires - now).total_seconds())
            if topology_remaining < 0:
                topology_state = "stale"
                blockers.append("recovery-topology-stale")
            elif topology_remaining <= warning_lead:
                topology_state = "attention"
                warnings.append("recovery-topology-expiring")
            else:
                topology_state = "current"

    posture_state = posture.get("state", "unknown")
    if posture_state not in {"ready", "attention", "degraded", "unknown"}:
        posture_state = "unknown"
        blockers.append("continuity-posture-state-unknown")
    elif posture_state == "degraded":
        blockers.append("continuity-posture-degraded")
    elif posture_state == "unknown":
        blockers.append("continuity-posture-unknown")
    elif posture_state == "attention":
        warnings.append("continuity-posture-attention")

    if posture_state == "degraded" or schedule_state == "overdue" or topology_state == "stale":
        overall = "degraded"
    elif posture_state == "unknown" or schedule_state == "unknown" or topology_state == "unknown":
        overall = "unknown"
    elif posture_state == "attention" or schedule_state == "due" or topology_state == "attention":
        overall = "attention"
    else:
        overall = "ready"

    return {
        "schemaVersion": "1.0",
        "assuranceId": f"{policy_id}:{_iso(now)}",
        "policyId": policy_id,
        "objectiveId": objective_id,
        "evaluatedAt": _iso(now),
        "state": overall,
        "postureState": posture_state,
        "schedule": {
            "state": schedule_state,
            "lastEvaluatedAt": _iso(last_evaluated),
            "nextDueAt": _iso(next_due),
            "overdueSeconds": overdue_seconds,
        },
        "topologyFreshness": {
            "state": topology_state,
            "observedAt": _iso(topology_observed),
            "expiresAt": _iso(topology_expires),
            "ageSeconds": topology_age,
            "freshnessRemainingSeconds": topology_remaining,
        },
        "blockerCodes": sorted(set(blockers)),
        "warningCodes": sorted(set(warnings)),
        "evidenceRefs": sorted(evidence_refs),
        "evaluationDispatchEligible": schedule_state in {"due", "overdue"},
    }


def build_monitoring_metrics(
    policy: dict[str, Any],
    assurance: dict[str, Any],
    posture: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build bounded GoreeCloud Monitoring metric projections."""
    if policy.get("monitoringEnabled", True) is not True:
        return []

    objective_id = assurance["objectiveId"]
    generated_at = assurance["evaluatedAt"]
    evidence_refs = assurance.get("evidenceRefs", [])
    labels = {"objectiveId": objective_id}

    metrics = [
        {
            "schemaVersion": "1.0",
            "metricId": f"{assurance['assuranceId']}:assurance-state",
            "objectiveId": objective_id,
            "generatedAt": generated_at,
            "metricName": "everkeep.continuity.assurance_state",
            "value": 1,
            "unit": "state",
            "labels": labels | {"state": assurance["state"]},
            "evidenceRefs": evidence_refs,
            "projectionOnly": True,
            "sensitivePayloadsExcluded": True,
        },
        {
            "schemaVersion": "1.0",
            "metricId": f"{assurance['assuranceId']}:evaluation-overdue",
            "objectiveId": objective_id,
            "generatedAt": generated_at,
            "metricName": "everkeep.continuity.evaluation_overdue_seconds",
            "value": assurance["schedule"]["overdueSeconds"],
            "unit": "seconds",
            "labels": labels | {"scheduleState": assurance["schedule"]["state"]},
            "evidenceRefs": evidence_refs,
            "projectionOnly": True,
            "sensitivePayloadsExcluded": True,
        },
        {
            "schemaVersion": "1.0",
            "metricId": f"{assurance['assuranceId']}:failover-eligible",
            "objectiveId": objective_id,
            "generatedAt": generated_at,
            "metricName": "everkeep.continuity.failover_eligible",
            "value": 1 if posture.get("failoverEligible") is True else 0,
            "unit": "boolean",
            "labels": labels | {"postureState": assurance["postureState"]},
            "evidenceRefs": evidence_refs,
            "projectionOnly": True,
            "sensitivePayloadsExcluded": True,
        },
    ]
    if assurance["topologyFreshness"]["ageSeconds"] is not None:
        metrics.append(
            {
                "schemaVersion": "1.0",
                "metricId": f"{assurance['assuranceId']}:topology-age",
                "objectiveId": objective_id,
                "generatedAt": generated_at,
                "metricName": "everkeep.continuity.topology_age_seconds",
                "value": assurance["topologyFreshness"]["ageSeconds"],
                "unit": "seconds",
                "labels": labels | {"topologyState": assurance["topologyFreshness"]["state"]},
                "evidenceRefs": evidence_refs,
                "projectionOnly": True,
                "sensitivePayloadsExcluded": True,
            }
        )
    return metrics


def build_notify_intents(policy: dict[str, Any], assurance: dict[str, Any]) -> list[dict[str, Any]]:
    """Build deduplicated GoreeCloud Notify intents without delivering them."""
    if policy.get("notifyEnabled", True) is not True:
        return []

    objective_id = assurance["objectiveId"]
    generated_at = assurance["evaluatedAt"]
    evidence_refs = assurance.get("evidenceRefs", [])
    intents: list[dict[str, Any]] = []

    def add(category: str, severity: str, title: str, reason: str) -> None:
        intents.append(
            {
                "schemaVersion": "1.0",
                "intentId": f"{assurance['assuranceId']}:{category}",
                "objectiveId": objective_id,
                "generatedAt": generated_at,
                "category": category,
                "severity": severity,
                "title": title,
                "reason": reason,
                "dedupeKey": f"everkeep:{objective_id}:{category}",
                "evidenceRefs": evidence_refs,
                "deliveryAuthority": "goreecloud-notify",
                "projectionOnly": True,
                "deliveryAttempted": False,
                "sensitivePayloadsExcluded": True,
            }
        )

    posture_state = assurance["postureState"]
    if posture_state == "degraded":
        add("continuity-degraded", "high", "Continuity objective degraded", "Current Everkeep continuity evidence is degraded.")
    elif posture_state == "unknown":
        add("continuity-unknown", "medium", "Continuity state unknown", "Required continuity evidence is missing, stale, malformed, or unverified.")
    elif posture_state == "attention":
        add("continuity-attention", "low", "Continuity objective needs attention", "Continuity evidence is approaching a policy threshold.")

    schedule_state = assurance["schedule"]["state"]
    if schedule_state == "overdue":
        add("continuity-evaluation-overdue", "high", "Continuity evaluation overdue", "The policy-defined continuity evaluation deadline has passed.")
    elif schedule_state == "due":
        add("continuity-evaluation-due", "low", "Continuity evaluation due", "A continuity evaluation is due now or has not yet been recorded.")
    elif schedule_state == "unknown":
        add("continuity-evaluation-unknown", "medium", "Continuity evaluation timing unknown", "The last continuity evaluation time cannot be verified.")

    topology_state = assurance["topologyFreshness"]["state"]
    if topology_state == "stale":
        add("recovery-topology-stale", "high", "Recovery topology stale", "Authoritative recovery-topology evidence has exceeded its policy-defined maximum age.")
    elif topology_state == "unknown":
        add("recovery-topology-unknown", "medium", "Recovery topology unknown", "Current authoritative recovery-topology freshness cannot be established.")
    elif topology_state == "attention":
        add("recovery-topology-expiring", "low", "Recovery topology nearing expiry", "Recovery-topology evidence is approaching its policy-defined freshness deadline.")

    return intents
