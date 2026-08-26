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
    mod = load("staging_verify", ROOT / "scripts" / "staging_verify.py")
    passed = [mod.Check("a", "pass", True), mod.Check("b", "pass", True)]
    evidence = mod.build_evidence(passed)
    assert evidence["operational"] is True

    for checks in [
        [mod.Check("a", "unknown", True)],
        [mod.Check("a", "fail", True)],
        [mod.Check("a", "pass", False)],
        [],
    ]:
        assert mod.build_evidence(checks)["operational"] is False

    schema = json.loads((ROOT / "contracts" / "everkeep.staging-evidence.schema.json").read_text())
    assert schema["properties"]["environment"]["const"] == "staging"
    assert set(schema["required"]) == {"schemaVersion", "environment", "capturedAt", "checks", "operational"}

    script = (ROOT / "scripts" / "staging_verify.py").read_text()
    for required in [
        "EVERKEEP_POSTGRES_DSN",
        "EVERKEEP_IDENTITY_ENDPOINT",
        "EVERKEEP_PRIVACY_ENDPOINT",
        "EVERKEEP_WARDVEIL_ENDPOINT",
        "EVERKEEP_MESH_ENDPOINT",
        "status == \"pass\" and c.authoritative",
    ]:
        assert required in script

    runbook = (ROOT / "docs" / "STAGING-VERIFICATION.md").read_text()
    for required in ["PostgreSQL", "GoreeCloud Identity", "Privacy Shield", "Wardveil Security", "GoreeCloud Mesh", "operational"]:
        assert required in runbook

    print("Everkeep staging verification validation passed")


if __name__ == "__main__":
    main()
