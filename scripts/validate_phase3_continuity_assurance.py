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
    assurance_mod = load("continuity_assurance", ROOT / "scripts" / "continuity_assurance.py")
    persistence = load("persistent_service", ROOT / "scripts" / "persistent_service.py")
    assurance_service = load("continuity_assurance_service", ROOT / "scripts" / "continuity_assurance_service.py")
    recovery_center = load("recovery_center", ROOT / "scripts" / "recovery_center.py")

    objective = {
        "schemaVersion": "1.0", "objectiveId": "service:documents:continuity",
        "scope": {"service": "goreecloud-documents"}, "rpoSeconds": 3600,
        "rtoSeconds": 900, "maxExerciseAgeSeconds": 86400, "minFailureDomains": 2,
        "requireAlternateRecoveryTarget": True, "requireDependencyReadiness": True,
        "requireKeyMaterialReadiness": True,
    }
    evidence = {
        "lastProtectionAt": "2026-08-27T11:30:00Z", "measuredRecoverySeconds": 600,
        "lastExerciseAt": "2026-08-27T00:00:00Z",
        "failureDomains": ["provider:a/region:1", "provider:c/region:3"],
        "alternateRecoveryTargetReady": True, "dependenciesReady": True, "keyMaterialReady": True,
        "evidenceRefs": {
            "rpo": "evidence:rpo:1", "rto": "evidence:rto:1", "exercise": "evidence:exercise:1",
            "failureDomains": "evidence:domains:1", "alternateRecoveryTarget": "evidence:alternate:1",
            "dependencies": "evidence:deps:1", "keyMaterial": "evidence:keys:1",
        },
    }
    posture = continuity.evaluate_continuity(objective, evidence, "2026-08-27T12:00:00Z")
    assert posture["state"] == "ready" and posture["failoverEligible"] is True

    policy = {
        "schemaVersion": "1.0", "policyId": "assurance:documents",
        "objectiveId": objective["objectiveId"], "evaluationIntervalSeconds": 3600,
        "maxTopologyAgeSeconds": 7200, "warningLeadSeconds": 600,
        "monitoringEnabled": True, "notifyEnabled": True,
    }
    topology = {
        "schemaVersion": "1.0", "topologyId": "topology:documents:2026-08-27",
        "scope": {"service": "goreecloud-documents"}, "observedAt": "2026-08-27T11:00:00Z",
        "authoritative": True,
        "nodes": [{"nodeId": "service:documents", "nodeType": "service", "state": "ready"}],
        "edges": [], "recoveryTargets": [], "evidenceRefs": ["evidence:topology:1"],
        "sensitivePayloadsExcluded": True,
    }

    ready = assurance_mod.evaluate_assurance(policy, objective, posture, topology, "2026-08-27T11:30:00Z", "2026-08-27T12:00:00Z")
    assert ready["state"] == "ready"
    assert ready["schedule"]["state"] == "scheduled"
    assert ready["topologyFreshness"]["state"] == "current"
    assert ready["evaluationDispatchEligible"] is False

    due = assurance_mod.evaluate_assurance(policy, objective, posture, dict(topology) | {"observedAt": "2026-08-27T10:10:00Z"}, "2026-08-27T11:10:00Z", "2026-08-27T12:00:00Z")
    assert due["state"] == "attention"
    assert due["schedule"]["state"] == "due"
    assert due["topologyFreshness"]["state"] == "attention"
    assert due["evaluationDispatchEligible"] is True

    overdue = assurance_mod.evaluate_assurance(policy, objective, posture, dict(topology) | {"observedAt": "2026-08-27T09:00:00Z"}, "2026-08-27T10:00:00Z", "2026-08-27T12:00:00Z")
    assert overdue["state"] == "degraded"
    assert "continuity-evaluation-overdue" in overdue["blockerCodes"]
    assert "recovery-topology-stale" in overdue["blockerCodes"]

    unknown = assurance_mod.evaluate_assurance(policy, objective, posture, None, "not-a-time", "2026-08-27T12:00:00Z")
    assert unknown["state"] == "unknown"
    assert unknown["schedule"]["state"] == "unknown"
    assert unknown["topologyFreshness"]["state"] == "unknown"

    metrics = assurance_mod.build_monitoring_metrics(policy, overdue, posture)
    assert len(metrics) == 4
    assert all(item["projectionOnly"] is True and item["sensitivePayloadsExcluded"] is True for item in metrics)
    intents = assurance_mod.build_notify_intents(policy, overdue)
    categories = {item["category"] for item in intents}
    assert "continuity-evaluation-overdue" in categories and "recovery-topology-stale" in categories
    assert all(item["deliveryAuthority"] == "goreecloud-notify" for item in intents)
    assert all(item["projectionOnly"] is True and item["deliveryAttempted"] is False for item in intents)

    disabled_policy = dict(policy) | {"monitoringEnabled": False, "notifyEnabled": False}
    assert assurance_mod.build_monitoring_metrics(disabled_policy, overdue, posture) == []
    assert assurance_mod.build_notify_intents(disabled_policy, overdue) == []

    store = persistence.EverkeepStore()
    extension = assurance_service.ContinuityAssuranceStoreExtension(store)
    extension.save_policy(policy)
    assert extension.get_policy(policy["policyId"]) == policy
    extension.record_evaluation(ready)
    assert extension.list_evaluations(objective["objectiveId"])[0]["assuranceId"] == ready["assuranceId"]
    extension.record_signal("monitoring-metric", metrics[0])
    extension.record_signal("notify-intent", intents[0])
    assert {item["signalType"] for item in extension.list_signals(objective["objectiveId"])} == {"monitoring-metric", "notify-intent"}

    resources = [
        {"resourceId": "documents:primary", "protected": True, "readiness": "Recovery Ready", "recoveryEligible": True, "integrityCurrent": True, "restoreTestCurrent": True, "policyCompliant": True, "continuityState": "ready", "rpoCompliant": True, "rtoCompliant": True, "recoveryExerciseCurrent": True, "failureDomainDiverse": True, "topologyCurrent": True, "assuranceScheduleState": "scheduled", "failoverEligible": True, "blockers": []},
        {"resourceId": "photos:primary", "protected": True, "readiness": "At Risk", "recoveryEligible": False, "integrityCurrent": True, "restoreTestCurrent": True, "policyCompliant": True, "continuityState": "attention", "rpoCompliant": True, "rtoCompliant": True, "recoveryExerciseCurrent": True, "failureDomainDiverse": True, "topologyCurrent": True, "assuranceScheduleState": "due", "failoverEligible": False, "blockers": []},
        {"resourceId": "vault:primary", "protected": True, "readiness": "At Risk", "recoveryEligible": False, "integrityCurrent": True, "restoreTestCurrent": True, "policyCompliant": True, "continuityState": "unknown", "rpoCompliant": None, "rtoCompliant": None, "recoveryExerciseCurrent": None, "failureDomainDiverse": None, "topologyCurrent": None, "assuranceScheduleState": "unknown", "failoverEligible": False, "blockers": []},
    ]
    summary = recovery_center.build_summary(resources, "2026-08-27T12:10:00Z")
    assert summary["schemaVersion"] == "1.4"
    assert summary["continuity"]["assuranceSchedule"] == {"scheduled": 1, "due": 1, "overdue": 0, "unknown": 1}
    actions = {(item["resourceId"], item["action"]) for item in summary["recommendedActions"]}
    assert ("documents:primary", "create-failover-plan") in actions
    assert ("photos:primary", "evaluate-continuity-now") in actions
    assert ("vault:primary", "inspect-continuity-assurance") in actions

    for filename in ["everkeep.continuity-assurance-policy.schema.json", "everkeep.continuity-assurance-state.schema.json", "everkeep.monitoring-metric.schema.json", "everkeep.notify-intent.schema.json"]:
        assert json.loads((ROOT / "contracts" / filename).read_text())["properties"]["schemaVersion"]["const"] == "1.0"
    notify_contract = json.loads((ROOT / "contracts" / "everkeep.notify-intent.schema.json").read_text())
    assert notify_contract["properties"]["deliveryAuthority"]["const"] == "goreecloud-notify"
    assert notify_contract["properties"]["deliveryAttempted"]["const"] is False
    assert notify_contract["properties"]["projectionOnly"]["const"] is True
    assert json.loads((ROOT / "contracts" / "everkeep.recovery-center.summary.schema.json").read_text())["properties"]["schemaVersion"]["const"] == "1.4"

    action_contract = json.loads((ROOT / "contracts" / "everkeep.recovery-action.schema.json").read_text())
    for action in ["inspect-continuity-assurance", "evaluate-continuity-now"]:
        assert action in action_contract["properties"]["action"]["enum"]

    migration = (ROOT / "db" / "postgres" / "005_continuity_assurance.sql").read_text()
    for phrase in ["everkeep_continuity_assurance_policies", "everkeep_continuity_assurance_evaluations", "everkeep_continuity_signal_projections", "projection_only = true", "delivery_attempted = false"]:
        assert phrase in migration

    docs = (ROOT / "docs" / "PHASE-3-CONTINUITY-ASSURANCE.md").read_text()
    for phrase in ["scheduled continuity assurance", "topology freshness", "GoreeCloud Monitoring", "GoreeCloud Notify", "does not deliver alerts", "fail closed"]:
        assert phrase in docs

    print("Everkeep Phase 3 continuity assurance validation passed")


if __name__ == "__main__":
    main()
