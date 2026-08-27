#!/usr/bin/env python3
"""Recovery Center projection for controlled failover drill and rollback state."""

from __future__ import annotations

from datetime import datetime, timezone

EXECUTOR_STATES = (
    "pending", "validating", "authorized", "staging", "executing", "verifying",
    "completed", "blocked", "failed", "cancelled", "not-applicable",
)
ROLLBACK_STATES = ("pass", "fail", "unknown", "not-applicable")
ACTIVE_STATES = {"pending", "validating", "authorized", "staging", "executing", "verifying"}


def _action(resource, action, reason):
    return {
        "action": action,
        "resourceId": resource["resourceId"],
        "reason": reason,
        "authorizedByEvidence": True,
        "destructive": False,
    }


def build_failover_operations_projection(resources, generated_at=None):
    resources = sorted(resources, key=lambda item: item["resourceId"])
    executor = {state: 0 for state in EXECUTOR_STATES}
    rollback = {state: 0 for state in ROLLBACK_STATES}
    active = []
    actions = []

    for resource in resources:
        state = resource.get("failoverExecutorState")
        if state not in EXECUTOR_STATES or state == "not-applicable":
            state = "not-applicable" if not resource.get("failoverExecutionId") else "blocked"
        executor[state] += 1

        if state in ACTIVE_STATES:
            active.append(
                {
                    "resourceId": resource["resourceId"],
                    "executionId": resource.get("failoverExecutionId", "unknown"),
                    "state": state,
                    "updatedAt": resource.get("failoverExecutionUpdatedAt"),
                }
            )
            actions.append(_action(resource, "inspect-failover-drill", "A controlled failover drill is currently active and may be inspected without granting production-effect authority."))
        elif state in {"blocked", "failed"}:
            actions.append(_action(resource, "inspect-failover-drill-blocker", "The controlled failover drill is blocked or failed and requires evidence review before another drill attempt."))

        if state == "completed":
            rollback_state = resource.get("rollbackEvidenceState", "unknown")
            if rollback_state not in {"pass", "fail", "unknown"}:
                rollback_state = "unknown"
            if rollback_state != "pass":
                actions.append(_action(resource, "review-rollback-assurance", "A completed drill requires passing exact-revision rollback assurance evidence."))
        else:
            rollback_state = "not-applicable"
        rollback[rollback_state] += 1

    active.sort(key=lambda item: (item["resourceId"], item["executionId"]))
    actions.sort(key=lambda item: (item["resourceId"], item["action"]))
    return {
        "schemaVersion": "1.0",
        "generatedAt": generated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "totals": {"resources": len(resources)},
        "executor": executor,
        "rollback": rollback,
        "activeDrills": active,
        "recommendedActions": actions,
    }
