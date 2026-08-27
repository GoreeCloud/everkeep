#!/usr/bin/env python3
"""Deterministic Everkeep recovery planning and fail-closed execution gating.

This module plans recovery work and evaluates authorization evidence. It does
not perform a restore, mutate source data, or claim that any runtime recovery
infrastructure exists.
"""

from __future__ import annotations

from datetime import datetime, timezone

REQUIRED_GATES = (
    "identity-authorized",
    "privacy-authorized",
    "wardveil-clear",
    "recovery-evidence-current",
    "recovery-point-eligible",
    "dependencies-ready",
    "key-material-ready",
)

GATE_FIELDS = {
    "identity-authorized": "identity",
    "privacy-authorized": "privacy",
    "wardveil-clear": "wardveil",
    "recovery-evidence-current": "evidence",
    "recovery-point-eligible": "recoveryPoint",
    "dependencies-ready": "dependencies",
    "key-material-ready": "keyMaterial",
}

VALID_MODES = {"dry-run", "sandbox", "restore"}


class RecoveryPlanError(ValueError):
    pass


def _utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _dependencies(resource):
    return sorted({
        relation["resourceId"]
        for relation in resource.get("relationships", [])
        if relation.get("type") == "dependency" and relation.get("resourceId")
    })


def _ordered_scope(target_resource_ids, resources):
    """Return dependencies before dependents with stable ordering."""
    visiting = set()
    visited = set()
    ordered = []

    def visit(resource_id):
        if resource_id in visited:
            return
        if resource_id in visiting:
            raise RecoveryPlanError(f"dependency cycle detected at {resource_id}")
        resource = resources.get(resource_id)
        if resource is None:
            raise RecoveryPlanError(f"missing resource metadata for {resource_id}")
        visiting.add(resource_id)
        for dependency_id in _dependencies(resource):
            visit(dependency_id)
        visiting.remove(resource_id)
        visited.add(resource_id)
        ordered.append(resource_id)

    for resource_id in sorted(set(target_resource_ids)):
        visit(resource_id)
    return ordered


def build_plan(
    plan_id,
    target_resource_ids,
    resources,
    mode="sandbox",
    created_at=None,
    requested_recovery_points=None,
):
    if mode not in VALID_MODES:
        raise RecoveryPlanError(f"unsupported recovery mode: {mode}")
    targets = sorted(set(target_resource_ids))
    if not targets:
        raise RecoveryPlanError("at least one target resource is required")

    scope = _ordered_scope(targets, resources)
    target_mode = {"dry-run": "none", "sandbox": "isolated", "restore": "production"}[mode]
    steps = []
    verify_step_by_resource = {}
    order = 1

    for resource_id in scope:
        dependency_verifications = [verify_step_by_resource[dep] for dep in _dependencies(resources[resource_id])]
        validate_id = f"{resource_id}:validate"
        stage_id = f"{resource_id}:stage"
        restore_id = f"{resource_id}:restore"
        verify_id = f"{resource_id}:verify"

        steps.extend([
            {
                "stepId": validate_id,
                "order": order,
                "resourceId": resource_id,
                "operation": "validate",
                "dependsOn": dependency_verifications,
                "targetMode": "none",
            },
            {
                "stepId": stage_id,
                "order": order + 1,
                "resourceId": resource_id,
                "operation": "stage",
                "dependsOn": [validate_id],
                "targetMode": target_mode,
            },
            {
                "stepId": restore_id,
                "order": order + 2,
                "resourceId": resource_id,
                "operation": "restore",
                "dependsOn": [stage_id],
                "targetMode": target_mode,
            },
            {
                "stepId": verify_id,
                "order": order + 3,
                "resourceId": resource_id,
                "operation": "verify",
                "dependsOn": [restore_id],
                "targetMode": target_mode,
            },
        ])
        verify_step_by_resource[resource_id] = verify_id
        order += 4

    return {
        "schemaVersion": "1.0",
        "planId": plan_id,
        "createdAt": created_at or _utc_now(),
        "mode": mode,
        "targetResourceIds": targets,
        "requestedRecoveryPointIds": dict(sorted((requested_recovery_points or {}).items())),
        "steps": steps,
        "requiredGates": list(REQUIRED_GATES),
        "sourceMutationAllowed": False,
        "promotionRequired": mode == "sandbox",
    }


def evaluate_execution(plan, gate_evidence, execution_id, environment):
    """Evaluate authoritative gate evidence; missing/unknown evidence blocks execution."""
    results = {}
    blockers = []
    evidence_refs = set()

    for gate_name in plan.get("requiredGates", REQUIRED_GATES):
        field = GATE_FIELDS[gate_name]
        supplied = gate_evidence.get(gate_name) or {}
        state = supplied.get("state", "unknown")
        if state not in {"pass", "fail", "unknown"}:
            state = "unknown"
        evidence_ref = supplied.get("evidenceRef")
        reason = supplied.get("reason")
        results[field] = {
            "state": state,
            "evidenceRef": evidence_ref,
            "reason": reason,
        }
        if evidence_ref:
            evidence_refs.add(evidence_ref)
        if state != "pass":
            blockers.append(f"gate:{gate_name}:{state}")

    authorized = not blockers and plan.get("sourceMutationAllowed") is False
    return {
        "schemaVersion": "1.0",
        "executionId": execution_id,
        "planId": plan["planId"],
        "state": "authorized" if authorized else "blocked",
        "environment": environment,
        "authorized": authorized,
        "sourceMutationAllowed": False,
        "gateResults": results,
        "evidenceRefs": sorted(evidence_refs),
        "blockerCodes": sorted(blockers),
        "startedAt": None,
        "finishedAt": None,
    }


def execution_may_start(execution):
    return (
        execution.get("authorized") is True
        and execution.get("state") == "authorized"
        and execution.get("sourceMutationAllowed") is False
        and not execution.get("blockerCodes")
    )
