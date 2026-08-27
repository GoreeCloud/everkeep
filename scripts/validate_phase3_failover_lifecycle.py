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
    lifecycle = load("recovery_center_lifecycle", ROOT / "scripts" / "recovery_center_lifecycle.py")
    resources = [
        {
            "resourceId": "documents:primary",
            "failoverExecutionId": "execution:documents:1",
            "failoverExecutorState": "completed",
            "rollbackEvidenceState": "pass",
            "failoverAcceptanceState": "pass",
            "failoverExecutionUpdatedAt": "2026-08-27T18:00:00Z",
        },
        {
            "resourceId": "photos:primary",
            "failoverExecutionId": "execution:photos:1",
            "failoverExecutorState": "executing",
            "failoverExecutionUpdatedAt": "2026-08-27T18:01:00Z",
        },
        {
            "resourceId": "vault:primary",
            "failoverExecutionId": "execution:vault:1",
            "failoverExecutorState": "blocked",
        },
        {
            "resourceId": "mail:primary",
            "failoverExecutionId": "execution:mail:1",
            "failoverExecutorState": "completed",
        },
        {
            "resourceId": "notes:primary",
            "failoverExecutionId": "execution:notes:1",
            "failoverExecutorState": "mystery",
        },
        {"resourceId": "music:primary"},
    ]

    projection = lifecycle.build_failover_lifecycle_projection(resources, "2026-08-27T18:05:00Z")
    assert projection["schemaVersion"] == "1.0"
    assert projection["totals"] == {"resources": 6, "executions": 5}
    assert projection["acceptance"] == {"pass": 1, "fail": 0, "unknown": 1, "not-applicable": 3}

    by_resource = {item["resourceId"]: item for item in projection["executions"]}
    assert by_resource["documents:primary"]["state"] == "completed"
    assert by_resource["documents:primary"]["rollbackState"] == "pass"
    assert by_resource["documents:primary"]["acceptanceState"] == "pass"
    assert by_resource["documents:primary"]["refreshRequired"] is False
    assert by_resource["photos:primary"]["phase"] == "active"
    assert by_resource["vault:primary"]["phase"] == "terminal"
    assert by_resource["mail:primary"]["rollbackState"] == "unknown"
    assert by_resource["mail:primary"]["acceptanceState"] == "unknown"
    assert by_resource["mail:primary"]["refreshRequired"] is True
    assert by_resource["notes:primary"]["state"] == "unknown"
    assert by_resource["notes:primary"]["phase"] == "unknown"
    assert by_resource["notes:primary"]["refreshRequired"] is True

    for item in projection["executions"]:
        assert item["simulationOnly"] is True
        assert item["externalEffectsAuthorized"] is False

    actions = {(item["resourceId"], item["action"]) for item in projection["recommendedActions"]}
    assert ("photos:primary", "inspect-failover-drill") in actions
    assert ("vault:primary", "inspect-failover-drill-blocker") in actions
    assert ("mail:primary", "review-rollback-assurance") in actions
    assert ("mail:primary", "evaluate-failover-acceptance") in actions
    assert ("notes:primary", "inspect-failover-drill") in actions
    assert all(action != "execute-failover" for _, action in actions)

    contract = json.loads((ROOT / "contracts" / "everkeep.recovery-center.failover-lifecycle.schema.json").read_text())
    assert contract["properties"]["schemaVersion"]["const"] == "1.0"
    execution_props = contract["properties"]["executions"]["items"]["properties"]
    assert "unknown" in execution_props["state"]["enum"]
    assert execution_props["simulationOnly"]["const"] is True
    assert execution_props["externalEffectsAuthorized"]["const"] is False

    core_summary = json.loads((ROOT / "contracts" / "everkeep.recovery-center.summary.schema.json").read_text())
    assert core_summary["properties"]["schemaVersion"]["const"] == "1.5"
    operations = json.loads((ROOT / "contracts" / "everkeep.recovery-center.failover-operations.schema.json").read_text())
    assert operations["properties"]["schemaVersion"]["const"] == "1.0"

    docs = (ROOT / "docs" / "PHASE-3-FAILOVER-LIFECYCLE.md").read_text()
    for phrase in [
        "Recovery Center 1.5",
        "separate lifecycle detail",
        "rollback assurance",
        "failover acceptance",
        "unknown",
        "execute-failover",
        "simulation-only",
    ]:
        assert phrase in docs

    print("Everkeep Phase 3 failover lifecycle projection validation passed")


if __name__ == "__main__":
    main()
