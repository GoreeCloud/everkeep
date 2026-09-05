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


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def consumer_accepts(
    record: dict,
    environment: str,
    target_revision: str,
    now: datetime | None = None,
) -> bool:
    target = record.get("target", {})
    exercise = record.get("exercise", {})
    if record.get("schemaVersion") != "1.1":
        return False
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

    started = parse_timestamp(exercise.get("startedAt"))
    completed = parse_timestamp(exercise.get("completedAt"))
    captured = parse_timestamp(record.get("capturedAt"))
    fresh_until = parse_timestamp(record.get("freshUntil"))
    if None in (started, completed, captured, fresh_until):
        return False

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        return False
    current = current.astimezone(timezone.utc)
    return started < completed <= captured < fresh_until and captured <= current <= fresh_until


def main():
    schema = json.loads(SCHEMA.read_text())
    doc = DOC.read_text()

    required = set(schema["required"])
    for field in {
        "verificationId",
        "environment",
        "capturedAt",
        "freshUntil",
        "everkeepSourceRevision",
        "target",
        "status",
        "authoritative",
        "exercise",
        "evidenceRefs",
    }:
        require(field in required, f"restore verification schema missing required field: {field}")

    require(schema["properties"]["schemaVersion"]["const"] == "1.1", "restore verification schema must be version 1.1")
    require(schema["properties"]["freshUntil"]["format"] == "date-time", "freshUntil must be a date-time")
    target = schema["properties"]["target"]
    require(target["properties"]["deployedRevision"]["pattern"] == "^[0-9a-f]{40}$", "target revision must be exact SHA")
    require(schema["properties"]["securityStateAuthorityTransferred"]["const"] is False, "security authority must not transfer")

    exercise_required = set(schema["properties"]["exercise"]["required"])
    for field in {"recoveryPointId", "startedAt", "completedAt", "isolatedVerification", "integrityVerified", "restoredStateVerified", "promotionToProductionPerformed"}:
        require(field in exercise_required, f"restore exercise missing required field: {field}")

    revision = "a" * 40
    fixed_now = datetime(2026, 9, 5, 16, 0, tzinfo=timezone.utc)
    good = {
        "schemaVersion": "1.1",
        "verificationId": "restore-verification-test",
        "environment": "production",
        "capturedAt": "2026-09-05T15:30:00Z",
        "freshUntil": "2026-09-06T15:30:00Z",
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
            "startedAt": "2026-09-05T15:00:00Z",
            "completedAt": "2026-09-05T15:20:00Z",
            "isolatedVerification": True,
            "integrityVerified": True,
            "restoredStateVerified": True,
            "promotionToProductionPerformed": False,
        },
        "evidenceRefs": ["everkeep:test:restore"],
        "securityStateAuthorityTransferred": False,
    }
    require(consumer_accepts(good, "production", revision, fixed_now), "valid fresh restore evidence must satisfy consumer gate")

    for field, value in [("status", "fail"), ("authoritative", False)]:
        bad = dict(good)
        bad[field] = value
        require(not consumer_accepts(bad, "production", revision, fixed_now), f"consumer must reject {field}={value}")

    mismatch = json.loads(json.dumps(good))
    mismatch["target"]["deployedRevision"] = "b" * 40
    require(not consumer_accepts(mismatch, "production", revision, fixed_now), "consumer must reject revision mismatch")

    unverified = json.loads(json.dumps(good))
    unverified["exercise"]["restoredStateVerified"] = False
    require(not consumer_accepts(unverified, "production", revision, fixed_now), "consumer must reject unverified restored state")

    expired = json.loads(json.dumps(good))
    expired["freshUntil"] = "2026-09-05T15:45:00Z"
    require(not consumer_accepts(expired, "production", revision, fixed_now), "consumer must reject expired restore evidence")

    missing_freshness = json.loads(json.dumps(good))
    del missing_freshness["freshUntil"]
    require(not consumer_accepts(missing_freshness, "production", revision, fixed_now), "consumer must reject restore evidence without freshness")

    future_capture = json.loads(json.dumps(good))
    future_capture["capturedAt"] = "2026-09-05T16:30:00Z"
    require(not consumer_accepts(future_capture, "production", revision, fixed_now), "consumer must reject future-captured restore evidence")

    naive_timestamp = json.loads(json.dumps(good))
    naive_timestamp["freshUntil"] = "2026-09-06T15:30:00"
    require(not consumer_accepts(naive_timestamp, "production", revision, fixed_now), "consumer must reject timezone-less freshness evidence")

    for phrase in [
        "PITR availability remains recovery-capability evidence only",
        "Everkeep remains the resilience, backup, restore, and recovery-verification authority",
        "securityStateAuthorityTransferred=false",
        "Wardveil Security may consume",
        "freshUntil",
    ]:
        require(phrase in doc, f"restore verification documentation missing: {phrase}")

    print("Everkeep restore verification contract validation passed")


if __name__ == "__main__":
    main()
