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
    mod = load("live_acceptance", ROOT / "scripts" / "live_acceptance.py")
    passed = [mod.AcceptanceCheck(name, "pass", True, {"verified": True}) for name in mod.REQUIRED_CHECKS]
    assert mod.evaluate(passed, "staging", "abcdef1")["accepted"] is True

    incomplete = passed[:-1]
    assert mod.evaluate(incomplete, "staging", "abcdef1")["accepted"] is False

    denied = list(passed)
    denied[0] = mod.AcceptanceCheck(denied[0].name, "fail", True, {"verified": True})
    assert mod.evaluate(denied, "staging", "abcdef1")["accepted"] is False

    unauth = list(passed)
    unauth[0] = mod.AcceptanceCheck(unauth[0].name, "pass", False, {"verified": False})
    assert mod.evaluate(unauth, "staging", "abcdef1")["accepted"] is False

    schema = json.loads((ROOT / "contracts" / "everkeep.live-acceptance.schema.json").read_text())
    assert "accepted" in schema["required"]
    assert set(schema["properties"]["environment"]["enum"]) == {"staging", "production"}

    runbook = (ROOT / "docs" / "LIVE-ACCEPTANCE.md").read_text()
    for required in ["Identity", "Privacy Shield", "Wardveil", "Mesh", "cursor", "restart", "authoritative"]:
        assert required in runbook

    print("Everkeep live acceptance validation passed")


if __name__ == "__main__":
    main()
