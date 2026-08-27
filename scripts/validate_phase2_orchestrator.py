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
    mod = load("recovery_orchestrator", ROOT / "scripts" / "recovery_orchestrator.py")
    resources = {
        "database:primary": {"resourceId": "database:primary", "relationships": []},
        "app:documents": {
            "resourceId": "app:documents",
            "relationships": [{"type": "dependency", "resourceId": "database:primary"}],
        },
    }

    plan = mod.build_plan(
        "plan:test",
        ["app:documents"],
        resources,
        mode="sandbox",
        created_at="2026-08-27T12:00:00Z",
        requested_recovery_points={"database:primary": "rp:db:1", "app:documents": "rp:docs:1"},
    )
    assert plan["mode"] == "sandbox"
    assert plan["sourceMutationAllowed"] is False
    assert plan["promotionRequired"] is True
    assert plan["steps"][0]["resourceId"] == "database:primary"
    assert plan["steps"][4]["resourceId"] == "app:documents"
    assert "database:primary:verify" in plan["steps"][4]["dependsOn"]
    assert all(step["targetMode"] in {"none", "isolated"} for step in plan["steps"])

    gates = {
        gate: {"state": "pass", "evidenceRef": f"evidence:{gate}"}
        for gate in mod.REQUIRED_GATES
    }
    execution = mod.evaluate_execution(plan, gates, "exec:test", "staging")
    assert execution["authorized"] is True
    assert execution["state"] == "authorized"
    assert mod.execution_may_start(execution) is True
    assert len(execution["evidenceRefs"]) == len(mod.REQUIRED_GATES)

    missing_security = dict(gates)
    missing_security.pop("wardveil-clear")
    blocked = mod.evaluate_execution(plan, missing_security, "exec:blocked", "staging")
    assert blocked["authorized"] is False
    assert blocked["state"] == "blocked"
    assert "gate:wardveil-clear:unknown" in blocked["blockerCodes"]
    assert mod.execution_may_start(blocked) is False

    production = mod.build_plan("plan:restore", ["database:primary"], resources, mode="restore", created_at="2026-08-27T12:00:00Z")
    assert any(step["targetMode"] == "production" for step in production["steps"])
    assert production["sourceMutationAllowed"] is False

    cyclic = {
        "a": {"relationships": [{"type": "dependency", "resourceId": "b"}]},
        "b": {"relationships": [{"type": "dependency", "resourceId": "a"}]},
    }
    try:
        mod.build_plan("plan:cycle", ["a"], cyclic)
    except mod.RecoveryPlanError:
        pass
    else:
        raise AssertionError("dependency cycles must fail closed")

    plan_schema = json.loads((ROOT / "contracts" / "everkeep.recovery-plan.schema.json").read_text())
    execution_schema = json.loads((ROOT / "contracts" / "everkeep.recovery-execution.schema.json").read_text())
    assert plan_schema["properties"]["sourceMutationAllowed"]["const"] is False
    assert execution_schema["properties"]["sourceMutationAllowed"]["const"] is False

    migration = (ROOT / "db" / "postgres" / "002_resilience_control_plane.sql").read_text()
    for table in ["everkeep_recovery_plans", "everkeep_recovery_executions"]:
        assert table in migration

    openapi = (ROOT / "api" / "openapi.yaml").read_text()
    for route in ["/v1/recovery-center/summary:", "/v1/recovery-plans:", "/v1/recovery-plans/{planId}/authorize:"]:
        assert route in openapi

    docs = (ROOT / "docs" / "PHASE-2-RECOVERY-ORCHESTRATION.md").read_text()
    for phrase in ["dependencies before dependents", "source data", "Recovery Sandbox", "fail closed", "promotion"]:
        assert phrase in docs

    print("Everkeep Phase 2 recovery orchestration validation passed")


if __name__ == "__main__":
    main()
