#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts" / "everkeep.restore-verification.schema.json"
DOC = ROOT / "docs" / "RESTORE-VERIFICATION.md"


def require(condition: bool, message: str):
    if not condition:
        raise SystemExit(message)


def consumer_accepts(record: dict, environment: str, target_revision: str) -> bool:
    target = record.get("target", {})
    exercise = record.get("exercise", {})
    if record.get("environment") != environment:
        return False
    if record.get("status") != "pass" or record.get("authoritative") is not True:
        return False
    if target.get("deployedRevision") != target_revision:
        return False
    if target.get("system") != "Wardveil Security":
        return False
    if target.get("component") != "Cloudflare persistence runtime":
        return False
    if target.get("resourceId") != "goreecloud-wardveil-persistence":
        return False
    if exercise.get("isolatedVerification") is not True:
        return False
    if exercise.get("integrityVerified") is not True:
        return False
    if exercise.get("restoredStateVerified") is not True:
        return False
    if not record.get("evidenceRefs"):
        return False
    try:
        started = datetime.fromisoformat(exercise["startedAt"].replace("Z", "+00:00"))
        completed = datetime.fromisoformat(exercise["completedAt"].replace("Z", "+00:00"))
        captured = datetime.fromisoformat(record["capturedAt"].replace("Z", "+00:00"))
    except (KeyError, ValueError, TypeError):
        return False
    now = datetime.now(timezone.utc)
    return started < completed <= captured <= now


def main():
    schema = json.loads(SCHEMA.read_text())
    doc = DOC.read_text()

    required = set(schema["required"])
    for field in {"verificationId", "environment", "capturedAt", "everkeepSourceRevision", "target", "status", "authoritative", "exercise", "evidenceRefs"}:
        require(field in required, f"restore verification schema missing required field: {field}")

    target = schema["properties"]["target"]
    require(target["properties"]["deployedRevision"]["pattern"] == "^[0-9a-f]{40}$", "target revision must be exact SHA")
    require(schema["properties"]["securityStateAuthorityTransferred"]["const"] is False, "security authority must not transfer")

    exercise_required = set(schema["properties"]["exercise"]["required"])
    for field in {"recoveryPointId", "startedAt", "completedAt", "isolatedVerification", "integrityVerified", "restoredStateVerified", "promotionToProductionPerformed"}:
        require(field in exercise_required, f"restore exercise missing required field: {field}")

    revision = "a" * 40
    good = {
        "schemaVersion": "1.0",
        "verificationId": "restore-verification-test",
        "environment": "production",
        "capturedAt": "2026-08-26T21:30:00Z",
        "everkeepSourceRevision": "e246fb0e7c97a6f1da75188b25042b0611c57095",
        "target": {
            "system": "Wardveil Security",
            "component": "Cloudflare persistence runtime",
            "resourceId": "goreecloud-wardveil-persistence",
            "deployedRevision": revision,
        },
        "status": "pass",
        "authoritative": True,
        "exercise": {
            "recoveryPointId": "pitr-bookmark-test",
            "startedAt": "2026-08-26T21:00:00Z",
            "completedAt": "2026-08-26T21:20:00Z",
            "isolatedVerification": True,
            "integrityVerified": True,
            "restoredStateVerified": True,
            "promotionToProductionPerformed": False,
        },
        "evidenceRefs": ["everkeep:test:restore"],
        "securityStateAuthorityTransferred": False,
    }
    require(consumer_accepts(good, "production", revision), "valid restore evidence must satisfy consumer gate")

    for field, value in [("status", "fail"), ("authoritative", False)]:
        bad = dict(good)
        bad[field] = value
        require(not consumer_accepts(bad, "production", revision), f"consumer must reject {field}={value}")

    mismatch = json.loads(json.dumps(good))
    mismatch["target"]["deployedRevision"] = "b" * 40
    require(not consumer_accepts(mismatch, "production", revision), "consumer must reject revision mismatch")

    unverified = json.loads(json.dumps(good))
    unverified["exercise"]["restoredStateVerified"] = False
    require(not consumer_accepts(unverified, "production", revision), "consumer must reject unverified restored state")

    for phrase in [
        "PITR availability remains recovery-capability evidence only",
        "Everkeep remains the resilience, backup, restore, and recovery-verification authority",
        "securityStateAuthorityTransferred=false",
        "Wardveil Security may consume",
    ]:
        require(phrase in doc, f"restore verification documentation missing: {phrase}")

    print("Everkeep restore verification contract validation passed")


if __name__ == "__main__":
    main()
