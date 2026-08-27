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
    mod = load("recovery_center", ROOT / "scripts" / "recovery_center.py")
    resources = [
        {"resourceId": "doc:1", "protected": True, "readiness": "Recovery Ready", "recoveryEligible": True, "preservationEligible": True, "exportEligible": True, "integrityCurrent": True, "restoreTestCurrent": True, "policyCompliant": True, "blockers": []},
        {"resourceId": "photo:2", "protected": True, "readiness": "At Risk", "recoveryEligible": False, "integrityCurrent": False, "restoreTestCurrent": False, "policyCompliant": True, "blockers": [{"code": "restore-test-stale", "severity": "medium"}, {"code": "verification-stale", "severity": "high"}]},
        {"resourceId": "vault:3", "protected": False, "readiness": "Recovery Blocked", "recoveryEligible": False, "integrityCurrent": None, "restoreTestCurrent": None, "policyCompliant": False, "blockers": [{"code": "key-material-unavailable", "severity": "critical"}, {"code": "policy-noncompliant", "severity": "high"}]},
    ]

    summary = mod.build_summary(resources, "2026-08-27T12:00:00Z")
    assert summary["schemaVersion"] == "1.5"
    assert summary["totals"]["resources"] == 3
    assert summary["readiness"] == {"recoveryReady": 1, "atRisk": 1, "recoveryBlocked": 1, "unknown": 0}
    assert summary["protection"] == {"protected": 2, "unprotected": 1}
    assert summary["assurance"]["integrityCurrent"] == {"pass": 1, "fail": 1, "unknown": 1}
    assert summary["continuity"]["state"] == {"ready": 0, "attention": 0, "degraded": 0, "unknown": 3}
    assert summary["continuity"]["objectives"]["rpoCompliant"] == {"pass": 0, "fail": 0, "unknown": 3}
    assert summary["continuity"]["objectives"]["topologyCurrent"] == {"pass": 0, "fail": 0, "unknown": 3}
    assert summary["continuity"]["assuranceSchedule"] == {"scheduled": 0, "due": 0, "overdue": 0, "unknown": 3}
    assert summary["failoverGovernance"]["approval"]["not-applicable"] == 3
    assert summary["failoverGovernance"]["acceptance"]["not-applicable"] == 3
    assert summary["priorityBlockers"][0]["code"] == "key-material-unavailable"

    actions = {(action["resourceId"], action["action"]) for action in summary["recommendedActions"]}
    for required in [
        ("doc:1", "restore-resource"), ("doc:1", "create-recovery-plan"), ("doc:1", "run-recovery-sandbox"),
        ("doc:1", "create-preservation-capsule"), ("doc:1", "export-resource"),
        ("vault:3", "protect-resource"), ("vault:3", "inspect-key-readiness"),
    ]:
        assert required in actions
    assert ("photo:2", "restore-resource") not in actions
    assert ("vault:3", "restore-resource") not in actions
    assert ("doc:1", "inspect-continuity-assurance") in actions

    unknown = mod.build_summary([{"resourceId": "x", "protected": False}], "2026-08-27T12:00:00Z")
    assert unknown["readiness"]["unknown"] == 1
    assert unknown["assurance"]["integrityCurrent"]["unknown"] == 1
    assert unknown["continuity"]["state"]["unknown"] == 1
    assert unknown["continuity"]["objectives"]["topologyCurrent"]["unknown"] == 1
    assert unknown["continuity"]["assuranceSchedule"]["unknown"] == 1
    assert unknown["failoverGovernance"]["approval"]["not-applicable"] == 1
    assert unknown["failoverGovernance"]["acceptance"]["not-applicable"] == 1
    assert all(action["action"] != "restore-resource" for action in unknown["recommendedActions"])

    summary_schema = json.loads((ROOT / "contracts" / "everkeep.recovery-center.summary.schema.json").read_text())
    action_schema = json.loads((ROOT / "contracts" / "everkeep.recovery-action.schema.json").read_text())
    assert summary_schema["properties"]["schemaVersion"]["const"] == "1.5"
    for action in ["restore-resource", "run-recovery-sandbox", "create-preservation-capsule", "export-resource"]:
        assert action in action_schema["properties"]["action"]["enum"]

    docs = (ROOT / "docs" / "PHASE-2-RECOVERY-CENTER.md").read_text()
    for phrase in ["backup existence alone", "Recovery Ready", "recoveryEligible: true", "Glaze UI", "Assurance coverage"]:
        assert phrase in docs

    print("Everkeep Phase 2 Recovery Center validation passed")


if __name__ == "__main__":
    main()
