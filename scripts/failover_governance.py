#!/usr/bin/env python3
"""Fail-closed Everkeep failover approval and acceptance governance.

This module binds approval evidence to the exact contents of a non-executable
failover plan and evaluates environment/revision-bound acceptance evidence after
a separate recovery executor reports completion. Approval may make an executor
handoff eligible, but neither an approval nor acceptance artifact grants runtime
execution, traffic switching, or production mutation authority.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

APPROVAL_GATES = {
    "operator": ("operator-approval", "operator"),
    "identity": ("identity-authorized", "goreecloud-identity"),
    "privacy": ("privacy-authorized", "privacy-shield"),
    "wardveil": ("wardveil-clear", "wardveil-security"),
    "continuity": ("continuity-evidence-current", "everkeep"),
    "target": ("target-ready", "everkeep"),
    "dependencies": ("dependencies-ready", "everkeep"),
    "keyMaterial": ("key-material-ready", "everkeep"),
}

ACCEPTANCE_AUTHORITIES = {
    "serviceHealth": "target-runtime",
    "dataIntegrity": "everkeep",
    "dependencies": "everkeep",
    "security": "wardveil-security",
    "privacy": "privacy-shield",
    "rollback": "everkeep",
}


class FailoverGovernanceError(ValueError):
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


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _now(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    parsed = _parse_time(value)
    if parsed is None:
        raise FailoverGovernanceError("evaluated/observed time must be an ISO 8601 date-time")
    return parsed


def canonical_plan_digest(plan: dict[str, Any]) -> str:
    """Return a stable digest binding governance artifacts to exact plan content."""
    encoded = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _approval_gate(
    name: str,
    supplied: Any,
    now: datetime,
    blockers: list[str],
    evidence_refs: set[str],
) -> tuple[dict[str, Any], bool]:
    _, expected_authority = APPROVAL_GATES[name]
    if not isinstance(supplied, dict):
        blockers.append(f"failover-approval-{name}-unknown")
        return {
            "state": "unknown",
            "authority": expected_authority,
            "evidenceRef": None,
            "observedAt": None,
            "validUntil": None,
            "reason": "approval evidence unavailable",
        }, False

    state = supplied.get("state")
    authority = supplied.get("authority")
    evidence_ref = supplied.get("evidenceRef")
    observed_at = _parse_time(supplied.get("observedAt"))
    valid_until = _parse_time(supplied.get("validUntil"))
    reason = supplied.get("reason")
    normalized_state = state if state in {"pass", "fail", "unknown"} else "unknown"

    if authority != expected_authority:
        normalized_state = "unknown"
        blockers.append(f"failover-approval-{name}-authority-unknown")
    if not evidence_ref:
        normalized_state = "unknown"
        blockers.append(f"failover-approval-{name}-evidence-unknown")
    else:
        evidence_refs.add(str(evidence_ref))
    if observed_at is None or valid_until is None or (observed_at and valid_until and valid_until < observed_at):
        normalized_state = "unknown"
        blockers.append(f"failover-approval-{name}-time-unknown")

    expired = valid_until is not None and valid_until <= now
    if normalized_state == "fail":
        blockers.append(f"failover-approval-{name}-denied")
    elif normalized_state == "unknown":
        blockers.append(f"failover-approval-{name}-unknown")
    elif expired:
        blockers.append(f"failover-approval-{name}-expired")

    return {
        "state": normalized_state,
        "authority": expected_authority if authority != expected_authority else authority,
        "evidenceRef": evidence_ref if evidence_ref else None,
        "observedAt": _iso(observed_at),
        "validUntil": _iso(valid_until),
        "reason": reason if isinstance(reason, str) and reason else None,
    }, expired


def evaluate_failover_approval(
    approval_id: str,
    plan: dict[str, Any],
    gate_evidence: dict[str, Any],
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    """Evaluate approval evidence without creating an execution credential."""
    if not approval_id:
        raise FailoverGovernanceError("approval_id is required")
    if not isinstance(plan, dict) or not plan.get("planId") or not plan.get("objectiveId"):
        raise FailoverGovernanceError("a failover plan with planId and objectiveId is required")

    now = _now(evaluated_at)
    blockers: list[str] = []
    evidence_refs = set(plan.get("evidenceRefs", []))
    target = plan.get("target") if isinstance(plan.get("target"), dict) else None

    plan_state = plan.get("state")
    if plan_state == "blocked":
        blockers.append("failover-plan-blocked")
    elif plan_state != "ready-for-approval":
        blockers.append("failover-plan-not-ready-for-approval")
    if plan.get("executionAuthorized") is not False:
        blockers.append("failover-plan-execution-boundary-invalid")
    if plan.get("sourceMutationAllowed") is not False:
        blockers.append("failover-plan-source-mutation-boundary-invalid")
    if target is None or not all(target.get(key) for key in ("targetId", "environment", "failureDomain")):
        blockers.append("failover-plan-target-unknown")

    normalized_gates: dict[str, Any] = {}
    expired_gate = False
    expirations: list[datetime] = []
    for name in APPROVAL_GATES:
        normalized, expired = _approval_gate(name, gate_evidence.get(name), now, blockers, evidence_refs)
        normalized_gates[name] = normalized
        expired_gate = expired_gate or expired
        valid_until = _parse_time(normalized.get("validUntil"))
        if valid_until is not None:
            expirations.append(valid_until)

    gate_states = [gate["state"] for gate in normalized_gates.values()]
    explicit_denial = plan_state == "blocked" or any(state == "fail" for state in gate_states)
    structural_unknown = (
        plan_state not in {"ready-for-approval", "blocked"}
        or target is None
        or plan.get("executionAuthorized") is not False
        or plan.get("sourceMutationAllowed") is not False
    )

    if explicit_denial:
        state = "denied"
    elif structural_unknown or any(state == "unknown" for state in gate_states):
        state = "unknown"
    elif expired_gate:
        state = "expired"
    else:
        state = "approved"

    expires_at = min(expirations) if expirations else None
    target_projection = {
        "targetId": target.get("targetId", "unknown") if target else "unknown",
        "environment": target.get("environment", "unknown") if target else "unknown",
        "failureDomain": target.get("failureDomain", "unknown") if target else "unknown",
    }
    return {
        "schemaVersion": "1.0",
        "approvalId": approval_id,
        "planId": plan["planId"],
        "planDigest": canonical_plan_digest(plan),
        "objectiveId": plan["objectiveId"],
        "target": target_projection,
        "evaluatedAt": _iso(now),
        "expiresAt": _iso(expires_at),
        "state": state,
        "gateResults": normalized_gates,
        "blockerCodes": sorted(set(blockers)),
        "evidenceRefs": sorted(evidence_refs),
        "handoffEligible": state == "approved",
        "executionAuthorized": False,
        "executionCredential": False,
        "sourceMutationAllowed": False,
    }


def approval_may_execute(approval: dict[str, Any]) -> bool:
    """Approval is never an execution credential."""
    return False


def _acceptance_check(
    name: str,
    supplied: Any,
    blockers: list[str],
    evidence_refs: set[str],
) -> dict[str, Any]:
    expected_authority = ACCEPTANCE_AUTHORITIES[name]
    if not isinstance(supplied, dict):
        blockers.append(f"failover-acceptance-{name}-unknown")
        return {
            "state": "unknown",
            "authority": expected_authority,
            "evidenceRef": None,
            "reason": "acceptance evidence unavailable",
        }

    state = supplied.get("state")
    authority = supplied.get("authority")
    evidence_ref = supplied.get("evidenceRef")
    reason = supplied.get("reason")
    normalized_state = state if state in {"pass", "fail", "unknown"} else "unknown"
    if authority != expected_authority:
        normalized_state = "unknown"
        blockers.append(f"failover-acceptance-{name}-authority-unknown")
    if not evidence_ref:
        normalized_state = "unknown"
        blockers.append(f"failover-acceptance-{name}-evidence-unknown")
    else:
        evidence_refs.add(str(evidence_ref))
    if normalized_state == "fail":
        blockers.append(f"failover-acceptance-{name}-failed")
    elif normalized_state == "unknown":
        blockers.append(f"failover-acceptance-{name}-unknown")

    return {
        "state": normalized_state,
        "authority": expected_authority if authority != expected_authority else authority,
        "evidenceRef": evidence_ref if evidence_ref else None,
        "reason": reason if isinstance(reason, str) and reason else None,
    }


def evaluate_failover_acceptance(
    acceptance_id: str,
    plan: dict[str, Any],
    execution: dict[str, Any],
    expected_revision: str,
    observed_revision: str,
    check_evidence: dict[str, Any],
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Evaluate exact-environment/revision acceptance after separate execution."""
    if not acceptance_id:
        raise FailoverGovernanceError("acceptance_id is required")
    if not expected_revision or not observed_revision:
        raise FailoverGovernanceError("expected_revision and observed_revision are required")
    if not isinstance(plan, dict) or not plan.get("planId") or not plan.get("objectiveId"):
        raise FailoverGovernanceError("a failover plan with planId and objectiveId is required")
    if not isinstance(execution, dict) or not execution.get("executionId"):
        raise FailoverGovernanceError("a recovery execution record with executionId is required")

    now = _now(observed_at)
    blockers: list[str] = []
    evidence_refs = set(plan.get("evidenceRefs", []))
    evidence_refs.update(execution.get("evidenceRefs", []))
    target = plan.get("target") if isinstance(plan.get("target"), dict) else None
    target_id = target.get("targetId") if target else None
    target_environment = target.get("environment") if target else None

    if execution.get("planId") != plan.get("planId"):
        blockers.append("failover-acceptance-plan-mismatch")
    if execution.get("state") != "completed":
        blockers.append("failover-execution-not-completed")
    if execution.get("authorized") is not True:
        blockers.append("failover-execution-authorization-unproven")
    if execution.get("sourceMutationAllowed") is not False:
        blockers.append("failover-execution-source-mutation-boundary-invalid")
    if not target_id or not target_environment:
        blockers.append("failover-acceptance-target-unknown")
    elif execution.get("environment") != target_environment:
        blockers.append("failover-acceptance-environment-mismatch")

    exact_revision = expected_revision == observed_revision
    if not exact_revision:
        blockers.append("failover-acceptance-revision-mismatch")

    normalized_checks: dict[str, Any] = {}
    for name in ACCEPTANCE_AUTHORITIES:
        normalized_checks[name] = _acceptance_check(name, check_evidence.get(name), blockers, evidence_refs)

    check_states = [item["state"] for item in normalized_checks.values()]
    binding_failures = {
        "failover-acceptance-plan-mismatch",
        "failover-execution-not-completed",
        "failover-execution-authorization-unproven",
        "failover-execution-source-mutation-boundary-invalid",
        "failover-acceptance-target-unknown",
        "failover-acceptance-environment-mismatch",
        "failover-acceptance-revision-mismatch",
    }
    has_binding_failure = any(code in binding_failures for code in blockers)

    if has_binding_failure or any(state == "fail" for state in check_states):
        state = "fail"
    elif any(state == "unknown" for state in check_states):
        state = "unknown"
    else:
        state = "pass"

    authoritative = state == "pass"
    return {
        "schemaVersion": "1.0",
        "acceptanceId": acceptance_id,
        "planId": plan["planId"],
        "planDigest": canonical_plan_digest(plan),
        "executionId": execution["executionId"],
        "objectiveId": plan["objectiveId"],
        "targetId": target_id or "unknown",
        "environment": target_environment or str(execution.get("environment") or "unknown"),
        "expectedRevision": expected_revision,
        "observedRevision": observed_revision,
        "observedAt": _iso(now),
        "state": state,
        "authoritative": authoritative,
        "checks": normalized_checks,
        "blockerCodes": sorted(set(blockers)),
        "evidenceRefs": sorted(evidence_refs),
        "exactRevisionBound": exact_revision,
        "productionMutationAuthorized": False,
    }


def acceptance_may_authorize_mutation(acceptance: dict[str, Any]) -> bool:
    """Acceptance records evidence; they never authorize production mutation."""
    return False
