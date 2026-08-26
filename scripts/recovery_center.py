#!/usr/bin/env python3
from collections import Counter
from datetime import datetime, timezone

READINESS_KEYS = {
    "Recovery Ready": "recoveryReady",
    "At Risk": "atRisk",
    "Recovery Blocked": "recoveryBlocked",
    "Unknown": "unknown",
}

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _action(resource, action, reason, authorized, destructive=False):
    return {
        "action": action,
        "resourceId": resource["resourceId"],
        "reason": reason,
        "authorizedByEvidence": bool(authorized),
        "destructive": bool(destructive),
    }


def recommended_actions(resource):
    actions = []
    if not resource.get("protected", False):
        actions.append(_action(resource, "protect-resource", "Resource has no effective protection evidence.", True))
    blockers = set(resource.get("blockers", []))
    if "integrity-failed" in blockers or "verification-stale" in blockers:
        actions.append(_action(resource, "verify-integrity", "Integrity evidence is failed or stale.", True))
    if "restore-test-missing" in blockers or "restore-test-stale" in blockers:
        actions.append(_action(resource, "run-restore-test", "Restore-test evidence is missing or stale.", True))
    if "policy-noncompliant" in blockers:
        actions.append(_action(resource, "inspect-policy", "Protection policy is not currently satisfied.", True))
    if "key-material-unavailable" in blockers:
        actions.append(_action(resource, "inspect-key-readiness", "Required recovery key material is unavailable.", True))
    if "dependency-unavailable" in blockers:
        actions.append(_action(resource, "inspect-dependencies", "A required recovery dependency is unavailable.", True))

    # Restore is exposed only when evidence explicitly says the resource is eligible
    # and the deterministic readiness state is Recovery Ready.
    if resource.get("readiness") == "Recovery Ready" and resource.get("recoveryEligible") is True:
        actions.append(_action(resource, "restore-resource", "Current evidence confirms recovery eligibility.", True, destructive=False))
    return actions


def build_summary(resources, generated_at=None):
    resources = sorted(resources, key=lambda r: r["resourceId"])
    readiness = {v: 0 for v in READINESS_KEYS.values()}
    protection = {"protected": 0, "unprotected": 0}
    blocker_counts = Counter()
    blocker_severity = {}
    actions = []

    for resource in resources:
        state = resource.get("readiness", "Unknown")
        readiness[READINESS_KEYS.get(state, "unknown")] += 1
        protection["protected" if resource.get("protected", False) else "unprotected"] += 1
        for blocker in resource.get("blockers", []):
            code = blocker if isinstance(blocker, str) else blocker["code"]
            severity = "high" if isinstance(blocker, str) else blocker.get("severity", "high")
            blocker_counts[code] += 1
            current = blocker_severity.get(code)
            if current is None or SEVERITY_ORDER[severity] < SEVERITY_ORDER[current]:
                blocker_severity[code] = severity
        actions.extend(recommended_actions(resource))

    priority = [
        {"code": code, "count": count, "severity": blocker_severity[code]}
        for code, count in blocker_counts.items()
    ]
    priority.sort(key=lambda x: (SEVERITY_ORDER[x["severity"]], -x["count"], x["code"]))
    actions.sort(key=lambda a: (a["resourceId"], a["action"]))

    return {
        "schemaVersion": "1.0",
        "generatedAt": generated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "totals": {"resources": len(resources)},
        "readiness": readiness,
        "protection": protection,
        "priorityBlockers": priority,
        "recommendedActions": actions,
    }
