#!/usr/bin/env python3
import json
import sys
from pathlib import Path

REQUIRED_CHECKS = [
    "protectionFresh",
    "integrityVerified",
    "policyCompliant",
    "restoreTestFresh",
    "dependenciesReady",
    "keysReady",
    "copyRequirementsMet",
]

WEIGHTS = {
    "protectionFresh": 20,
    "integrityVerified": 20,
    "policyCompliant": 15,
    "restoreTestFresh": 15,
    "dependenciesReady": 10,
    "keysReady": 10,
    "copyRequirementsMet": 10,
}

HARD_BLOCKERS = {"integrityVerified", "policyCompliant", "keysReady"}


def evaluate(payload):
    checks = payload.get("checks", {})
    missing = [name for name in REQUIRED_CHECKS if name not in checks]
    if missing:
        return {"state": "unknown", "score": 0, "blockingReasons": [f"missing:{x}" for x in missing]}

    score = sum(WEIGHTS[name] for name in REQUIRED_CHECKS if checks[name] is True)
    failed = [name for name in REQUIRED_CHECKS if checks[name] is not True]
    hard = [name for name in failed if name in HARD_BLOCKERS]

    if hard:
        state = "recovery_blocked"
    elif not failed:
        state = "recovery_ready"
    else:
        state = "at_risk"

    return {"state": state, "score": score, "blockingReasons": failed}


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: evaluate_readiness.py <input.json>")
    payload = json.loads(Path(sys.argv[1]).read_text())
    result = evaluate(payload)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
