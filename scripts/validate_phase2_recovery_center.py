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
        {
            "resourceId": "doc:1",
            "protected": True,
            "readiness": "Recovery Ready",
            "recoveryEligible": True,
            "blockers": [],
        },
        {
            "resourceId": "photo:2",
            "protected": True,
            "readiness": "At Risk",
            "recoveryEligible": False,
            "blockers": [
                {"code": "restore-test-stale", "severity": "medium"},
                {"code": "verification-stale", "severity": "high"},
            ],
        },
        {
            "resourceId": "vault:3",
            "protected": False,
            "readiness": "Recovery Blocked",
            "recoveryEligible": False,
            "blockers": [
                {"code": "key-material-unavailable", "severity": "critical"},
                {"code": "policy-noncompliant", "severity": "high"},
            ],
        },
    ]
    summary = mod.build_summary(resources, "2026-08-26T22:00:00Z")
    assert summary["totals"]["resources"] == 3
    assert summary["readiness"] == {
        "recoveryReady": 1,
        "atRisk": 1,
        "recoveryBlocked": 1,
        "unknown": 0,
    }
    assert summary["protection"] == {"protected": 2, "unprotected": 1}
    assert summary["priorityBlockers"][0]["code"] == "key-material-unavailable"

    actions = {(a["resourceId"], a["action"]) for a in summary["recommendedActions"]}
    assert ("doc:1", "restore-resource") in actions
    assert ("photo:2", "restore-resource") not in actions
    assert ("vault:3", "restore-resource") not in actions
    assert ("vault:3", "protect-resource") in actions
    assert ("vault:3", "inspect-key-readiness") in actions

    unknown = mod.build_summary([{"resourceId": "x", "protected": False}], "2026-08-26T22:00:00Z")
    assert unknown["readiness"]["unknown"] == 1
    assert all(a["action"] != "restore-resource" for a in unknown["recommendedActions"])

    summary_schema = json.loads((ROOT / "contracts" / "everkeep.recovery-center.summary.schema.json").read_text())
    action_schema = json.loads((ROOT / "contracts" / "everkeep.recovery-action.schema.json").read_text())
    assert summary_schema["properties"]["schemaVersion"]["const"] == "1.0"
    assert "restore-resource" in action_schema["properties"]["action"]["enum"]

    docs = (ROOT / "docs" / "PHASE-2-RECOVERY-CENTER.md").read_text()
    for phrase in ["backup existence alone", "Recovery Ready", "recoveryEligible: true", "Glaze UI"]:
        assert phrase in docs

    print("Everkeep Phase 2 Recovery Center validation passed")


if __name__ == "__main__":
    main()
