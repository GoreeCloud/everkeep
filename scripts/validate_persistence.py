#!/usr/bin/env python3
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
import importlib.util

ROOT = Path(__file__).resolve().parents[1]


def load_store():
    path = ROOT / "scripts" / "persistent_service.py"
    spec = importlib.util.spec_from_file_location("persistent_service", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def schema(path, required):
    data = json.loads(path.read_text())
    assert data["type"] == "object"
    assert set(required).issubset(set(data.get("required", [])))


def main():
    contracts = ROOT / "contracts"
    schema(contracts / "everkeep.persistence.schema.json", {"schemaVersion", "engine", "tables", "transactional"})
    schema(contracts / "everkeep.adapter.schema.json", {"schemaVersion", "adapterId", "application", "resourceClasses", "capabilities", "eventCursor"})

    mod = load_store()
    with NamedTemporaryFile(suffix=".db") as tmp:
        store = mod.EverkeepStore(tmp.name)
        resource = {"resourceId": "doc:1", "application": "goreecloud-documents", "preservationTier": "protected"}
        store.register_resource(resource)
        try:
            store.register_resource(resource)
            raise AssertionError("duplicate resource accepted")
        except ValueError:
            pass

        p1 = {"policyId": "policy:default", "name": "Default"}
        p2 = {"policyId": "policy:default", "name": "Default v2"}
        assert store.save_policy(p1) == 1
        assert store.save_policy(p2) == 2
        assert store.get_policy("policy:default")["name"] == "Default v2"
        assert store.get_policy("policy:default", 1)["name"] == "Default"

        rp = {"recoveryPointId": "rp:1", "resourceId": "doc:1", "state": "available"}
        store.ingest_recovery_point(rp)
        assert store.transition_recovery_point("rp:1", "verifying") == "verifying"
        assert store.transition_recovery_point("rp:1", "available") == "available"
        try:
            store.transition_recovery_point("rp:1", "expired")
            store.transition_recovery_point("rp:1", "available")
            raise AssertionError("terminal recovery point transition accepted")
        except ValueError:
            pass

        store.record_retention_decision("doc:1", {"decision": "retain", "reason": "policy"})
        projection = store.recovery_center_projection("doc:1")
        assert projection["resource"]["resourceId"] == "doc:1"
        assert projection["retentionDecision"]["decision"] == "retain"
        assert projection["auditSequence"] > 0

        page = store.list_resources(limit=1)
        assert page["total"] == 1 and len(page["items"]) == 1
        store.set_adapter_state("documents", "cursor:10", {"lastEvent": 10})
        assert len(store.audit_events()) >= 5

    print("Everkeep persistent service validation passed")


if __name__ == "__main__":
    main()
