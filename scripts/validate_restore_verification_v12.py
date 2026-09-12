#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts" / "everkeep.restore-verification.v1.2.schema.json"
DOC = ROOT / "docs" / "RESTORE-VERIFICATION-V1.2.md"
HEX40 = set("0123456789abcdef")
MAX_EVIDENCE_REFERENCE_LENGTH = 1024


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def exact_sha(value: object, length: int) -> bool:
    return isinstance(value, str) and len(value) == length and set(value) <= HEX40


def bounded_reference(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or len(normalized) > MAX_EVIDENCE_REFERENCE_LENGTH:
        return None
    return normalized


def consumer_accepts_v12(
    record: dict,
    *,
    expected_environment_id: str,
    expected_resource_id: str,
    expected_target_revision: str,
    expected_everkeep_revision: str,
    expected_everkeep_tree: str,
    now: datetime,
) -> bool:
    if record.get("schemaVersion") != "1.2":
        return False
    if record.get("environment") != "isolated":
        return False
    if record.get("environmentId") != expected_environment_id:
        return False
    if record.get("status") != "pass" or record.get("authoritative") is not True:
        return False
    if record.get("externalAuthorityTransferred") is not False:
        return False
    if record.get("everkeepSourceRevision") != expected_everkeep_revision:
        return False
    if record.get("everkeepSourceTree") != expected_everkeep_tree:
        return False
    if not exact_sha(record.get("everkeepSourceRevision"), 40) or not exact_sha(record.get("everkeepSourceTree"), 40):
        return False

    target = record.get("target")
    recovery_point = record.get("recoveryPoint")
    execution = record.get("execution")
    if not isinstance(target, dict) or not isinstance(recovery_point, dict) or not isinstance(execution, dict):
        return False
    if target.get("resourceId") != expected_resource_id:
        return False
    if target.get("deployedRevision") != expected_target_revision or not exact_sha(target.get("deployedRevision"), 40):
        return False
    recovery_point_id = recovery_point.get("id")
    if not isinstance(recovery_point_id, str) or not recovery_point_id.strip():
        return False
    if not exact_sha(recovery_point.get("artifactSha256"), 64):
        return False
    if execution.get("mode") != "real_isolated_restore":
        return False
    if execution.get("sourceMutationAllowed") is not False:
        return False
    if execution.get("productionPromotionPerformed") is not False:
        return False
    if execution.get("integrityVerified") is not True or execution.get("restoredStateVerified") is not True:
        return False

    evidence_refs = record.get("evidenceRefs")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        return False
    normalized_evidence_refs: list[str] = []
    for value in evidence_refs:
        normalized = bounded_reference(value)
        if normalized is None:
            return False
        normalized_evidence_refs.append(normalized)
    if len(set(normalized_evidence_refs)) != len(normalized_evidence_refs):
        return False
    evidence_ref_set = set(normalized_evidence_refs)

    checks = execution.get("workloadChecks")
    if not isinstance(checks, list) or not checks:
        return False
    check_ids: set[str] = set()
    for check in checks:
        if not isinstance(check, dict):
            return False
        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id or check_id in check_ids:
            return False
        check_ids.add(check_id)
        if check.get("status") != "pass":
            return False
        check_evidence = bounded_reference(check.get("evidenceRef"))
        if check_evidence is None or check_evidence not in evidence_ref_set:
            return False

    produced = parse_timestamp(recovery_point.get("producedAt"))
    started = parse_timestamp(execution.get("startedAt"))
    completed = parse_timestamp(execution.get("completedAt"))
    captured = parse_timestamp(record.get("capturedAt"))
    fresh_until = parse_timestamp(record.get("freshUntil"))
    if None in (produced, started, completed, captured, fresh_until):
        return False
    if now.tzinfo is None or now.utcoffset() is None:
        return False
    current = now.astimezone(timezone.utc)
    return produced <= started < completed <= captured <= current <= fresh_until


def fixture() -> dict:
    return {
        "schemaVersion": "1.2",
        "verificationId": "isolated-restore-1",
        "environment": "isolated",
        "environmentId": "recovery-sandbox-1",
        "capturedAt": "2026-09-12T04:45:00Z",
        "freshUntil": "2026-09-13T04:45:00Z",
        "everkeepSourceRevision": "a" * 40,
        "everkeepSourceTree": "b" * 40,
        "target": {
            "system": "GoreeCloud Example",
            "component": "example-runtime",
            "resourceId": "resource-1",
            "deployedRevision": "c" * 40,
        },
        "recoveryPoint": {
            "id": "recovery-point-1",
            "artifactSha256": "d" * 64,
            "producedAt": "2026-09-12T04:00:00Z",
        },
        "execution": {
            "mode": "real_isolated_restore",
            "startedAt": "2026-09-12T04:10:00Z",
            "completedAt": "2026-09-12T04:40:00Z",
            "sourceMutationAllowed": False,
            "productionPromotionPerformed": False,
            "integrityVerified": True,
            "restoredStateVerified": True,
            "workloadChecks": [
                {"id": "service-start", "status": "pass", "evidenceRef": "evidence:service-start"},
                {"id": "data-integrity", "status": "pass", "evidenceRef": "evidence:data-integrity"},
            ],
        },
        "status": "pass",
        "authoritative": True,
        "evidenceRefs": [
            "evidence:restore-log",
            "evidence:artifact-digest",
            "evidence:service-start",
            "evidence:data-integrity",
        ],
        "externalAuthorityTransferred": False,
    }


def accepted(record: dict) -> bool:
    return consumer_accepts_v12(
        record,
        expected_environment_id="recovery-sandbox-1",
        expected_resource_id="resource-1",
        expected_target_revision="c" * 40,
        expected_everkeep_revision="a" * 40,
        expected_everkeep_tree="b" * 40,
        now=datetime(2026, 9, 12, 5, 0, tzinfo=timezone.utc),
    )


def main() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    require(schema.get("additionalProperties") is False, "v1.2 restore contract must be closed")
    require(schema["properties"]["schemaVersion"]["const"] == "1.2", "v1.2 schema version mismatch")
    require(schema["properties"]["environment"]["const"] == "isolated", "v1.2 must bind isolated environment")
    require(schema["properties"]["externalAuthorityTransferred"]["const"] is False, "external authority must not transfer")
    require(schema["properties"]["execution"]["properties"]["mode"]["const"] == "real_isolated_restore", "simulation must not satisfy v1.2")
    require(schema["properties"]["execution"]["properties"]["sourceMutationAllowed"]["const"] is False, "restore verification must preserve source")
    require(schema["properties"]["execution"]["properties"]["productionPromotionPerformed"]["const"] is False, "verification must not promote production")

    good = fixture()
    require(accepted(good), "valid exact isolated restore evidence must pass")

    mutations = []
    for path, value in (
        (("environmentId",), "other-sandbox"),
        (("everkeepSourceRevision",), "e" * 40),
        (("target", "deployedRevision"), "e" * 40),
        (("recoveryPoint", "id"), ""),
        (("execution", "mode"), "simulation"),
        (("execution", "integrityVerified"), False),
        (("execution", "restoredStateVerified"), False),
        (("execution", "sourceMutationAllowed"), True),
        (("externalAuthorityTransferred",), True),
    ):
        bad = json.loads(json.dumps(good))
        target = bad
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        mutations.append(bad)
    failed_check = json.loads(json.dumps(good))
    failed_check["execution"]["workloadChecks"][0]["status"] = "fail"
    mutations.append(failed_check)
    orphan_check_evidence = json.loads(json.dumps(good))
    orphan_check_evidence["execution"]["workloadChecks"][0]["evidenceRef"] = "evidence:not-in-manifest"
    mutations.append(orphan_check_evidence)
    malformed_evidence_manifest = json.loads(json.dumps(good))
    malformed_evidence_manifest["evidenceRefs"][0] = {"unexpected": "object"}
    mutations.append(malformed_evidence_manifest)
    duplicate_evidence_manifest = json.loads(json.dumps(good))
    duplicate_evidence_manifest["evidenceRefs"].append("evidence:service-start")
    mutations.append(duplicate_evidence_manifest)
    expired = json.loads(json.dumps(good))
    expired["freshUntil"] = "2026-09-12T04:50:00Z"
    mutations.append(expired)
    for bad in mutations:
        require(not accepted(bad), "invalid or weaker restore evidence must fail closed")

    for phrase in (
        "Backup Exists is not Recoverable",
        "real isolated restore",
        "exact recovery point artifact digest",
        "exact Everkeep source revision and tree",
        "exact deployed target revision",
        "simulation cannot satisfy this contract",
        "does not authorize production failover",
    ):
        require(phrase in doc, f"v1.2 restore documentation missing: {phrase}")

    print("Everkeep exact isolated restore verification v1.2 validation passed")


if __name__ == "__main__":
    main()
