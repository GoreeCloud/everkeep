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
    mod = load("succession", ROOT / "scripts" / "succession.py")
    policy = {
        "schemaVersion": "1.0",
        "policyId": "succession:1",
        "ownerSubject": "identity:user:owner",
        "status": "active",
        "createdAt": "2026-01-01T00:00:00Z",
        "rules": [
            {"ruleId": "rule:transfer", "resourceIds": ["photo:1"], "disposition": "transfer", "successorRefs": ["identity:user:successor"]},
            {"ruleId": "rule:delete", "resourceIds": ["vault:1"], "disposition": "delete", "successorRefs": []},
        ],
        "activation": {
            "waitingPeriodSeconds": 86400,
            "trustedContactQuorum": 2,
            "requiredSignals": ["owner-status-confirmed"],
        },
    }
    required = set(mod.required_signals(policy))
    assert required == {"privacy-authorized", "wardveil-clear", "successor-verified", "destruction-authorized", "trusted-contact-quorum", "owner-status-confirmed"}

    signals = {name: {"state": "pass", "evidenceRef": f"evidence:{name}"} for name in required}
    eligible = mod.evaluate(policy, signals, "decision:1", "2026-08-27T12:00:00Z", "2026-08-25T12:00:00Z")
    assert eligible["state"] == "eligible"
    assert eligible["activationEligible"] is True
    assert eligible["executionAuthorized"] is False

    too_early = mod.evaluate(policy, signals, "decision:2", "2026-08-25T18:00:00Z", "2026-08-25T12:00:00Z")
    assert too_early["state"] == "blocked"
    assert "waiting-period:pending" in too_early["blockers"]

    missing_privacy = dict(signals)
    missing_privacy.pop("privacy-authorized")
    unknown = mod.evaluate(policy, missing_privacy, "decision:3", "2026-08-27T12:00:00Z", "2026-08-25T12:00:00Z")
    assert unknown["state"] == "unknown"
    assert unknown["activationEligible"] is False
    assert "signal:privacy-authorized:unknown" in unknown["blockers"]

    rejected_security = dict(signals)
    rejected_security["wardveil-clear"] = {"state": "fail", "evidenceRef": "evidence:wardveil:block"}
    blocked = mod.evaluate(policy, rejected_security, "decision:4", "2026-08-27T12:00:00Z", "2026-08-25T12:00:00Z")
    assert blocked["state"] == "blocked"
    assert blocked["activationEligible"] is False

    inactive = mod.evaluate(policy | {"status": "draft"}, signals, "decision:5", "2026-08-27T12:00:00Z", "2026-08-25T12:00:00Z")
    assert inactive["state"] == "inactive"
    no_event = mod.evaluate(policy, signals, "decision:6", "2026-08-27T12:00:00Z")
    assert no_event["state"] == "inactive"
    revoked = mod.evaluate(policy | {"status": "revoked"}, signals, "decision:7", "2026-08-27T12:00:00Z", "2026-08-25T12:00:00Z")
    assert revoked["state"] == "revoked"

    policy_schema = json.loads((ROOT / "contracts" / "everkeep.succession-policy.schema.json").read_text())
    decision_schema = json.loads((ROOT / "contracts" / "everkeep.succession-decision.schema.json").read_text())
    assert policy_schema["properties"]["status"]["enum"][-1] == "revoked"
    assert decision_schema["properties"]["executionAuthorized"]["const"] is False

    migration = (ROOT / "db" / "postgres" / "003_assurance_succession.sql").read_text()
    for table in ["everkeep_succession_policies", "everkeep_succession_decisions"]:
        assert table in migration
    openapi = (ROOT / "api" / "openapi.yaml").read_text()
    for route in ["/v1/succession/policies:", "/v1/succession/policies/{successionPolicyId}/evaluate:"]:
        assert route in openapi

    docs = (ROOT / "docs" / "PHASE-2-SUCCESSION.md").read_text()
    for phrase in ["GoreeCloud Identity", "Privacy Shield", "Wardveil Security", "waiting period", "does not execute"]:
        assert phrase in docs

    print("Everkeep Phase 2 succession validation passed")


if __name__ == "__main__":
    main()
