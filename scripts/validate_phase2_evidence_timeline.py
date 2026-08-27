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
    mod = load("evidence_timeline", ROOT / "scripts" / "evidence_timeline.py")
    records = [
        {"resourceId": "doc:1", "evidenceId": "e:1", "category": "integrity", "observedAt": "2026-08-27T10:00:00Z", "state": "pass", "current": False, "summary": "Older integrity verification passed.", "evidenceRef": "ref:1", "producer": "everkeep"},
        {"resourceId": "doc:1", "evidenceId": "e:2", "category": "integrity", "observedAt": "2026-08-27T11:00:00Z", "state": "fail", "current": True, "summary": "Latest integrity verification failed.", "evidenceRef": "ref:2", "producer": "everkeep"},
        {"resourceId": "doc:1", "evidenceId": "e:3", "category": "restore-test", "observedAt": "2026-08-27T09:00:00Z", "state": "pass", "current": True, "summary": "Restore test passed.", "evidenceRef": "ref:3", "producer": "everkeep", "recoveryPointId": "rp:1"},
        {"resourceId": "other", "evidenceId": "e:4", "category": "policy", "observedAt": "2026-08-27T12:00:00Z", "state": "pass", "current": True, "summary": "Other resource.", "evidenceRef": "ref:4"},
        {"resourceId": "doc:1", "evidenceId": "e:5", "category": "unexpected", "observedAt": "2026-08-27T08:00:00Z", "state": "unexpected", "current": True, "summary": "Malformed producer state is conservative.", "evidenceRef": "ref:5"},
    ]
    timeline = mod.build_timeline("doc:1", records, "2026-08-27T12:30:00Z")
    assert timeline["counts"] == {"total": 4, "pass": 2, "fail": 1, "unknown": 1, "info": 0}
    assert timeline["items"][0]["evidenceId"] == "e:2"
    assert timeline["latestByCategory"]["integrity"]["state"] == "fail"
    assert timeline["latestByCategory"]["restore-test"]["state"] == "pass"
    assert timeline["latestByCategory"]["other"]["state"] == "unknown"

    try:
        mod.build_timeline("doc:1", [{"resourceId": "doc:1", "observedAt": "2026-08-27T00:00:00Z"}])
    except ValueError:
        pass
    else:
        raise AssertionError("unattributed timeline evidence must fail closed")

    schema = json.loads((ROOT / "contracts" / "everkeep.evidence-timeline.schema.json").read_text())
    assert schema["properties"]["schemaVersion"]["const"] == "1.0"
    migration = (ROOT / "db" / "postgres" / "003_assurance_succession.sql").read_text()
    assert "everkeep_evidence_observations" in migration
    openapi = (ROOT / "api" / "openapi.yaml").read_text()
    assert "/v1/resources/{resourceId}/evidence-timeline:" in openapi
    docs = (ROOT / "docs" / "PHASE-2-EVIDENCE-TIMELINE.md").read_text()
    for phrase in ["current evidence", "Historical evidence", "color", "fail closed"]:
        assert phrase in docs

    print("Everkeep Phase 2 evidence timeline validation passed")


if __name__ == "__main__":
    main()
