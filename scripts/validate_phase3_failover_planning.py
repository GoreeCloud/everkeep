#!/usr/bin/env python3
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    continuity = load("continuity", ROOT / "scripts" / "continuity.py")
    planner = load("continuity_planner", ROOT / "scripts" / "continuity_planner.py")
    persistence = load("persistent_service", ROOT / "scripts" / "persistent_service.py")
    planning_service = load("continuity_planning_service", ROOT / "scripts" / "continuity_planning_service.py")
    recovery_center = load("recovery_center", ROOT / "scripts" / "recovery_center.py")

    objective = {"schemaVersion": "1.0", "objectiveId": "service:documents:continuity", "scope": {"service": "goreecloud-documents"}, "rpoSeconds": 3600, "rtoSeconds": 900, "maxExerciseAgeSeconds": 86400, "minFailureDomains": 2, "requireAlternateRecoveryTarget": True, "requireDependencyReadiness": True, "requireKeyMaterialReadiness": True}
    evidence = {"lastProtectionAt": "2026-08-27T11:30:00Z", "measuredRecoverySeconds": 600, "lastExerciseAt": "2026-08-27T00:00:00Z", "failureDomains": ["provider:a/region:1", "provider:c/region:3"], "alternateRecoveryTargetReady": True, "dependenciesReady": True, "keyMaterialReady": True, "evidenceRefs": {"rpo": "evidence:rpo:1", "rto": "evidence:rto:1", "exercise": "evidence:exercise:1", "failureDomains": "evidence:domains:1", "alternateRecoveryTarget": "evidence:alternate:1", "dependencies": "evidence:deps:1", "keyMaterial": "evidence:keys:1"}}
    posture = continuity.evaluate_continuity(objective, evidence, "2026-08-27T12:00:00Z")
    assert posture["state"] == "ready" and posture["failoverEligible"] is True

    topology = {
        "schemaVersion": "1.0", "topologyId": "topology:documents:2026-08-27", "scope": {"service": "goreecloud-documents"}, "observedAt": "2026-08-27T11:55:00Z", "authoritative": True,
        "nodes": [
            {"nodeId": "service:documents", "nodeType": "service", "state": "ready", "failureDomain": "provider:b/region:2", "displayName": "Documents", "evidenceRef": "evidence:node:service"},
            {"nodeId": "db:documents", "nodeType": "data-store", "state": "ready", "failureDomain": "provider:a/region:1", "displayName": "Documents DB", "evidenceRef": "evidence:node:db"},
            {"nodeId": "storage:documents", "nodeType": "storage", "state": "ready", "failureDomain": "provider:a/region:1", "displayName": "Documents storage", "evidenceRef": "evidence:node:storage"},
            {"nodeId": "identity:primary", "nodeType": "identity", "state": "ready", "failureDomain": "provider:b/region:2", "displayName": "Identity", "evidenceRef": "evidence:node:identity"},
            {"nodeId": "dns:primary", "nodeType": "dns", "state": "ready", "failureDomain": "provider:b/region:2", "displayName": "DNS", "evidenceRef": "evidence:node:dns"},
        ],
        "edges": [
            {"sourceNodeId": "service:documents", "targetNodeId": "db:documents", "relationship": "depends-on"},
            {"sourceNodeId": "db:documents", "targetNodeId": "storage:documents", "relationship": "depends-on"},
            {"sourceNodeId": "service:documents", "targetNodeId": "identity:primary", "relationship": "depends-on"},
            {"sourceNodeId": "service:documents", "targetNodeId": "dns:primary", "relationship": "uses"},
        ],
        "recoveryTargets": [{"targetId": "target:dr-c", "environment": "isolated-dr-c", "state": "ready", "failureDomain": "provider:c/region:3", "supportsNodeIds": ["service:documents", "db:documents", "storage:documents"], "evidenceRef": "evidence:target:dr-c"}],
        "evidenceRefs": ["evidence:topology:1"], "sensitivePayloadsExcluded": True,
    }
    scenario = {"schemaVersion": "1.0", "scenarioId": "scenario:region-a-loss", "name": "Loss of provider A region 1", "failureType": "region-loss", "createdAt": "2026-08-27T12:00:00Z", "affectedNodeIds": [], "affectedFailureDomains": ["provider:a/region:1"], "simulated": True, "productionMutationAllowed": False}

    impact = planner.analyze_failure(topology, scenario)
    assert impact["state"] == "analyzed"
    assert impact["directlyAffectedNodeIds"] == ["db:documents", "storage:documents"]
    assert impact["transitivelyAffectedNodeIds"] == ["service:documents"]
    assert impact["recoveryNodeIds"] == ["db:documents", "service:documents", "storage:documents"]

    plan = planner.build_failover_plan("plan:documents:region-a-loss", objective, posture, topology, scenario, "2026-08-27T12:01:00Z")
    assert plan["state"] == "ready-for-approval" and plan["target"]["targetId"] == "target:dr-c"
    assert plan["requiresApproval"] is True and plan["executionAuthorized"] is False and plan["sourceMutationAllowed"] is False
    assert planner.plan_may_execute(plan) is False
    operations = [step["operation"] for step in plan["steps"]]
    assert operations[0] == "isolate-failed-scope" and "recover-node" in operations and operations[-1] == "request-promotion"

    blocked_topology = dict(topology); blocked_topology["recoveryTargets"] = [dict(topology["recoveryTargets"][0]) | {"state": "unavailable"}]
    blocked = planner.build_failover_plan("plan:documents:no-target", objective, posture, blocked_topology, scenario, "2026-08-27T12:02:00Z")
    assert blocked["state"] == "blocked" and "eligible-recovery-target-unavailable" in blocked["blockerCodes"] and blocked["steps"] == []

    non_authoritative = dict(topology); non_authoritative["authoritative"] = False
    non_authoritative_plan = planner.build_failover_plan("plan:documents:untrusted-topology", objective, posture, non_authoritative, scenario, "2026-08-27T12:03:00Z")
    assert non_authoritative_plan["state"] == "blocked" and "recovery-topology-not-authoritative" in non_authoritative_plan["blockerCodes"]

    store = persistence.EverkeepStore(); extension = planning_service.ContinuityPlanningStoreExtension(store)
    extension.save_topology(topology); extension.save_scenario(scenario); extension.save_plan(plan)
    assert extension.get_topology(topology["topologyId"])["authoritative"] is True
    assert extension.get_scenario(scenario["scenarioId"])["simulated"] is True
    assert extension.get_plan(plan["planId"])["executionAuthorized"] is False
    assert extension.list_plans(objective["objectiveId"])[0]["planId"] == plan["planId"]

    resources = [
        {"resourceId": "documents:primary", "protected": True, "readiness": "Recovery Ready", "recoveryEligible": True, "integrityCurrent": True, "restoreTestCurrent": True, "policyCompliant": True, "continuityState": "ready", "rpoCompliant": True, "rtoCompliant": True, "recoveryExerciseCurrent": True, "failureDomainDiverse": True, "topologyCurrent": True, "assuranceScheduleState": "scheduled", "failoverEligible": True, "blockers": []},
        {"resourceId": "photos:primary", "protected": True, "readiness": "At Risk", "recoveryEligible": False, "integrityCurrent": True, "restoreTestCurrent": True, "policyCompliant": True, "continuityState": "unknown", "rpoCompliant": True, "rtoCompliant": True, "recoveryExerciseCurrent": True, "failureDomainDiverse": True, "topologyCurrent": False, "assuranceScheduleState": "overdue", "failoverEligible": False, "blockers": [{"code": "recovery-topology-stale", "severity": "high"}]},
    ]
    summary = recovery_center.build_summary(resources, "2026-08-27T12:05:00Z")
    assert summary["schemaVersion"] == "1.4"
    assert summary["continuity"]["objectives"]["topologyCurrent"] == {"pass": 1, "fail": 1, "unknown": 0}
    assert summary["continuity"]["assuranceSchedule"] == {"scheduled": 1, "due": 0, "overdue": 1, "unknown": 0}
    actions = {(item["resourceId"], item["action"]) for item in summary["recommendedActions"]}
    assert ("documents:primary", "create-failover-plan") in actions
    assert ("photos:primary", "inspect-recovery-topology") in actions
    assert ("photos:primary", "evaluate-continuity-now") in actions
    assert ("photos:primary", "create-failover-plan") not in actions

    for filename in ["everkeep.recovery-topology.schema.json", "everkeep.failure-scenario.schema.json", "everkeep.failover-plan.schema.json"]:
        assert json.loads((ROOT / "contracts" / filename).read_text())["properties"]["schemaVersion"]["const"] == "1.0"
    plan_contract = json.loads((ROOT / "contracts" / "everkeep.failover-plan.schema.json").read_text())
    assert plan_contract["properties"]["executionAuthorized"]["const"] is False
    assert plan_contract["properties"]["sourceMutationAllowed"]["const"] is False
    assert plan_contract["properties"]["requiresApproval"]["const"] is True
    assert json.loads((ROOT / "contracts" / "everkeep.recovery-center.summary.schema.json").read_text())["properties"]["schemaVersion"]["const"] == "1.4"
    action_contract = json.loads((ROOT / "contracts" / "everkeep.recovery-action.schema.json").read_text())
    for action in ["create-failover-plan", "inspect-recovery-topology"]:
        assert action in action_contract["properties"]["action"]["enum"]

    migration = (ROOT / "db" / "postgres" / "004_continuity_planning.sql").read_text()
    assert "everkeep_continuity_topologies" in migration and "execution_authorized = false" in migration and "source_mutation_allowed = false" in migration
    docs = (ROOT / "docs" / "PHASE-3-FAILOVER-PLANNING.md").read_text()
    for phrase in ["recovery-topology evidence", "simulated failure scenarios", "dependency-aware recovery order", "requiresApproval: true", "does not switch traffic", "GoreeCloud Mesh"]:
        assert phrase in docs
    print("Everkeep Phase 3 failover planning validation passed")


if __name__ == "__main__":
    main()
