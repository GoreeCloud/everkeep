#!/usr/bin/env python3
"""Evidence-bounded failure analysis and non-executable failover planning.

This module turns authoritative recovery-topology evidence plus a simulated
failure scenario into a deterministic impact projection and, when all required
continuity evidence is ready, a failover plan that is still pending approval.
It never executes failover, changes traffic, mutates production data, or grants
runtime authorization.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

DEPENDENCY_RELATIONSHIPS = {"depends-on", "uses", "hosted-in", "routes-through"}
RECOVERABLE_NODE_TYPES = {
    "service",
    "data-store",
    "storage",
    "compute",
    "network",
    "dns",
    "identity",
    "key-material",
}
APPROVAL_GATES = (
    "operator-approval",
    "identity-authorized",
    "privacy-authorized",
    "wardveil-clear",
    "continuity-evidence-current",
    "target-ready",
    "dependencies-ready",
    "key-material-ready",
)


class ContinuityPlanningError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _nodes(topology: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for node in topology.get("nodes", []):
        node_id = node.get("nodeId")
        if not node_id:
            raise ContinuityPlanningError("every topology node requires nodeId")
        if node_id in result:
            raise ContinuityPlanningError(f"duplicate topology node: {node_id}")
        result[node_id] = node
    return result


def analyze_failure(topology: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    """Project direct and transitive impact without probing or mutating systems."""
    node_map = _nodes(topology)
    blockers = []
    evidence_refs = set(topology.get("evidenceRefs", []))

    if topology.get("authoritative") is not True:
        blockers.append("recovery-topology-not-authoritative")

    direct = set()
    unknown_node_ids = []
    for node_id in scenario.get("affectedNodeIds", []):
        if node_id in node_map:
            direct.add(node_id)
        else:
            unknown_node_ids.append(node_id)

    affected_domains = {
        str(value).strip()
        for value in scenario.get("affectedFailureDomains", [])
        if str(value).strip()
    }
    for node_id, node in node_map.items():
        if node.get("failureDomain") in affected_domains:
            direct.add(node_id)

    if unknown_node_ids:
        blockers.append("failure-scenario-node-unknown")
    if not direct:
        blockers.append("failure-scenario-has-no-evidenced-impact")

    impacted = set(direct)
    changed = True
    while changed:
        changed = False
        for edge in topology.get("edges", []):
            if edge.get("relationship") not in DEPENDENCY_RELATIONSHIPS:
                continue
            source = edge.get("sourceNodeId")
            target = edge.get("targetNodeId")
            if source not in node_map or target not in node_map:
                blockers.append("recovery-topology-edge-node-unknown")
                continue
            if target in impacted and source not in impacted:
                impacted.add(source)
                changed = True

    transitive = impacted - direct
    recovery_nodes = {
        node_id
        for node_id in impacted
        if node_map[node_id].get("nodeType") in RECOVERABLE_NODE_TYPES
    }
    for node_id in impacted:
        ref = node_map[node_id].get("evidenceRef")
        if ref:
            evidence_refs.add(ref)

    return {
        "state": "unknown" if blockers else "analyzed",
        "directlyAffectedNodeIds": sorted(direct),
        "transitivelyAffectedNodeIds": sorted(transitive),
        "affectedNodeIds": sorted(impacted),
        "recoveryNodeIds": sorted(recovery_nodes),
        "affectedFailureDomains": sorted(affected_domains),
        "unknownNodeIds": sorted(unknown_node_ids),
        "blockerCodes": sorted(set(blockers)),
        "evidenceRefs": sorted(evidence_refs),
    }


def _recovery_order(topology: dict[str, Any], recovery_node_ids: set[str]) -> list[str]:
    """Return dependencies before dependents for the impacted recovery scope."""
    dependencies = {node_id: set() for node_id in recovery_node_ids}
    for edge in topology.get("edges", []):
        if edge.get("relationship") not in DEPENDENCY_RELATIONSHIPS:
            continue
        source = edge.get("sourceNodeId")
        target = edge.get("targetNodeId")
        if source in recovery_node_ids and target in recovery_node_ids:
            dependencies[source].add(target)

    visiting = set()
    visited = set()
    ordered = []

    def visit(node_id: str):
        if node_id in visited:
            return
        if node_id in visiting:
            raise ContinuityPlanningError(f"dependency cycle detected at {node_id}")
        visiting.add(node_id)
        for dependency in sorted(dependencies[node_id]):
            visit(dependency)
        visiting.remove(node_id)
        visited.add(node_id)
        ordered.append(node_id)

    for node_id in sorted(recovery_node_ids):
        visit(node_id)
    return ordered


def _select_target(topology: dict[str, Any], impact: dict[str, Any]):
    required = set(impact["recoveryNodeIds"])
    failed_domains = set(impact["affectedFailureDomains"])
    candidates = []
    for target in topology.get("recoveryTargets", []):
        if target.get("state") != "ready" or not target.get("evidenceRef"):
            continue
        if target.get("failureDomain") in failed_domains:
            continue
        supported = set(target.get("supportsNodeIds", []))
        if not required.issubset(supported):
            continue
        candidates.append(target)
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item["targetId"])[0]


def build_failover_plan(
    plan_id: str,
    objective: dict[str, Any],
    posture: dict[str, Any],
    topology: dict[str, Any],
    scenario: dict[str, Any],
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic plan artifact that still requires separate approval."""
    if not plan_id:
        raise ContinuityPlanningError("plan_id is required")
    objective_id = objective.get("objectiveId")
    if not objective_id:
        raise ContinuityPlanningError("objectiveId is required")
    if posture.get("objectiveId") != objective_id:
        raise ContinuityPlanningError("posture objective does not match requested objective")

    impact = analyze_failure(topology, scenario)
    blockers = list(impact["blockerCodes"])
    evidence_refs = set(impact["evidenceRefs"])
    evidence_refs.update(posture.get("evidenceRefs", []))

    if posture.get("state") != "ready" or posture.get("failoverEligible") is not True:
        blockers.append("continuity-posture-not-failover-eligible")

    target = _select_target(topology, impact)
    if target is None:
        blockers.append("eligible-recovery-target-unavailable")
    else:
        evidence_refs.add(target["evidenceRef"])

    steps = []
    if not blockers and target is not None:
        try:
            order = _recovery_order(topology, set(impact["recoveryNodeIds"]))
        except ContinuityPlanningError:
            blockers.append("recovery-dependency-cycle")
            order = []

        if not blockers:
            step_order = 1
            isolate_id = f"{plan_id}:isolate"
            validate_target_id = f"{plan_id}:validate-target"
            steps.append({
                "stepId": isolate_id,
                "order": step_order,
                "operation": "isolate-failed-scope",
                "targetRef": scenario["scenarioId"],
                "dependsOn": [],
            })
            step_order += 1
            steps.append({
                "stepId": validate_target_id,
                "order": step_order,
                "operation": "validate-recovery-target",
                "targetRef": target["targetId"],
                "dependsOn": [],
            })
            step_order += 1

            verify_steps = {}
            for node_id in order:
                dependency_verifications = []
                for edge in topology.get("edges", []):
                    if edge.get("relationship") not in DEPENDENCY_RELATIONSHIPS:
                        continue
                    if edge.get("sourceNodeId") == node_id and edge.get("targetNodeId") in verify_steps:
                        dependency_verifications.append(verify_steps[edge["targetNodeId"]])
                recover_id = f"{plan_id}:recover:{node_id}"
                verify_id = f"{plan_id}:verify:{node_id}"
                steps.append({
                    "stepId": recover_id,
                    "order": step_order,
                    "operation": "recover-node",
                    "targetRef": node_id,
                    "dependsOn": sorted(set([isolate_id, validate_target_id] + dependency_verifications)),
                })
                step_order += 1
                steps.append({
                    "stepId": verify_id,
                    "order": step_order,
                    "operation": "verify-node",
                    "targetRef": node_id,
                    "dependsOn": [recover_id],
                })
                step_order += 1
                verify_steps[node_id] = verify_id

            verify_service_id = f"{plan_id}:verify-service"
            rollback_id = f"{plan_id}:prepare-rollback"
            promotion_id = f"{plan_id}:request-promotion"
            steps.append({
                "stepId": verify_service_id,
                "order": step_order,
                "operation": "verify-service",
                "targetRef": objective_id,
                "dependsOn": sorted(verify_steps.values()),
            })
            step_order += 1
            steps.append({
                "stepId": rollback_id,
                "order": step_order,
                "operation": "prepare-rollback",
                "targetRef": target["targetId"],
                "dependsOn": [verify_service_id],
            })
            step_order += 1
            steps.append({
                "stepId": promotion_id,
                "order": step_order,
                "operation": "request-promotion",
                "targetRef": target["targetId"],
                "dependsOn": [rollback_id],
            })

    state = "ready-for-approval" if not blockers and target is not None else "blocked"
    target_projection = None if target is None else {
        "targetId": target["targetId"],
        "environment": target["environment"],
        "failureDomain": target["failureDomain"],
        "evidenceRef": target["evidenceRef"],
    }
    return {
        "schemaVersion": "1.0",
        "planId": plan_id,
        "objectiveId": objective_id,
        "topologyId": topology["topologyId"],
        "scenarioId": scenario["scenarioId"],
        "createdAt": created_at or _utc_now(),
        "state": state,
        "target": target_projection,
        "impact": {
            "directlyAffectedNodeIds": impact["directlyAffectedNodeIds"],
            "transitivelyAffectedNodeIds": impact["transitivelyAffectedNodeIds"],
            "affectedNodeIds": impact["affectedNodeIds"],
            "recoveryNodeIds": impact["recoveryNodeIds"],
            "affectedFailureDomains": impact["affectedFailureDomains"],
        },
        "steps": steps,
        "approvalGates": list(APPROVAL_GATES),
        "blockerCodes": sorted(set(blockers)),
        "evidenceRefs": sorted(evidence_refs),
        "requiresApproval": True,
        "executionAuthorized": False,
        "sourceMutationAllowed": False,
    }


def plan_may_execute(plan: dict[str, Any]) -> bool:
    """Fail closed: this planning artifact never grants execution authority."""
    return False
