#!/usr/bin/env python3
"""Controlled, fail-closed Everkeep failover executor reference state machine.

This module accepts only drill-mode handoffs. It revalidates current authority
and exact-plan evidence, records a deterministic execution lifecycle, and never
performs external effects, switches traffic, embeds credentials, or mutates a
source system. Runtime adapters that can produce external effects remain a
separate future deployment boundary.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from failover_governance import canonical_plan_digest

EXECUTOR_GATES = {
    "identity": "goreecloud-identity",
    "privacy": "privacy-shield",
    "wardveil": "wardveil-security",
    "continuity": "everkeep",
    "target": "everkeep",
    "dependencies": "everkeep",
    "keyMaterial": "everkeep",
}

ALLOWED_TRANSITIONS = {
    "pending": {"validating", "cancelled"},
    "validating": {"authorized", "blocked", "cancelled"},
    "authorized": {"staging", "cancelled"},
    "staging": {"executing", "blocked", "failed", "cancelled"},
    "executing": {"verifying", "failed", "cancelled"},
    "verifying": {"completed", "failed", "cancelled"},
    "completed": set(),
    "blocked": set(),
    "failed": set(),
    "cancelled": set(),
}

TERMINAL_STATES = {"completed", "blocked", "failed", "cancelled"}


class FailoverExecutorError(ValueError):
    pass


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


def _now(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    parsed = _parse_time(value)
    if parsed is None:
        raise FailoverExecutorError("time must be an ISO 8601 date-time")
    return parsed


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_gate(name: str, supplied: Any, now: datetime, blockers: list[str], evidence: set[str]) -> dict[str, Any]:
    expected_authority = EXECUTOR_GATES[name]
    if not isinstance(supplied, dict):
        blockers.append(f"executor-{name}-unknown")
        return {
            "state": "unknown",
            "authority": expected_authority,
            "evidenceRef": None,
            "observedAt": None,
            "validUntil": None,
            "reason": "executor gate evidence unavailable",
        }

    state = supplied.get("state") if supplied.get("state") in {"pass", "fail", "unknown"} else "unknown"
    authority = supplied.get("authority")
    evidence_ref = supplied.get("evidenceRef")
    observed_at = _parse_time(supplied.get("observedAt"))
    valid_until = _parse_time(supplied.get("validUntil"))
    reason = supplied.get("reason")

    if authority != expected_authority:
        state = "unknown"
        blockers.append(f"executor-{name}-authority-unknown")
    if not evidence_ref:
        state = "unknown"
        blockers.append(f"executor-{name}-evidence-unknown")
    else:
        evidence.add(str(evidence_ref))
    if observed_at is None or valid_until is None or (observed_at and valid_until and valid_until < observed_at):
        state = "unknown"
        blockers.append(f"executor-{name}-time-unknown")
    elif valid_until <= now:
        state = "unknown"
        blockers.append(f"executor-{name}-expired")

    if state == "fail":
        blockers.append(f"executor-{name}-failed")
    elif state == "unknown":
        blockers.append(f"executor-{name}-unknown")

    return {
        "state": state,
        "authority": expected_authority if authority != expected_authority else authority,
        "evidenceRef": evidence_ref if evidence_ref else None,
        "observedAt": _iso(observed_at) if observed_at else None,
        "validUntil": _iso(valid_until) if valid_until else None,
        "reason": reason if isinstance(reason, str) and reason else None,
    }


def build_executor_request(
    request_id: str,
    plan: dict[str, Any],
    approval: dict[str, Any],
    expected_revision: str,
    gate_evidence: dict[str, Any],
    requested_at: str | None = None,
) -> dict[str, Any]:
    """Build a non-effecting drill handoff after revalidating current authority."""
    if not request_id or not expected_revision:
        raise FailoverExecutorError("request_id and expected_revision are required")
    if not isinstance(plan, dict) or not plan.get("planId") or not plan.get("objectiveId"):
        raise FailoverExecutorError("a failover plan with planId and objectiveId is required")
    if not isinstance(approval, dict) or not approval.get("approvalId"):
        raise FailoverExecutorError("an approval artifact is required")

    now = _now(requested_at)
    digest = canonical_plan_digest(plan)
    blockers: list[str] = []
    evidence = set(approval.get("evidenceRefs", []))
    target = plan.get("target") if isinstance(plan.get("target"), dict) else {}

    approval_expires = _parse_time(approval.get("expiresAt"))
    if approval.get("state") != "approved" or approval.get("handoffEligible") is not True:
        blockers.append("executor-approval-not-eligible")
    if approval.get("executionAuthorized") is not False or approval.get("executionCredential") is not False:
        blockers.append("executor-approval-boundary-invalid")
    if approval.get("sourceMutationAllowed") is not False:
        blockers.append("executor-source-mutation-boundary-invalid")
    if approval.get("planId") != plan.get("planId") or approval.get("planDigest") != digest:
        blockers.append("executor-plan-binding-mismatch")
    if approval.get("objectiveId") != plan.get("objectiveId"):
        blockers.append("executor-objective-binding-mismatch")
    approval_target = approval.get("target") if isinstance(approval.get("target"), dict) else {}
    for key in ("targetId", "environment", "failureDomain"):
        if not target.get(key) or approval_target.get(key) != target.get(key):
            blockers.append("executor-target-binding-mismatch")
            break
    if approval_expires is None:
        blockers.append("executor-approval-expiry-unknown")
    elif approval_expires <= now:
        blockers.append("executor-approval-expired")

    normalized_gates = {
        name: _normalize_gate(name, gate_evidence.get(name), now, blockers, evidence)
        for name in EXECUTOR_GATES
    }
    all_current_pass = all(gate["state"] == "pass" for gate in normalized_gates.values())
    handoff_accepted = not blockers and all_current_pass

    return {
        "schemaVersion": "1.0",
        "requestId": request_id,
        "approvalId": approval["approvalId"],
        "planId": plan["planId"],
        "planDigest": digest,
        "objectiveId": plan["objectiveId"],
        "mode": "drill",
        "target": {
            "targetId": target.get("targetId", "unknown"),
            "environment": target.get("environment", "unknown"),
            "failureDomain": target.get("failureDomain", "unknown"),
        },
        "expectedRevision": expected_revision,
        "requestedAt": _iso(now),
        "approvalExpiresAt": _iso(approval_expires) if approval_expires else _iso(now),
        "gateResults": normalized_gates,
        "blockerCodes": sorted(set(blockers)),
        "evidenceRefs": sorted(evidence),
        "handoffAccepted": handoff_accepted,
        "simulationOnly": True,
        "externalEffectsAuthorized": False,
        "sourceMutationAllowed": False,
        "trafficMutationAllowed": False,
        "credentialsEmbedded": False,
    }


def start_execution(execution_id: str, request: dict[str, Any], started_at: str | None = None) -> dict[str, Any]:
    if not execution_id:
        raise FailoverExecutorError("execution_id is required")
    now = _now(started_at)
    safe_request = (
        request.get("handoffAccepted") is True
        and request.get("simulationOnly") is True
        and request.get("externalEffectsAuthorized") is False
        and request.get("sourceMutationAllowed") is False
        and request.get("trafficMutationAllowed") is False
        and request.get("credentialsEmbedded") is False
    )
    state = "pending" if safe_request else "blocked"
    blockers = list(request.get("blockerCodes", []))
    if not safe_request:
        blockers.append("executor-request-not-safe")

    return {
        "schemaVersion": "1.0",
        "executionId": execution_id,
        "requestId": request.get("requestId", "unknown"),
        "approvalId": request.get("approvalId", "unknown"),
        "planId": request.get("planId", "unknown"),
        "planDigest": request.get("planDigest", "0" * 64),
        "objectiveId": request.get("objectiveId", "unknown"),
        "mode": "drill",
        "target": deepcopy(request.get("target", {"targetId": "unknown", "environment": "unknown", "failureDomain": "unknown"})),
        "expectedRevision": request.get("expectedRevision", "unknown"),
        "state": state,
        "currentStepIndex": 0,
        "completedStepIds": [],
        "blockerCodes": sorted(set(blockers)),
        "evidenceRefs": sorted(set(request.get("evidenceRefs", []))),
        "startedAt": _iso(now),
        "updatedAt": _iso(now),
        "finishedAt": _iso(now) if state == "blocked" else None,
        "simulationOnly": True,
        "externalEffectsAuthorized": False,
        "sourceMutationAllowed": False,
        "trafficMutationAllowed": False,
        "credentialsEmbedded": False,
    }


def transition_execution(
    execution: dict[str, Any],
    next_state: str,
    *,
    step_id: str | None = None,
    evidence_refs: list[str] | None = None,
    blocker_codes: list[str] | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Advance state only; the reference executor performs no external operation."""
    current = execution.get("state")
    if current not in ALLOWED_TRANSITIONS or next_state not in ALLOWED_TRANSITIONS[current]:
        raise FailoverExecutorError(f"invalid executor transition: {current} -> {next_state}")
    if any(execution.get(key) is not expected for key, expected in {
        "simulationOnly": True,
        "externalEffectsAuthorized": False,
        "sourceMutationAllowed": False,
        "trafficMutationAllowed": False,
        "credentialsEmbedded": False,
    }.items()):
        raise FailoverExecutorError("executor safety boundary was modified")

    now = _now(observed_at)
    updated = deepcopy(execution)
    updated["state"] = next_state
    updated["updatedAt"] = _iso(now)
    if step_id:
        completed = list(updated.get("completedStepIds", []))
        if step_id not in completed:
            completed.append(step_id)
            updated["completedStepIds"] = completed
            updated["currentStepIndex"] = int(updated.get("currentStepIndex", 0)) + 1
    updated["evidenceRefs"] = sorted(set(updated.get("evidenceRefs", [])) | set(evidence_refs or []))
    updated["blockerCodes"] = sorted(set(updated.get("blockerCodes", [])) | set(blocker_codes or []))
    updated["finishedAt"] = _iso(now) if next_state in TERMINAL_STATES else None
    return updated


def executor_may_produce_external_effects(execution: dict[str, Any]) -> bool:
    """The Phase 3.4 reference executor never receives external-effect authority."""
    return False
