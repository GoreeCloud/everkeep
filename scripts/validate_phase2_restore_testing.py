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
    mod = load("restore_test_scheduler", ROOT / "scripts" / "restore_test_scheduler.py")
    resource = {"resourceId": "db:1", "createdAt": "2026-08-01T00:00:00Z"}
    policy = {
        "policyId": "policy:db",
        "enabled": True,
        "verification": {"restoreTestIntervalSeconds": 86400, "requireRecoverySandbox": True},
    }
    evidence = {"lastSuccessfulRestoreTestAt": "2026-08-25T00:00:00Z"}
    gates = {
        name: {"state": "pass", "evidenceRef": f"ref:{name}"}
        for name in ["identity-authorized", "privacy-authorized", "wardveil-clear", "recovery-point-eligible", "sandbox-available"]
    }

    due = mod.build_schedule("schedule:1", resource, policy, evidence, gates, "2026-08-26T12:00:00Z")
    assert due["temporalState"] == "due"
    assert due["dispatchState"] == "ready"
    assert due["dispatchable"] is True
    assert due["requiresSandbox"] is True
    assert due["sourceMutationAllowed"] is False

    scheduled = mod.build_schedule("schedule:2", resource, policy, evidence, gates, "2026-08-25T12:00:00Z")
    assert scheduled["temporalState"] == "scheduled"
    assert scheduled["dispatchable"] is False

    overdue = mod.build_schedule("schedule:3", resource, policy, evidence, gates, "2026-08-28T12:00:00Z")
    assert overdue["temporalState"] == "overdue"

    missing_wardveil = dict(gates)
    missing_wardveil.pop("wardveil-clear")
    unknown = mod.build_schedule("schedule:4", resource, policy, evidence, missing_wardveil, "2026-08-26T12:00:00Z")
    assert unknown["dispatchState"] == "unknown"
    assert unknown["dispatchable"] is False
    assert "gate:wardveil-clear:unknown" in unknown["blockers"]

    failed_sandbox = dict(gates)
    failed_sandbox["sandbox-available"] = {"state": "fail", "evidenceRef": "ref:sandbox:failed"}
    blocked = mod.build_schedule("schedule:5", resource, policy, evidence, failed_sandbox, "2026-08-26T12:00:00Z")
    assert blocked["dispatchState"] == "blocked"
    assert blocked["dispatchable"] is False

    no_anchor = mod.build_schedule("schedule:6", {"resourceId": "x"}, policy, {}, gates, "2026-08-26T12:00:00Z")
    assert no_anchor["temporalState"] == "unknown"
    assert no_anchor["nextDueAt"] is None

    try:
        mod.build_schedule("bad", resource, {"policyId": "p", "enabled": False, "verification": {}}, {}, {}, "2026-08-26T12:00:00Z")
    except mod.RestoreTestScheduleError:
        pass
    else:
        raise AssertionError("invalid scheduling policy must fail closed")

    schema = json.loads((ROOT / "contracts" / "everkeep.restore-test-schedule.schema.json").read_text())
    assert schema["properties"]["sourceMutationAllowed"]["const"] is False
    migration = (ROOT / "db" / "postgres" / "003_assurance_succession.sql").read_text()
    assert "everkeep_restore_test_schedules" in migration
    openapi = (ROOT / "api" / "openapi.yaml").read_text()
    assert "/v1/resources/{resourceId}/restore-test-schedule/evaluate:" in openapi
    docs = (ROOT / "docs" / "PHASE-2-RESTORE-TESTING.md").read_text()
    for phrase in ["policy-derived", "Recovery Sandbox", "source data", "Unknown"]:
        assert phrase in docs

    print("Everkeep Phase 2 restore-test scheduling validation passed")


if __name__ == "__main__":
    main()
