#!/usr/bin/env python3
"""Read-only Recovery Center detail projection for failover executor lifecycle.

This projection complements the Phase 3.5 failover-operations summary without
changing Recovery Center 1.5 or authorizing an effecting failover operation.
"""

from __future__ import annotations

from datetime import datetime, timezone

ACTIVE_STATES = {"pending", "validating", "authorized", "staging", "executing", "verifying"}
TERMINAL_STATES = {"completed", "blocked", "failed", "cancelled"}
KNOWN_STATES = ACTIVE_STATES | TERMINAL_STATES
ASSURANCE_STATES = {"pass", "fail", "unknown"}


def _action(resource, action, reason):
    return {
        "action": action,
        "resourceId": resource["resourceId"],
        "reason": reason,
        "authorizedByEvidence": True,
        "destructive": False,
    }


def _assurance_state(value, applicable):
    if not applicable:
        return "not-applicable"
    return value if value in ASSURANCE_STATES else "unknown"


def build_failover_lifecycle_projection(resources, generated_at=None):
    """Project executor lifecycle without converting lifecycle into recovery truth."""
    resources = sorted(resources, key=lambda item: item["resourceId"])
    executions = []
    actions = []
    acceptance = {state: 0 for state in ("pass", "fail", "unknown", "not-applicable")}

    for resource in resources:
        execution_id = str(resource.get("failoverExecutionId") or "").strip()
        if not execution_id:
            continue

        raw_state = resource.get("failoverExecutorState")
        state = raw_state if raw_state in KNOWN_STATES else "unknown"
        if state in ACTIVE_STATES:
            phase = "active"
        elif state in TERMINAL_STATES:
            phase = "terminal"
        else:
            phase = "unknown"

        completed = state == "completed"
        rollback_state = _assurance_state(resource.get("rollbackEvidenceState"), completed)
        acceptance_state = _assurance_state(resource.get("failoverAcceptanceState"), completed)
        acceptance[acceptance_state] += 1

        refresh_required = state == "unknown" or (
            completed and (rollback_state == "unknown" or acceptance_state == "unknown")
        )

        executions.append(
            {
                "resourceId": resource["resourceId"],
                "executionId": execution_id,
                "state": state,
                "phase": phase,
                "updatedAt": resource.get("failoverExecutionUpdatedAt"),
                "rollbackState": rollback_state,
                "acceptanceState": acceptance_state,
                "refreshRequired": refresh_required,
                "simulationOnly": True,
                "externalEffectsAuthorized": False,
            }
        )

        if state in ACTIVE_STATES or state in {"cancelled", "unknown"}:
            actions.append(_action(
                resource,
                "inspect-failover-drill",
                "Failover executor lifecycle evidence may be inspected without granting production-effect authority.",
            ))
        elif state in {"blocked", "failed"}:
            actions.append(_action(
                resource,
                "inspect-failover-drill-blocker",
                "Failover executor evidence is blocked or failed and requires review before another drill attempt.",
            ))

        if completed and rollback_state != "pass":
            actions.append(_action(
                resource,
                "review-rollback-assurance",
                "A completed drill requires passing exact-revision rollback assurance evidence.",
            ))
        if completed and acceptance_state != "pass":
            actions.append(_action(
                resource,
                "evaluate-failover-acceptance",
                "A completed drill requires separate environment- and revision-bound acceptance evidence.",
            ))

    executions.sort(key=lambda item: (item["resourceId"], item["executionId"]))
    actions.sort(key=lambda item: (item["resourceId"], item["action"]))
    return {
        "schemaVersion": "1.0",
        "generatedAt": generated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "totals": {"resources": len(resources), "executions": len(executions)},
        "acceptance": acceptance,
        "executions": executions,
        "recommendedActions": actions,
    }
