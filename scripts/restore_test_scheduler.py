#!/usr/bin/env python3
"""Policy-derived restore-test scheduling and fail-closed dispatch eligibility."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

BASE_GATES = ("identity-authorized", "privacy-authorized", "wardveil-clear", "recovery-point-eligible")


class RestoreTestScheduleError(ValueError):
    pass


def _parse(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _fmt(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_schedule(schedule_id, resource, policy, evidence, gate_evidence, evaluated_at=None):
    verification = policy.get("verification") or {}
    interval = verification.get("restoreTestIntervalSeconds")
    if policy.get("enabled") is not True or not isinstance(interval, int) or interval < 60:
        raise RestoreTestScheduleError("enabled policy with restoreTestIntervalSeconds >= 60 required")
    resource_id = resource.get("resourceId")
    policy_id = policy.get("policyId")
    if not resource_id or not policy_id:
        raise RestoreTestScheduleError("resourceId and policyId are required")

    now = _parse(evaluated_at) if evaluated_at else datetime.now(timezone.utc)
    last_success_text = evidence.get("lastSuccessfulRestoreTestAt")
    anchor_text = last_success_text or resource.get("createdAt")
    if anchor_text:
        anchor = _parse(anchor_text)
        next_due = anchor + timedelta(seconds=interval)
        overdue_at = next_due + timedelta(seconds=interval)
        if now < next_due:
            temporal_state = "scheduled"
        elif now < overdue_at:
            temporal_state = "due"
        else:
            temporal_state = "overdue"
        next_due_text = _fmt(next_due)
    else:
        temporal_state = "unknown"
        next_due_text = None

    required_gates = list(BASE_GATES)
    requires_sandbox = verification.get("requireRecoverySandbox") is True
    if requires_sandbox:
        required_gates.append("sandbox-available")

    blockers = []
    evidence_refs = set()
    saw_unknown = False
    saw_fail = False
    for gate in required_gates:
        supplied = gate_evidence.get(gate) or {}
        state = supplied.get("state", "unknown")
        if state not in {"pass", "fail", "unknown"}:
            state = "unknown"
        evidence_ref = supplied.get("evidenceRef")
        if evidence_ref:
            evidence_refs.add(evidence_ref)
        if state == "fail":
            saw_fail = True
            blockers.append(f"gate:{gate}:fail")
        elif state != "pass":
            saw_unknown = True
            blockers.append(f"gate:{gate}:unknown")

    if saw_fail:
        dispatch_state = "blocked"
    elif saw_unknown:
        dispatch_state = "unknown"
    else:
        dispatch_state = "ready"

    dispatchable = temporal_state in {"due", "overdue"} and dispatch_state == "ready"
    return {
        "schemaVersion": "1.0",
        "scheduleId": schedule_id,
        "resourceId": resource_id,
        "policyId": policy_id,
        "evaluatedAt": _fmt(now),
        "intervalSeconds": interval,
        "lastSuccessfulTestAt": last_success_text,
        "nextDueAt": next_due_text,
        "temporalState": temporal_state,
        "dispatchState": dispatch_state,
        "dispatchable": dispatchable,
        "requiresSandbox": requires_sandbox,
        "sourceMutationAllowed": False,
        "blockers": sorted(blockers),
        "evidenceRefs": sorted(evidence_refs),
    }
