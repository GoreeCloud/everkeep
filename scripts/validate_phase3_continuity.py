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
    persistence = load("persistent_service", ROOT / "scripts" / "persistent_service.py")
    continuity_service = load("continuity_service", ROOT / "scripts" / "continuity_service.py")
    recovery_center = load("recovery_center", ROOT / "scripts" / "recovery_center.py")

    objective = {
        "schemaVersion": "1.0",
        "objectiveId": "service:documents:continuity",
        "scope": {"service": "goreecloud-documents"},
        "rpoSeconds": 3600,
        "rtoSeconds": 900,
        "maxExerciseAgeSeconds": 86400,
        "minFailureDomains": 2,
        "requireAlternateRecoveryTarget": True,
        "requireDependencyReadiness": True,
        "requireKeyMaterialReadiness": True,
    }
    ready_evidence = {
        "lastProtectionAt": "2026-08-27T11:30:00Z",
        "measuredRecoverySeconds": 600,
        "lastExerciseAt": "2026-08-27T00:00:00Z",
        "failureDomains": ["provider:a/region:1", "provider:b/region:2"],
        "alternateRecoveryTargetReady": True,
        "dependenciesReady": True,
        "keyMaterialReady": True,
        "evidenceRefs": {
            "rpo": "evidence:rpo:1",
            "rto": "evidence:rto:1",
            "exercise": "evidence:exercise:1",
            "failureDomains": "evidence:domains:1",
            "alternateRecoveryTarget": "evidence:alternate:1",
            "dependencies": "evidence:deps:1",
            "keyMaterial": "evidence:keys:1"
        }
    }

    ready = continuity.evaluate_continuity(objective, ready_evidence, "2026-08-27T12:00:00Z")
    assert ready["state"] == "ready"
    assert ready["failoverEligible"] is True
    assert ready["dimensions"]["rpo"]["measured"] == 1800
    assert ready["dimensions"]["failureDomains"]["measured"] == 2

    attention_evidence = dict(ready_evidence)
    attention_evidence["lastProtectionAt"] = "2026-08-27T11:10:00Z"
    attention = continuity.evaluate_continuity(objective, attention_evidence, "2026-08-27T12:00:00Z")
    assert attention["state"] == "attention"
    assert "rpo-at-risk" in attention["warningCodes"]
    assert attention["failoverEligible"] is False

    degraded_evidence = dict(ready_evidence)
    degraded_evidence.update({
        "lastProtectionAt": "2026-08-27T10:00:00Z",
        "failureDomains": ["provider:a/region:1"],
        "alternateRecoveryTargetReady": False,
    })
    degraded = continuity.evaluate_continuity(objective, degraded_evidence, "2026-08-27T12:00:00Z")
    assert degraded["state"] == "degraded"
    assert "rpo-missed" in degraded["blockerCodes"]
    assert "failure-domain-concentration" in degraded["blockerCodes"]
    assert "alternate-recovery-target-unavailable" in degraded["blockerCodes"]
    assert degraded["failoverEligible"] is False

    unknown = continuity.evaluate_continuity(objective, {}, "2026-08-27T12:00:00Z")
    assert unknown["state"] == "unknown"
    assert unknown["failoverEligible"] is False
    assert "rpo-evidence-unknown" in unknown["blockerCodes"]

    checks = {
        name: {"state": "pass", "evidenceRef": f"evidence:{name}:1", "reason": "verified"}
        for name in ("integrity", "serviceHealth", "dependencies", "security", "privacy")
    }
    exercise = continuity.build_exercise_record(
        "exercise:documents:2026-08-27",
        objective["objectiveId"],
        "failover-drill",
        "2026-08-27T11:00:00Z",
        "2026-08-27T11:10:00Z",
        "isolated-dr",
        checks,
    )
    assert exercise["result"] == "pass"
    assert exercise["durationSeconds"] == 600
    assert exercise["productionMutationAllowed"] is False

    store = persistence.EverkeepStore()
    extension = continuity_service.ContinuityStoreExtension(store)
    extension.save_objective(objective)
    assert extension.get_objective(objective["objectiveId"]) == objective
    extension.record_exercise(exercise)
    assert extension.list_exercises(objective["objectiveId"])[0]["exerciseId"] == exercise["exerciseId"]
    durable_posture = extension.posture(objective["objectiveId"], ready_evidence, "2026-08-27T12:00:00Z")
    assert durable_posture["state"] == "ready"

    resources = [
        {
            "resourceId": "documents:primary",
            "protected": True,
            "readiness": "Recovery Ready",
            "recoveryEligible": True,
            "integrityCurrent": True,
            "restoreTestCurrent": True,
            "policyCompliant": True,
            "continuityState": "ready",
            "rpoCompliant": True,
            "rtoCompliant": True,
            "recoveryExerciseCurrent": True,
            "failureDomainDiverse": True,
            "blockers": [],
        },
        {
            "resourceId": "photos:primary",
            "protected": True,
            "readiness": "At Risk",
            "recoveryEligible": False,
            "integrityCurrent": True,
            "restoreTestCurrent": True,
            "policyCompliant": True,
            "continuityState": "degraded",
            "rpoCompliant": False,
            "rtoCompliant": True,
            "recoveryExerciseCurrent": False,
            "failureDomainDiverse": False,
            "alternateRecoveryTargetReady": False,
            "blockers": [
                {"code": "rpo-missed", "severity": "high"},
                {"code": "recovery-exercise-stale", "severity": "medium"},
                {"code": "failure-domain-concentration", "severity": "high"},
            ],
        },
    ]
    summary = recovery_center.build_summary(resources, "2026-08-27T12:00:00Z")
    assert summary["schemaVersion"] == "1.2"
    assert summary["continuity"]["state"]["ready"] == 1
    assert summary["continuity"]["state"]["degraded"] == 1
    assert summary["continuity"]["objectives"]["rpoCompliant"]["fail"] == 1
    actions = {(item["resourceId"], item["action"]) for item in summary["recommendedActions"]}
    assert ("photos:primary", "inspect-continuity-objective") in actions
    assert ("photos:primary", "run-disaster-recovery-drill") in actions
    assert ("photos:primary", "inspect-failure-domains") in actions
    assert ("photos:primary", "inspect-alternate-recovery-target") in actions

    for filename in [
        "everkeep.continuity-objective.schema.json",
        "everkeep.continuity-posture.schema.json",
        "everkeep.recovery-exercise.schema.json",
    ]:
        contract = json.loads((ROOT / "contracts" / filename).read_text())
        assert contract["properties"]["schemaVersion"]["const"] == "1.0"

    summary_contract = json.loads((ROOT / "contracts" / "everkeep.recovery-center.summary.schema.json").read_text())
    assert summary_contract["properties"]["schemaVersion"]["const"] == "1.2"
    action_contract = json.loads((ROOT / "contracts" / "everkeep.recovery-action.schema.json").read_text())
    for action in [
        "inspect-continuity-objective",
        "run-disaster-recovery-drill",
        "inspect-failure-domains",
        "inspect-alternate-recovery-target",
    ]:
        assert action in action_contract["properties"]["action"]["enum"]

    docs = (ROOT / "docs" / "PHASE-3-CONTINUITY.md").read_text()
    for phrase in [
        "RPO and RTO",
        "failure-domain",
        "recovery exercise",
        "fail closed",
        "does not perform failover",
        "GoreeCloud Mesh",
    ]:
        assert phrase in docs

    print("Everkeep Phase 3 continuity validation passed")


if __name__ == "__main__":
    main()
