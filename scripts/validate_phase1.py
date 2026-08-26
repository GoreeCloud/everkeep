#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_evaluator():
    path = ROOT / "scripts" / "evaluate_readiness.py"
    spec = importlib.util.spec_from_file_location("evaluate_readiness", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_schema_shape(path, required_keys):
    data = json.loads(path.read_text())
    assert data.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
    assert data.get("type") == "object"
    required = set(data.get("required", []))
    missing = set(required_keys) - required
    assert not missing, f"{path.name} missing required schema keys: {sorted(missing)}"


def main():
    contracts = ROOT / "contracts"
    assert_schema_shape(contracts / "everkeep.mesh.request.schema.json", {"schemaVersion", "requestId", "operation", "resourceId", "requestedAt", "actor"})
    assert_schema_shape(contracts / "everkeep.mesh.event.schema.json", {"schemaVersion", "eventId", "eventType", "resourceId", "occurredAt", "status"})
    assert_schema_shape(contracts / "everkeep.readiness.schema.json", {"schemaVersion", "resourceId", "evaluatedAt", "state", "score", "checks"})

    evaluator = load_evaluator()
    fixtures = {
        "recovery-ready.json": ("recovery_ready", 100),
        "at-risk.json": ("at_risk", 85),
        "recovery-blocked.json": ("recovery_blocked", 80),
    }
    for name, expected in fixtures.items():
        payload = json.loads((ROOT / "examples" / "readiness" / name).read_text())
        result = evaluator.evaluate(payload)
        actual = (result["state"], result["score"])
        assert actual == expected, f"{name}: expected {expected}, got {actual}"

    unknown = evaluator.evaluate({"checks": {"protectionFresh": True}})
    assert unknown["state"] == "unknown" and unknown["score"] == 0

    print("Everkeep Phase 1 Mesh/readiness validation passed")


if __name__ == "__main__":
    main()
