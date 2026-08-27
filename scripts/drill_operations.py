#!/usr/bin/env python3
"""Bounded Everkeep disaster-recovery drill operations and rollback assurance.

Phase 3.5 may advance an already accepted Phase 3.4 executor request through a
simulation-only state machine and construct rollback assurance artifacts. This
module never provisions infrastructure, moves data, switches traffic, embeds
credentials, mutates a source system, or authorizes production rollback.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from failover_executor import (
    FailoverExecutorError,
    start_execution,
    transition_execution,
)
from failover_governance import canonical_plan_digest

ROLLBACK_AUTHORITIES = {
    "serviceHealth": "target-runtime",
    "dataIntegrity": "everkeep",
    "dependencies": "everkeep",
    "security": "wardveil-security",
    "privacy": "privacy-shield",
}


class DrillOperationsError(ValueError):
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
        raise DrillOperationsError("time must be an ISO 8601 date-time")
    return parsed


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe(artifact: dict[str, Any]) -> bool:
    return (
        artifact.get("simulationOnly") is True
        and artifact.get("externalEffectsAuthorized") is False
        and artifact.get("sourceMutationAllowed") is False
        and artifact.get("trafficMutationAllowed") is False
        and artifact.get("credentialsEmbedded") is False
    )


def build_drill_dispatch(
    dispatch_id: str,
    execution_id: str,
    request: dict[str, Any],
    plan: dict[str, Any],
    requested_at: str | None = None,
) -> dict[str, Any]:
    """Bind an accepted Phase 3.4 request to one simulation-only drill dispatch."""
    if not dispatch_id or not execution_id:
        raise DrillOperationsError("dispatch_id and execution_id are required")
    if not isinstance(request, dict) or not request.get("requestId"):
        raise DrillOperationsError("executor request is required")
    if not isinstance(plan, dict) or not plan.get("planId") or not plan.get("objectiveId"):
        raise DrillOperationsError("failover plan is required")

    now = _now(requested_at)
    blockers = list(request.get("blockerCodes", []))
    digest = canonical_plan_digest(plan)
    target = plan.get("target") if isinstance(plan.get("target"), dict) else {}

    if request.get("handoffAccepted") is not True:
        blockers.append("drill-dispatch-handoff-not-accepted")
    if not _safe(request):
        blockers.append("drill-dispatch-safety-boundary-invalid")
    if request.get("planId") != plan.get("planId") or request.get("planDigest") != digest:
        blockers.append("drill-dispatch-plan-binding-mismatch")
    if request.get("objectiveId") != plan.get("objectiveId"):
        blockers.append("drill-dispatch-objective-binding-mismatch")
    request_target = request.get("target") if isinstance(request.get("target"), dict) else {}
    if any(request_target.get(key) != target.get(key) for key in ("targetId", "environment", "failureDomain")):
        blockers.append("drill-dispatch-target-binding-mismatch")
    approval_expires = _parse_time(request.get("approvalExpiresAt"))
    if approval_expires is None:
        blockers.append("drill-dispatch-approval-expiry-unknown")
    elif approval_expires <= now:
        blockers.append("drill-dispatch-approval-expired")

    return {
        "schemaVersion": "1.0",
        "dispatchId": dispatch_id,
        "requestId": request["requestId"],
        "executionId": execution_id,
        "planId": plan["planId"],
        "planDigest": digest,
        "objectiveId": plan["objectiveId"],
        "target": {
            "targetId": target.get("targetId", "unknown"),
            "environment": target.get("environment", "unknown"),
            "failureDomain": target.get("failureDomain", "unknown"),
        },
        "expectedRevision": request.get("expectedRevision", "unknown"),
        "state": "accepted" if not blockers else "blocked",
        "requestedAt": _iso(now),
        "blockerCodes": sorted(set(blockers)),
        "evidenceRefs": sorted(set(request.get("evidenceRefs", []))),
        "simulationOnly": True,
        "externalEffectsAuthorized": False,
        "sourceMutationAllowed": False,
        "trafficMutationAllowed": False,
        "credentialsEmbedded": False,
    }


def record_drill_step(
    execution: dict[str, Any],
    step_id: str,
    *,
    evidence_ref: str | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Record one simulated plan step while remaining in the executing state."""
    if execution.get("state") != "executing":
        raise DrillOperationsError("drill steps may be recorded only while executing")
    if not step_id:
        raise DrillOperationsError("step_id is required")
    if not _safe(execution):
        raise DrillOperationsError("executor safety boundary was modified")

    now = _now(observed_at)
    updated = deepcopy(execution)
    completed = list(updated.get("completedStepIds", []))
    if step_id in completed:
        raise DrillOperationsError("duplicate drill step")
    completed.append(step_id)
    updated["completedStepIds"] = completed
    updated["currentStepIndex"] = len(completed)
    if evidence_ref:
        updated["evidenceRefs"] = sorted(set(updated.get("evidenceRefs", [])) | {evidence_ref})
    updated["updatedAt"] = _iso(now)
    return updated


