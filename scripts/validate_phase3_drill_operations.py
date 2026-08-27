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
    operations = load("drill_operations", ROOT / "scripts" / "drill_operations.py")
    operations_store = load("drill_operations_service", ROOT / "scripts" / "drill_operations_service.py")
    recovery_ops = load("recovery_center_operations", ROOT / "scripts" / "recovery_center_operations.py")
    assurance = load("continuity_assurance", ROOT / "scripts" / "continuity_assurance.py")
    signals = load("continuity_signals", ROOT / "runtime" / "continuity_signals.py")
    authority = load("continuity_authority", ROOT / "runtime" / "continuity_authority.py")

    plan = {
        "schemaVersion": "1.0",
        "planId": "plan:documents:region-a-loss",
        "objectiveId": "service:documents:continuity",
        "topologyId": "topology:documents:2026-08-27",
        "scenarioId": "scenario:region-a-loss",
        "createdAt": "2026-08-27T17:35:00Z",
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
            {"stepId": "step:stage-database", "action": "stage-database"},
            {"stepId": "step:stage-service", "action": "stage-service"},
            {"stepId": "step:verify-service", "action": "verify-service"},
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
            "authority": producer,
            "evidenceRef": f"evidence:approval:{name}",
            "observedAt": "2026-08-27T17:36:00Z",
            "validUntil": "2026-08-27T19:00:00Z",
            "reason": "current authority evidence",
        }
        for name, producer in approval_authorities.items()
    }
    approval = governance.evaluate_failover_approval(
        "approval:documents:phase35", plan, approval_gates, "2026-08-27T17:40:00Z"
    )
    assert approval["state"] == "approved"

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
            "authority": producer,
            "evidenceRef": f"evidence:executor:{name}",
            "observedAt": "2026-08-27T17:41:00Z",
            "validUntil": "2026-08-27T18:30:00Z",
            "reason": "fresh executor evidence",
        }
        for name, producer in executor_authorities.items()
    }
    request = executor.build_executor_request(
        "request:documents:phase35", plan, approval, "revision:abc123", executor_gates, "2026-08-27T17:42:00Z"
    )
    assert request["handoffAccepted"] is True

    dispatch = operations.build_drill_dispatch(
        "dispatch:documents:phase35", "execution:documents:phase35", request, plan, "2026-08-27T17:43:00Z"
    )
    assert dispatch["state"] == "accepted"
    assert dispatch["simulationOnly"] is True
    assert dispatch["externalEffectsAuthorized"] is False
    assert dispatch["trafficMutationAllowed"] is False

    execution = operations.run_bounded_drill(dispatch, request, plan, "2026-08-27T17:44:00Z")
    assert execution["state"] == "completed"
    assert execution["completedStepIds"] == [
        "step:stage-database", "step:stage-service", "step:verify-service"
    ]
    assert execution["currentStepIndex"] == 3
    assert execution["externalEffectsAuthorized"] is False

    expired_dispatch = operations.build_drill_dispatch(
        "dispatch:documents:expired", "execution:documents:expired", request, plan, "2026-08-27T19:01:00Z"
    )
    assert expired_dispatch["state"] == "blocked"
    assert "drill-dispatch-approval-expired" in expired_dispatch["blockerCodes"]

    changed_plan = dict(plan) | {"createdAt": "2026-08-27T17:35:01Z"}
    changed_dispatch = operations.build_drill_dispatch(
        "dispatch:documents:changed", "execution:documents:changed", request, changed_plan, "2026-08-27T17:43:00Z"
    )
    assert changed_dispatch["state"] == "blocked"
    assert "drill-dispatch-plan-binding-mismatch" in changed_dispatch["blockerCodes"]

    rollback = operations.build_rollback_plan(
        "rollback-plan:documents:phase35", execution, plan, "2026-08-27T17:46:00Z"
    )
    assert rollback["state"] == "ready-for-drill"
    assert [step["reversesStepId"] for step in rollback["steps"]] == [
        "step:verify-service", "step:stage-service", "step:stage-database"
    ]
    assert rollback["requiresApproval"] is True
    assert rollback["executionAuthorized"] is False
    assert rollback["externalEffectsAuthorized"] is False

    rollback_authorities = {
        "serviceHealth": "target-runtime",
        "dataIntegrity": "everkeep",
        "dependencies": "everkeep",
        "security": "wardveil-security",
        "privacy": "privacy-shield",
    }
    rollback_checks = {
        name: {
            "state": "pass",
            "authority": producer,
            "evidenceRef": f"evidence:rollback:{name}",
            "reason": "verified in isolated drill",
        }
        for name, producer in rollback_authorities.items()
    }
    rollback_evidence = operations.evaluate_rollback_assurance(
        "rollback-evidence:documents:phase35", rollback, "revision:abc123", rollback_checks,
        "2026-08-27T17:48:00Z"
    )
    assert rollback_evidence["state"] == "pass"
    assert rollback_evidence["authoritative"] is True
    assert rollback_evidence["exactRevisionBound"] is True
    assert rollback_evidence["externalEffectsObserved"] is False
    assert rollback_evidence["productionMutationAuthorized"] is False
    assert operations.rollback_evidence_may_authorize_production_mutation(rollback_evidence) is False

    mismatch = operations.evaluate_rollback_assurance(
        "rollback-evidence:documents:mismatch", rollback, "revision:def456", rollback_checks,
        "2026-08-27T17:48:00Z"
    )
    assert mismatch["state"] == "fail"
    assert mismatch["exactRevisionBound"] is False
    assert "rollback-assurance-revision-mismatch" in mismatch["blockerCodes"]

    resources = [
        {
            "resourceId": "documents:primary", "failoverExecutionId": execution["executionId"],
            "failoverExecutorState": "completed", "rollbackEvidenceState": "pass",
        },
        {
            "resourceId": "photos:primary", "failoverExecutionId": "execution:photos:1",
            "failoverExecutorState": "executing", "failoverExecutionUpdatedAt": "2026-08-27T17:48:00Z",
        },
        {
            "resourceId": "vault:primary", "failoverExecutionId": "execution:vault:1",
            "failoverExecutorState": "blocked",
        },
        {"resourceId": "music:primary"},
    ]
    projection = recovery_ops.build_failover_operations_projection(resources, "2026-08-27T17:49:00Z")
    assert projection["schemaVersion"] == "1.0"
    assert projection["executor"]["completed"] == 1
    assert projection["executor"]["executing"] == 1
    assert projection["executor"]["blocked"] == 1
    assert projection["executor"]["not-applicable"] == 1
    assert projection["rollback"] == {"pass": 1, "fail": 0, "unknown": 0, "not-applicable": 3}
    actions = {(item["resourceId"], item["action"]) for item in projection["recommendedActions"]}
    assert ("photos:primary", "inspect-failover-drill") in actions
    assert ("vault:primary", "inspect-failover-drill-blocker") in actions
    assert all(action != "execute-failover" for _, action in actions)

    missing_rollback_projection = recovery_ops.build_failover_operations_projection(
        [{"resourceId": "documents:primary", "failoverExecutionId": "execution:1", "failoverExecutorState": "completed"}],
        "2026-08-27T17:49:00Z",
    )
    assert missing_rollback_projection["rollback"]["unknown"] == 1
    assert missing_rollback_projection["recommendedActions"][0]["action"] == "review-rollback-assurance"

    assurance_record = {
        "assuranceId": "assurance:documents:phase35",
        "objectiveId": plan["objectiveId"],
        "evaluatedAt": "2026-08-27T17:50:00Z",
        "state": "attention",
        "postureState": "attention",
        "schedule": {"state": "due", "overdueSeconds": 0},
        "topologyFreshness": {"state": "current", "ageSeconds": 60},
        "evidenceRefs": ["evidence:assurance:1"],
    }
    policy = {"monitoringEnabled": True, "notifyEnabled": True}
    metrics = assurance.build_monitoring_metrics(policy, assurance_record, {"failoverEligible": True})
    intents = assurance.build_notify_intents(policy, assurance_record)
    assert metrics and intents

    class MonitoringClient:
        def publish_metric(self, payload):
            assert "evidenceRefs" not in payload
            assert payload["metricName"].startswith("everkeep.continuity.")
            return {"accepted": True, "receiptRef": "monitoring-receipt:1"}

    class NotifyClient:
        def deliver_intent(self, payload):
            assert "evidenceRefs" not in payload
            assert payload["dedupeKey"].startswith("everkeep:")
            return {"accepted": True, "receiptRef": "notify-receipt:1"}

    monitoring_delivery = signals.deliver_monitoring_metric(
        "delivery:monitoring:1", metrics[0], MonitoringClient(), "2026-08-27T17:51:00Z"
    )
    notify_delivery = signals.deliver_notify_intent(
        "delivery:notify:1", intents[0], NotifyClient(), "2026-08-27T17:51:00Z"
    )
    assert monitoring_delivery["state"] == "accepted"
    assert monitoring_delivery["authority"] == "goreecloud-monitoring"
    assert notify_delivery["state"] == "accepted"
    assert notify_delivery["authority"] == "goreecloud-notify"
    assert monitoring_delivery["credentialsEmbedded"] is False
    assert notify_delivery["credentialsEmbedded"] is False

    class FailingNotifyClient:
        def deliver_intent(self, payload):
            raise RuntimeError("synthetic provider failure")

    failed_delivery = signals.deliver_notify_intent(
        "delivery:notify:failed", intents[0], FailingNotifyClient(), "2026-08-27T17:52:00Z"
    )
    assert failed_delivery["state"] == "failed"
    assert failed_delivery["reason"] == "provider call failed: RuntimeError"

    class IdentityProvider:
        def read_decision(self, *, gate, subject_ref):
            assert gate == "identity"
            assert subject_ref == plan["objectiveId"]
            return {
                "state": "pass", "authority": "goreecloud-identity",
                "evidenceRef": "evidence:identity:runtime", "validUntil": "2026-08-27T18:30:00Z",
            }

    identity_gate = authority.read_authority_evidence(
        IdentityProvider(), gate="identity", expected_authority="goreecloud-identity",
        subject_ref=plan["objectiveId"], observed_at="2026-08-27T17:53:00Z"
    )
    assert identity_gate["state"] == "pass"
    assert identity_gate["readOnly"] is True
    assert identity_gate["credentialsEmbedded"] is False

    class StaleProvider:
        def read_decision(self, *, gate, subject_ref):
            return {
                "state": "pass", "authority": "privacy-shield",
                "evidenceRef": "evidence:privacy:stale", "validUntil": "2026-08-27T17:00:00Z",
            }

    stale_gate = authority.read_authority_evidence(
        StaleProvider(), gate="privacy", expected_authority="privacy-shield",
        subject_ref=plan["objectiveId"], observed_at="2026-08-27T17:53:00Z"
    )
    assert stale_gate["state"] == "unknown"

    connection = sqlite3.connect(":memory:")
    store = operations_store.DrillOperationsStore(connection)
    store.save_dispatch(dispatch)
    store.save_rollback_plan(rollback)
    store.save_rollback_evidence(rollback_evidence)
    store.save_signal_delivery(monitoring_delivery)
    store.save_signal_delivery(notify_delivery)
    assert len(store.list_signal_deliveries(plan["objectiveId"])) == 2
    try:
        store.save_dispatch(dispatch)
        raise AssertionError("duplicate dispatch should fail")
    except operations_store.DrillOperationsStoreError:
        pass
    try:
        store.save_rollback_plan(dict(rollback) | {"trafficMutationAllowed": True})
        raise AssertionError("unsafe rollback plan should fail")
    except operations_store.DrillOperationsStoreError:
        pass

    for filename in [
        "everkeep.failover-drill-dispatch.schema.json",
        "everkeep.rollback-plan.schema.json",
        "everkeep.rollback-evidence.schema.json",
        "everkeep.signal-delivery.schema.json",
        "everkeep.recovery-center.failover-operations.schema.json",
    ]:
        contract = json.loads((ROOT / "contracts" / filename).read_text())
        assert contract["properties"]["schemaVersion"]["const"] == "1.0"

    rollback_contract = json.loads((ROOT / "contracts" / "everkeep.rollback-plan.schema.json").read_text())
    assert rollback_contract["properties"]["executionAuthorized"]["const"] is False
    assert rollback_contract["properties"]["trafficMutationAllowed"]["const"] is False
    rollback_evidence_contract = json.loads((ROOT / "contracts" / "everkeep.rollback-evidence.schema.json").read_text())
    assert rollback_evidence_contract["properties"]["productionMutationAuthorized"]["const"] is False
    signal_contract = json.loads((ROOT / "contracts" / "everkeep.signal-delivery.schema.json").read_text())
    assert signal_contract["properties"]["credentialsEmbedded"]["const"] is False

    action_contract = json.loads((ROOT / "contracts" / "everkeep.recovery-action.schema.json").read_text())
    for action_name in ["inspect-failover-drill", "inspect-failover-drill-blocker", "review-rollback-assurance"]:
        assert action_name in action_contract["properties"]["action"]["enum"]
    assert "execute-failover" not in action_contract["properties"]["action"]["enum"]

    existing_summary = json.loads((ROOT / "contracts" / "everkeep.recovery-center.summary.schema.json").read_text())
    assert existing_summary["properties"]["schemaVersion"]["const"] == "1.5"

    migration = (ROOT / "db" / "postgres" / "008_drill_operations.sql").read_text()
    for phrase in [
        "everkeep_failover_drill_dispatches", "everkeep_rollback_plans", "everkeep_rollback_evidence",
        "everkeep_continuity_signal_deliveries", "simulation_only = true",
        "external_effects_authorized = false", "traffic_mutation_allowed = false",
        "production_mutation_authorized = false", "credentials_embedded = false",
    ]:
        assert phrase in migration

    docs = (ROOT / "docs" / "PHASE-3-DRILL-OPERATIONS.md").read_text()
    for phrase in [
        "Drill Operations and Rollback Assurance", "Recovery Center 1.5", "exact revision",
        "GoreeCloud Monitoring", "GoreeCloud Notify", "read-only authority", "no `execute-failover` action",
        "implemented but not deployed", "production failover",
    ]:
        assert phrase in docs

    workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text()
    assert "Validate Phase 3 drill operations and rollback assurance" in workflow
    assert "python3 scripts/validate_phase3_drill_operations.py" in workflow

    print("Everkeep Phase 3.5 drill operations and rollback assurance validation passed")


if __name__ == "__main__":
    main()
