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
    governance = load("failover_governance", ROOT / "scripts" / "failover_governance.py")
    persistence = load("persistent_service", ROOT / "scripts" / "persistent_service.py")
    governance_service = load("failover_governance_service", ROOT / "scripts" / "failover_governance_service.py")
    recovery_center = load("recovery_center", ROOT / "scripts" / "recovery_center.py")

    plan = {
        "schemaVersion": "1.0",
        "planId": "plan:documents:region-a-loss",
        "objectiveId": "service:documents:continuity",
        "topologyId": "topology:documents:2026-08-27",
        "scenarioId": "scenario:region-a-loss",
        "createdAt": "2026-08-27T11:45:00Z",
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
        "steps": [],
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

    authorities = {
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
            "observedAt": "2026-08-27T11:55:00Z",
            "validUntil": "2026-08-27T12:30:00Z",
            "reason": "current authority evidence",
        }
        for name, authority in authorities.items()
    }

    digest = governance.canonical_plan_digest(plan)
    assert len(digest) == 64
    assert digest == governance.canonical_plan_digest(dict(plan))
    changed_plan = dict(plan) | {"createdAt": "2026-08-27T11:46:00Z"}
    assert governance.canonical_plan_digest(changed_plan) != digest

    approved = governance.evaluate_failover_approval(
        "approval:documents:1", plan, approval_gates, "2026-08-27T12:00:00Z"
    )
    assert approved["state"] == "approved"
    assert approved["planDigest"] == digest
    assert approved["expiresAt"] == "2026-08-27T12:30:00Z"
    assert approved["handoffEligible"] is True
    assert approved["executionAuthorized"] is False
    assert approved["executionCredential"] is False
    assert approved["sourceMutationAllowed"] is False
    assert governance.approval_may_execute(approved) is False

    expired = governance.evaluate_failover_approval(
        "approval:documents:expired", plan, approval_gates, "2026-08-27T13:00:00Z"
    )
    assert expired["state"] == "expired"
    assert expired["handoffEligible"] is False
    assert any(code.endswith("-expired") for code in expired["blockerCodes"])

    denied_gates = dict(approval_gates)
    denied_gates["privacy"] = dict(approval_gates["privacy"]) | {"state": "fail", "reason": "alternate placement denied"}
    denied = governance.evaluate_failover_approval(
        "approval:documents:denied", plan, denied_gates, "2026-08-27T12:00:00Z"
    )
    assert denied["state"] == "denied"
    assert "failover-approval-privacy-denied" in denied["blockerCodes"]

    unknown_gates = dict(approval_gates)
    unknown_gates["identity"] = dict(approval_gates["identity"]) | {"authority": "unknown-issuer"}
    unknown = governance.evaluate_failover_approval(
        "approval:documents:unknown", plan, unknown_gates, "2026-08-27T12:00:00Z"
    )
    assert unknown["state"] == "unknown"
    assert "failover-approval-identity-authority-unknown" in unknown["blockerCodes"]

    execution = {
        "schemaVersion": "1.0",
        "executionId": "execution:documents:1",
        "planId": plan["planId"],
        "state": "completed",
        "environment": "isolated-dr-c",
        "authorized": True,
        "sourceMutationAllowed": False,
        "gateResults": {},
        "evidenceRefs": ["evidence:execution:1"],
        "startedAt": "2026-08-27T12:05:00Z",
        "finishedAt": "2026-08-27T12:15:00Z",
    }
    acceptance_authorities = {
        "serviceHealth": "target-runtime",
        "dataIntegrity": "everkeep",
        "dependencies": "everkeep",
        "security": "wardveil-security",
        "privacy": "privacy-shield",
        "rollback": "everkeep",
    }
    acceptance_checks = {
        name: {
            "state": "pass",
            "authority": authority,
            "evidenceRef": f"evidence:acceptance:{name}",
            "reason": "verified",
        }
        for name, authority in acceptance_authorities.items()
    }

    acceptance = governance.evaluate_failover_acceptance(
        "acceptance:documents:1",
        plan,
        execution,
        "revision:abc123",
        "revision:abc123",
        acceptance_checks,
        "2026-08-27T12:20:00Z",
    )
    assert acceptance["state"] == "pass"
    assert acceptance["authoritative"] is True
    assert acceptance["exactRevisionBound"] is True
    assert acceptance["planDigest"] == digest
    assert acceptance["environment"] == "isolated-dr-c"
    assert acceptance["productionMutationAuthorized"] is False
    assert governance.acceptance_may_authorize_mutation(acceptance) is False

    revision_mismatch = governance.evaluate_failover_acceptance(
        "acceptance:documents:revision-mismatch",
        plan,
        execution,
        "revision:abc123",
        "revision:def456",
        acceptance_checks,
        "2026-08-27T12:20:00Z",
    )
    assert revision_mismatch["state"] == "fail"
    assert revision_mismatch["exactRevisionBound"] is False
    assert "failover-acceptance-revision-mismatch" in revision_mismatch["blockerCodes"]

    environment_mismatch = governance.evaluate_failover_acceptance(
        "acceptance:documents:environment-mismatch",
        plan,
        dict(execution) | {"environment": "wrong-environment"},
        "revision:abc123",
        "revision:abc123",
        acceptance_checks,
        "2026-08-27T12:20:00Z",
    )
    assert environment_mismatch["state"] == "fail"
    assert "failover-acceptance-environment-mismatch" in environment_mismatch["blockerCodes"]

    missing_security = dict(acceptance_checks)
    missing_security.pop("security")
    unknown_acceptance = governance.evaluate_failover_acceptance(
        "acceptance:documents:unknown",
        plan,
        execution,
        "revision:abc123",
        "revision:abc123",
        missing_security,
        "2026-08-27T12:20:00Z",
    )
    assert unknown_acceptance["state"] == "unknown"
    assert "failover-acceptance-security-unknown" in unknown_acceptance["blockerCodes"]

    store = persistence.EverkeepStore()
    extension = governance_service.FailoverGovernanceStoreExtension(store)
    extension.save_approval(approved)
    assert extension.get_approval(approved["approvalId"])["planDigest"] == digest
    assert extension.list_approvals(plan["planId"])[0]["approvalId"] == approved["approvalId"]
    extension.save_acceptance(acceptance)
    assert extension.get_acceptance(acceptance["acceptanceId"])["state"] == "pass"
    assert extension.list_acceptance_for_plan(plan["planId"])[0]["executionId"] == execution["executionId"]

    try:
        extension.save_approval(approved)
        raise AssertionError("duplicate approval should fail")
    except ValueError:
        pass
    try:
        extension.save_acceptance(acceptance)
        raise AssertionError("duplicate acceptance should fail")
    except ValueError:
        pass

    resources = [
        {
            "resourceId": "documents:primary", "protected": True, "readiness": "Recovery Ready",
            "recoveryEligible": True, "integrityCurrent": True, "restoreTestCurrent": True,
            "policyCompliant": True, "continuityState": "ready", "rpoCompliant": True,
            "rtoCompliant": True, "recoveryExerciseCurrent": True, "failureDomainDiverse": True,
            "topologyCurrent": True, "assuranceScheduleState": "scheduled", "failoverEligible": True,
            "failoverPlanState": "ready-for-approval", "failoverApprovalState": "approved", "blockers": [],
        },
        {
            "resourceId": "photos:primary", "protected": True, "readiness": "Recovery Ready",
            "recoveryEligible": True, "integrityCurrent": True, "restoreTestCurrent": True,
            "policyCompliant": True, "continuityState": "ready", "rpoCompliant": True,
            "rtoCompliant": True, "recoveryExerciseCurrent": True, "failureDomainDiverse": True,
            "topologyCurrent": True, "assuranceScheduleState": "scheduled", "failoverEligible": True,
            "failoverPlanState": "ready-for-approval", "failoverApprovalState": "expired", "blockers": [],
        },
        {
            "resourceId": "vault:primary", "protected": True, "readiness": "At Risk",
            "recoveryEligible": False, "integrityCurrent": True, "restoreTestCurrent": True,
            "policyCompliant": True, "continuityState": "attention", "rpoCompliant": True,
            "rtoCompliant": True, "recoveryExerciseCurrent": True, "failureDomainDiverse": True,
            "topologyCurrent": True, "assuranceScheduleState": "scheduled", "failoverEligible": False,
            "failoverPlanState": "ready-for-approval", "failoverApprovalState": "denied",
            "failoverExecutionState": "completed", "failoverAcceptanceState": "fail", "blockers": [],
        },
        {
            "resourceId": "music:primary", "protected": True, "readiness": "Recovery Ready",
            "recoveryEligible": True, "integrityCurrent": True, "restoreTestCurrent": True,
            "policyCompliant": True, "blockers": [],
        },
    ]
    summary = recovery_center.build_summary(resources, "2026-08-27T12:25:00Z")
    assert summary["schemaVersion"] == "1.5"
    assert summary["failoverGovernance"]["approval"] == {
        "approved": 1, "denied": 1, "expired": 1, "unknown": 0, "not-applicable": 1
    }
    assert summary["failoverGovernance"]["acceptance"] == {
        "pass": 0, "fail": 1, "unknown": 0, "not-applicable": 3
    }
    actions = {(item["resourceId"], item["action"]) for item in summary["recommendedActions"]}
    assert ("photos:primary", "review-failover-approval") in actions
    assert ("vault:primary", "inspect-failover-denial") in actions
    assert ("vault:primary", "evaluate-failover-acceptance") in actions
    assert ("documents:primary", "review-failover-approval") not in actions
    assert all(action != "execute-failover" for _, action in actions)

    for filename in ["everkeep.failover-approval.schema.json", "everkeep.failover-acceptance.schema.json"]:
        contract = json.loads((ROOT / "contracts" / filename).read_text())
        assert contract["properties"]["schemaVersion"]["const"] == "1.0"
    approval_contract = json.loads((ROOT / "contracts" / "everkeep.failover-approval.schema.json").read_text())
    assert approval_contract["properties"]["executionAuthorized"]["const"] is False
    assert approval_contract["properties"]["executionCredential"]["const"] is False
    assert approval_contract["properties"]["sourceMutationAllowed"]["const"] is False
    acceptance_contract = json.loads((ROOT / "contracts" / "everkeep.failover-acceptance.schema.json").read_text())
    assert acceptance_contract["properties"]["productionMutationAuthorized"]["const"] is False

    summary_contract = json.loads((ROOT / "contracts" / "everkeep.recovery-center.summary.schema.json").read_text())
    assert summary_contract["properties"]["schemaVersion"]["const"] == "1.5"
    assert "failoverGovernance" in summary_contract["required"]
    action_contract = json.loads((ROOT / "contracts" / "everkeep.recovery-action.schema.json").read_text())
    for action in ["review-failover-approval", "inspect-failover-denial", "evaluate-failover-acceptance"]:
        assert action in action_contract["properties"]["action"]["enum"]
    assert "execute-failover" not in action_contract["properties"]["action"]["enum"]

    migration = (ROOT / "db" / "postgres" / "006_failover_governance.sql").read_text()
    for phrase in [
        "everkeep_failover_approvals", "everkeep_failover_acceptance",
        "execution_authorized = false", "execution_credential = false",
        "source_mutation_allowed = false", "production_mutation_authorized = false",
    ]:
        assert phrase in migration

    docs = (ROOT / "docs" / "PHASE-3-FAILOVER-GOVERNANCE.md").read_text()
    for phrase in [
        "canonical SHA-256", "executionAuthorized: false", "executionCredential: false",
        "exact deployed revision", "Recovery Center 1.5", "no `execute-failover` action",
        "GoreeCloud Identity", "Privacy Shield", "Wardveil Security", "Glaze UI",
    ]:
        assert phrase in docs

    print("Everkeep Phase 3 failover governance validation passed")


if __name__ == "__main__":
    main()
