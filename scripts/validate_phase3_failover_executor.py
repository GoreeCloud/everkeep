#!/usr/bin/env python3
import importlib.util
import json
import sqlite3
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
    governance = load("failover_governance", ROOT / "scripts" / "failover_governance.py")
    executor = load("failover_executor", ROOT / "scripts" / "failover_executor.py")
    executor_service = load("failover_executor_service", ROOT / "scripts" / "failover_executor_service.py")

    plan = {
        "schemaVersion": "1.0",
        "planId": "plan:documents:region-a-loss",
        "objectiveId": "service:documents:continuity",
        "topologyId": "topology:documents:2026-08-27",
        "scenarioId": "scenario:region-a-loss",
        "createdAt": "2026-08-27T16:45:00Z",
        "state": "ready-for-approval",
        "target": {
            "targetId": "target:dr-c",
            "environment": "isolated-dr-c",
            "failureDomain": "provider:c/region:3",
            "evidenceRef": "evidence:target:dr-c",
        },
        "impact": {
            "directlyAffectedNodeIds": ["db:documents"],
            "transitivelyAffectedNodeIds": ["service:documents"],
            "affectedNodeIds": ["db:documents", "service:documents"],
            "recoveryNodeIds": ["db:documents", "service:documents"],
            "affectedFailureDomains": ["provider:a/region:1"],
        },
        "steps": [
            {"stepId": "step:prepare-target", "action": "prepare-target"},
            {"stepId": "step:verify-target", "action": "verify-target"},
        ],
        "approvalGates": [
            "operator-approval", "identity-authorized", "privacy-authorized", "wardveil-clear",
            "continuity-evidence-current", "target-ready", "dependencies-ready", "key-material-ready",
        ],
        "blockerCodes": [],
        "evidenceRefs": ["evidence:plan:1", "evidence:target:dr-c"],
        "requiresApproval": True,
        "executionAuthorized": False,
        "sourceMutationAllowed": False,
    }

    approval_authorities = {
        "operator": "operator",
        "identity": "goreecloud-identity",
        "privacy": "privacy-shield",
        "wardveil": "wardveil-security",
        "continuity": "everkeep",
        "target": "everkeep",
        "dependencies": "everkeep",
        "keyMaterial": "everkeep",
    }
    approval_gates = {
        name: {
            "state": "pass",
            "authority": authority,
            "evidenceRef": f"evidence:approval:{name}",
            "observedAt": "2026-08-27T16:50:00Z",
            "validUntil": "2026-08-27T18:00:00Z",
            "reason": "current authority evidence",
        }
        for name, authority in approval_authorities.items()
    }
    approval = governance.evaluate_failover_approval(
        "approval:documents:executor", plan, approval_gates, "2026-08-27T17:00:00Z"
    )
    assert approval["state"] == "approved"
    assert approval["handoffEligible"] is True

    executor_authorities = {
        "identity": "goreecloud-identity",
        "privacy": "privacy-shield",
        "wardveil": "wardveil-security",
        "continuity": "everkeep",
        "target": "everkeep",
        "dependencies": "everkeep",
        "keyMaterial": "everkeep",
    }
    executor_gates = {
        name: {
            "state": "pass",
            "authority": authority,
            "evidenceRef": f"evidence:executor:{name}",
            "observedAt": "2026-08-27T17:01:00Z",
            "validUntil": "2026-08-27T17:30:00Z",
            "reason": "fresh executor-time authority evidence",
        }
        for name, authority in executor_authorities.items()
    }

    request = executor.build_executor_request(
        "request:documents:drill-1", plan, approval, "revision:abc123", executor_gates, "2026-08-27T17:05:00Z"
    )
    assert request["planDigest"] == governance.canonical_plan_digest(plan)
    assert request["handoffAccepted"] is True
    assert request["mode"] == "drill"
    assert request["simulationOnly"] is True
    assert request["externalEffectsAuthorized"] is False
    assert request["sourceMutationAllowed"] is False
    assert request["trafficMutationAllowed"] is False
    assert request["credentialsEmbedded"] is False
    assert not request["blockerCodes"]

    execution = executor.start_execution("execution:documents:drill-1", request, "2026-08-27T17:06:00Z")
    assert execution["state"] == "pending"
    for next_state, step_id in [
        ("validating", None),
        ("authorized", None),
        ("staging", None),
        ("executing", "step:prepare-target"),
        ("verifying", "step:verify-target"),
        ("completed", None),
    ]:
        execution = executor.transition_execution(
            execution,
            next_state,
            step_id=step_id,
            evidence_refs=[f"evidence:state:{next_state}"],
            observed_at="2026-08-27T17:10:00Z",
        )
    assert execution["state"] == "completed"
    assert execution["completedStepIds"] == ["step:prepare-target", "step:verify-target"]
    assert execution["currentStepIndex"] == 2
    assert execution["finishedAt"] is not None
    assert executor.executor_may_produce_external_effects(execution) is False

    try:
        executor.transition_execution(execution, "executing", observed_at="2026-08-27T17:11:00Z")
        raise AssertionError("terminal execution transition should fail")
    except executor.FailoverExecutorError:
        pass

    changed_plan = dict(plan) | {"createdAt": "2026-08-27T16:46:00Z"}
    digest_mismatch = executor.build_executor_request(
        "request:documents:digest-mismatch", changed_plan, approval, "revision:abc123", executor_gates,
        "2026-08-27T17:05:00Z"
    )
    assert digest_mismatch["handoffAccepted"] is False
    assert "executor-plan-binding-mismatch" in digest_mismatch["blockerCodes"]

    expired = executor.build_executor_request(
        "request:documents:expired", plan, approval, "revision:abc123", executor_gates, "2026-08-27T18:01:00Z"
    )
    assert expired["handoffAccepted"] is False
    assert "executor-approval-expired" in expired["blockerCodes"]

    wrong_authority_gates = dict(executor_gates)
    wrong_authority_gates["wardveil"] = dict(executor_gates["wardveil"]) | {"authority": "everkeep"}
    wrong_authority = executor.build_executor_request(
        "request:documents:wrong-authority", plan, approval, "revision:abc123", wrong_authority_gates,
        "2026-08-27T17:05:00Z"
    )
    assert wrong_authority["handoffAccepted"] is False
    assert "executor-wardveil-authority-unknown" in wrong_authority["blockerCodes"]

    unsafe = dict(request) | {"trafficMutationAllowed": True}
    blocked_execution = executor.start_execution("execution:documents:unsafe", unsafe, "2026-08-27T17:06:00Z")
    assert blocked_execution["state"] == "blocked"
    assert "executor-request-not-safe" in blocked_execution["blockerCodes"]

    connection = sqlite3.connect(":memory:")
    store = executor_service.FailoverExecutorStore(connection)
    store.record_request(request)
    seq1 = store.append_state(executor.start_execution("execution:documents:stored", request, "2026-08-27T17:06:00Z"))
    stored = store.latest_state("execution:documents:stored")
    stored = executor.transition_execution(stored, "validating", observed_at="2026-08-27T17:07:00Z")
    seq2 = store.append_state(stored)
    assert (seq1, seq2) == (1, 2)
    assert [item["state"] for item in store.execution_history("execution:documents:stored")] == ["pending", "validating"]
    try:
        store.record_request(request)
        raise AssertionError("duplicate executor request should fail")
    except executor_service.FailoverExecutorStoreError:
        pass
    try:
        store.record_request(unsafe)
        raise AssertionError("unsafe executor request should fail persistence")
    except executor_service.FailoverExecutorStoreError:
        pass

    request_contract = json.loads((ROOT / "contracts" / "everkeep.failover-executor-request.schema.json").read_text())
    state_contract = json.loads((ROOT / "contracts" / "everkeep.failover-executor-state.schema.json").read_text())
    assert request_contract["properties"]["mode"]["const"] == "drill"
    assert state_contract["properties"]["mode"]["const"] == "drill"
    for contract in (request_contract, state_contract):
        assert contract["properties"]["simulationOnly"]["const"] is True
        assert contract["properties"]["externalEffectsAuthorized"]["const"] is False
        assert contract["properties"]["sourceMutationAllowed"]["const"] is False
        assert contract["properties"]["trafficMutationAllowed"]["const"] is False
        assert contract["properties"]["credentialsEmbedded"]["const"] is False

    migration = (ROOT / "db" / "postgres" / "007_failover_executor.sql").read_text()
    for phrase in [
        "everkeep_failover_executor_requests", "everkeep_failover_executor_states",
        "mode = 'drill'", "simulation_only = true", "external_effects_authorized = false",
        "source_mutation_allowed = false", "traffic_mutation_allowed = false", "credentials_embedded = false",
    ]:
        assert phrase in migration

    docs = (ROOT / "docs" / "PHASE-3-FAILOVER-EXECUTOR.md").read_text()
    for phrase in [
        "fresh executor-time authority evidence", "exact plan digest", "simulation-only",
        "no external effects", "GoreeCloud Identity", "Privacy Shield", "Wardveil Security",
        "traffic switching", "Recovery Center", "production failover",
    ]:
        assert phrase in docs

    print("Everkeep Phase 3 controlled failover executor validation passed")


if __name__ == "__main__":
    main()
