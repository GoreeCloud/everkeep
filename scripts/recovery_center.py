#!/usr/bin/env python3
"""Deterministic, evidence-bounded Recovery Center projections."""

from collections import Counter
from datetime import datetime, timezone

READINESS_KEYS = {
    "Recovery Ready": "recoveryReady",
    "At Risk": "atRisk",
    "Recovery Blocked": "recoveryBlocked",
    "Unknown": "unknown",
}

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
ASSURANCE_FIELDS = ("integrityCurrent", "restoreTestCurrent", "policyCompliant")


def _action(resource, action, reason, authorized, destructive=False):
    return {
        "action": action,
        "resourceId": resource["resourceId"],
        "reason": reason,
        "authorizedByEvidence": bool(authorized),
        "destructive": bool(destructive),
    }


def _tri_state(value):
    if value is True:
        return "pass"
    if value is False:
        return "fail"
    return "unknown"


def recommended_actions(resource):
    """Return only actions justified by the state supplied by authoritative evidence."""
    actions = []
    protected = resource.get("protected") is True
    blockers = {
        blocker if isinstance(blocker, str) else blocker["code"]
        for blocker in resource.get("blockers", [])
    }

    if not protected:
        actions.append(_action(resource, "protect-resource", "Resource has no effective protection evidence.", True))
    else:
        actions.append(_action(resource, "browse-recovery-points", "Protection evidence confirms recovery-point inventory may be inspected.", True))

    if "integrity-failed" in blockers or "verification-stale" in blockers or resource.get("integrityCurrent") is False:
        actions.append(_action(resource, "verify-integrity", "Integrity evidence is failed or stale.", True))
    if "restore-test-missing" in blockers or "restore-test-stale" in blockers or resource.get("restoreTestCurrent") is False:
        actions.append(_action(resource, "run-restore-test", "Restore-test evidence is missing, failed, or stale.", True))
    if "policy-noncompliant" in blockers or resource.get("policyCompliant") is False:
        actions.append(_action(resource, "inspect-policy", "Protection policy is not currently satisfied.", True))
    if "key-material-unavailable" in blockers:
        actions.append(_action(resource, "inspect-key-readiness", "Required recovery key material is unavailable.", True))
    if "dependency-unavailable" in blockers:
        actions.append(_action(resource, "inspect-dependencies", "A required recovery dependency is unavailable.", True))

    ready = resource.get("readiness") == "Recovery Ready"
    eligible = resource.get("recoveryEligible") is True
    if ready and eligible:
        actions.append(_action(resource, "create-recovery-plan", "Current evidence supports planning a recovery operation.", True))
        actions.append(_action(resource, "run-recovery-sandbox", "Current evidence supports an isolated recovery rehearsal.", True))
        actions.append(_action(resource, "restore-resource", "Current evidence confirms recovery eligibility.", True, destructive=False))

    if protected and resource.get("preservationEligible") is True:
        actions.append(_action(resource, "create-preservation-capsule", "Current evidence confirms the resource may be packaged for preservation.", True))
    if resource.get("exportEligible") is True:
        actions.append(_action(resource, "export-resource", "Current authority evidence permits a portability export.", True))

    return actions


def build_summary(resources, generated_at=None):
    resources = sorted(resources, key=lambda r: r["resourceId"])
    readiness = {value: 0 for value in READINESS_KEYS.values()}
    protection = {"protected": 0, "unprotected": 0}
    assurance = {
        field: {"pass": 0, "fail": 0, "unknown": 0}
        for field in ASSURANCE_FIELDS
    }
    blocker_counts = Counter()
    blocker_severity = {}
    actions = []

    for resource in resources:
        state = resource.get("readiness", "Unknown")
        readiness[READINESS_KEYS.get(state, "unknown")] += 1
        protection["protected" if resource.get("protected") is True else "unprotected"] += 1

        for field in ASSURANCE_FIELDS:
            assurance[field][_tri_state(resource.get(field))] += 1

        for blocker in resource.get("blockers", []):
            code = blocker if isinstance(blocker, str) else blocker["code"]
            severity = "high" if isinstance(blocker, str) else blocker.get("severity", "high")
            if severity not in SEVERITY_ORDER:
                severity = "high"
            blocker_counts[code] += 1
            current = blocker_severity.get(code)
            if current is None or SEVERITY_ORDER[severity] < SEVERITY_ORDER[current]:
                blocker_severity[code] = severity
        actions.extend(recommended_actions(resource))

    priority = [
        {"code": code, "count": count, "severity": blocker_severity[code]}
        for code, count in blocker_counts.items()
    ]
    priority.sort(key=lambda item: (SEVERITY_ORDER[item["severity"]], -item["count"], item["code"]))
    actions.sort(key=lambda item: (item["resourceId"], item["action"]))

    return {
        "schemaVersion": "1.1",
        "generatedAt": generated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "totals": {"resources": len(resources)},
        "readiness": readiness,
        "protection": protection,
        "assurance": assurance,
        "priorityBlockers": priority,
        "recommendedActions": actions,
    }