def run_bounded_drill(
    dispatch: dict[str, Any],
    request: dict[str, Any],
    plan: dict[str, Any],
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Advance a dispatch through a no-effect drill lifecycle."""
    now = _now(observed_at)
    if dispatch.get("state") != "accepted" or not _safe(dispatch):
        blocked_request = dict(request) | {"handoffAccepted": False}
        return start_execution(dispatch.get("executionId", "unknown"), blocked_request, _iso(now))
    if dispatch.get("requestId") != request.get("requestId"):
        raise DrillOperationsError("dispatch request binding mismatch")
    if dispatch.get("planDigest") != canonical_plan_digest(plan):
        raise DrillOperationsError("dispatch plan digest mismatch")

    execution = start_execution(dispatch["executionId"], request, _iso(now))
    if execution.get("state") != "pending":
        return execution

    for state in ("validating", "authorized", "staging", "executing"):
        execution = transition_execution(
            execution,
            state,
            evidence_refs=[f"evidence:drill:{dispatch['dispatchId']}:{state}"],
            observed_at=_iso(now),
        )

    for step in plan.get("steps", []):
        step_id = step.get("stepId") if isinstance(step, dict) else None
        if not step_id:
            raise DrillOperationsError("all drill plan steps require stepId")
        execution = record_drill_step(
            execution,
            step_id,
            evidence_ref=f"evidence:drill:{dispatch['dispatchId']}:step:{step_id}",
            observed_at=_iso(now),
        )

    execution = transition_execution(
        execution,
        "verifying",
        evidence_refs=[f"evidence:drill:{dispatch['dispatchId']}:verifying"],
        observed_at=_iso(now),
    )
    return transition_execution(
        execution,
        "completed",
        evidence_refs=[f"evidence:drill:{dispatch['dispatchId']}:completed"],
        observed_at=_iso(now),
    )


def build_rollback_plan(
    rollback_plan_id: str,
    execution: dict[str, Any],
    plan: dict[str, Any],
    created_at: str | None = None,
) -> dict[str, Any]:
    """Construct a reverse-order simulation plan from completed drill steps."""
    if not rollback_plan_id:
        raise DrillOperationsError("rollback_plan_id is required")
    now = _now(created_at)
    digest = canonical_plan_digest(plan)
    blockers: list[str] = []
    if execution.get("state") != "completed":
        blockers.append("rollback-source-execution-not-completed")
    if not _safe(execution):
        blockers.append("rollback-source-safety-boundary-invalid")
    if execution.get("planId") != plan.get("planId") or execution.get("planDigest") != digest:
        blockers.append("rollback-plan-binding-mismatch")
    if execution.get("objectiveId") != plan.get("objectiveId"):
        blockers.append("rollback-objective-binding-mismatch")

    completed = list(execution.get("completedStepIds", []))
    if not completed:
        blockers.append("rollback-completed-steps-unknown")
    steps = [
        {
            "stepId": f"rollback:{index + 1}:{step_id}",
            "reversesStepId": step_id,
            "action": "simulate-rollback-step",
            "externalEffect": False,
        }
        for index, step_id in enumerate(reversed(completed))
    ]
    target = execution.get("target") if isinstance(execution.get("target"), dict) else {}
    state = "ready-for-drill" if not blockers else ("unknown" if blockers == ["rollback-completed-steps-unknown"] else "blocked")

    return {
        "schemaVersion": "1.0",
        "rollbackPlanId": rollback_plan_id,
        "executionId": execution.get("executionId", "unknown"),
        "requestId": execution.get("requestId", "unknown"),
        "planId": plan.get("planId", "unknown"),
        "planDigest": digest,
        "objectiveId": plan.get("objectiveId", "unknown"),
        "target": {
            "targetId": target.get("targetId", "unknown"),
            "environment": target.get("environment", "unknown"),
            "failureDomain": target.get("failureDomain", "unknown"),
        },
        "expectedRevision": execution.get("expectedRevision", "unknown"),
        "state": state,
        "steps": steps,
        "blockerCodes": sorted(set(blockers)),
        "createdAt": _iso(now),
        "evidenceRefs": sorted(set(execution.get("evidenceRefs", []))),
        "requiresApproval": True,
        "executionAuthorized": False,
        "simulationOnly": True,
        "externalEffectsAuthorized": False,
        "sourceMutationAllowed": False,
        "trafficMutationAllowed": False,
        "credentialsEmbedded": False,
    }


def _rollback_check(
    name: str,
    supplied: Any,
    blockers: list[str],
    evidence_refs: set[str],
) -> dict[str, Any]:
    expected = ROLLBACK_AUTHORITIES[name]
    if not isinstance(supplied, dict):
        blockers.append(f"rollback-assurance-{name}-unknown")
        return {"state": "unknown", "authority": expected, "evidenceRef": None, "reason": "rollback evidence unavailable"}
    state = supplied.get("state") if supplied.get("state") in {"pass", "fail", "unknown"} else "unknown"
    authority = supplied.get("authority")
    evidence_ref = supplied.get("evidenceRef")
    reason = supplied.get("reason")
    if authority != expected:
        state = "unknown"
        blockers.append(f"rollback-assurance-{name}-authority-unknown")
    if not evidence_ref:
        state = "unknown"
        blockers.append(f"rollback-assurance-{name}-evidence-unknown")
    else:
        evidence_refs.add(str(evidence_ref))
    if state == "fail":
        blockers.append(f"rollback-assurance-{name}-failed")
    elif state == "unknown":
        blockers.append(f"rollback-assurance-{name}-unknown")
    return {
        "state": state,
        "authority": expected if authority != expected else authority,
        "evidenceRef": evidence_ref if evidence_ref else None,
        "reason": reason if isinstance(reason, str) and reason else None,
    }


def evaluate_rollback_assurance(
    rollback_evidence_id: str,
    rollback_plan: dict[str, Any],
    observed_revision: str,
    checks: dict[str, Any],
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    """Evaluate no-effect rollback rehearsal evidence against exact target revision."""
    if not rollback_evidence_id or not observed_revision:
        raise DrillOperationsError("rollback_evidence_id and observed_revision are required")
    now = _now(evaluated_at)
    blockers: list[str] = []
    evidence_refs = set(rollback_plan.get("evidenceRefs", []))
    target = rollback_plan.get("target") if isinstance(rollback_plan.get("target"), dict) else {}

    if rollback_plan.get("state") != "ready-for-drill":
        blockers.append("rollback-plan-not-ready-for-drill")
    if rollback_plan.get("executionAuthorized") is not False or not _safe(rollback_plan):
        blockers.append("rollback-plan-safety-boundary-invalid")
    expected_revision = rollback_plan.get("expectedRevision")
    exact_revision = bool(expected_revision and expected_revision == observed_revision)
    if not exact_revision:
        blockers.append("rollback-assurance-revision-mismatch")

    normalized = {
        name: _rollback_check(name, checks.get(name), blockers, evidence_refs)
        for name in ROLLBACK_AUTHORITIES
    }
    states = [item["state"] for item in normalized.values()]
    if any(state == "fail" for state in states) or "rollback-assurance-revision-mismatch" in blockers:
        state = "fail"
    elif any(state == "unknown" for state in states) or rollback_plan.get("state") != "ready-for-drill":
        state = "unknown"
    else:
        state = "pass"

    authoritative = state == "pass" and exact_revision
    return {
        "schemaVersion": "1.0",
        "rollbackEvidenceId": rollback_evidence_id,
        "rollbackPlanId": rollback_plan.get("rollbackPlanId", "unknown"),
        "executionId": rollback_plan.get("executionId", "unknown"),
        "planId": rollback_plan.get("planId", "unknown"),
        "planDigest": rollback_plan.get("planDigest", "0" * 64),
        "objectiveId": rollback_plan.get("objectiveId", "unknown"),
        "targetId": target.get("targetId", "unknown"),
        "environment": target.get("environment", "unknown"),
        "expectedRevision": expected_revision or "unknown",
        "observedRevision": observed_revision,
        "evaluatedAt": _iso(now),
        "state": state,
        "authoritative": authoritative,
        "exactRevisionBound": exact_revision,
        "checks": normalized,
        "blockerCodes": sorted(set(blockers)),
        "evidenceRefs": sorted(evidence_refs),
        "simulationOnly": True,
        "externalEffectsObserved": False,
        "productionMutationAuthorized": False,
    }


def rollback_evidence_may_authorize_production_mutation(evidence: dict[str, Any]) -> bool:
    return False
