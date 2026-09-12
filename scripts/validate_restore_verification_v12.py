#!/usr/bin/env python3
from __future__ import annotations

import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts" / "everkeep.restore-verification.v1.2.schema.json"
DOC = ROOT / "docs" / "RESTORE-VERIFICATION-V1.2.md"
HEX40 = set("0123456789abcdef")
MAX_EVIDENCE_REFERENCE_LENGTH = 1000
MAX_EVIDENCE_REFERENCES = 256
TOP_LEVEL_FIELDS = {
    "schemaVersion",
    "verificationId",
    "environment",
    "environmentId",
    "capturedAt",
    "freshUntil",
    "everkeepSourceRevision",
    "everkeepSourceTree",
    "target",
    "recoveryPoint",
    "execution",
    "status",
    "authoritative",
    "evidenceRefs",
    "externalAuthorityTransferred",
}
TARGET_FIELDS = {"system", "component", "resourceId", "deployedRevision"}
RECOVERY_POINT_FIELDS = {"id", "artifactSha256", "producedAt"}
EXECUTION_FIELDS = {
    "mode",
    "startedAt",
    "completedAt",
    "sourceMutationAllowed",
    "productionPromotionPerformed",
    "integrityVerified",
    "restoredStateVerified",
    "workloadChecks",
}
WORKLOAD_CHECK_FIELDS = {"id", "status", "evidenceRef"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value or value != value.strip():
        return None
    if any(unicodedata.category(char).startswith("C") for char in value):
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


def bounded_text(value: object, maximum: int) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or normalized != value or len(value) > maximum:
        return None
    if any(unicodedata.category(char).startswith("C") for char in value):
        return None
    return value


def bounded_reference(value: object) -> str | None:
    return bounded_text(value, MAX_EVIDENCE_REFERENCE_LENGTH)


def closed_shape(value: object, fields: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == fields


def consumer_accepts_v12(
    record: dict,
    *,
    expected_environment_id: str,
    expected_resource_id: str,
    expected_target_revision: str,
    expected_everkeep_revision: str,
    expected_everkeep_tree: str,
    expected_recovery_point_id: str,
    expected_artifact_sha256: str,
    now: datetime,
) -> bool:
    if not closed_shape(record, TOP_LEVEL_FIELDS):
        return False
    if record.get("schemaVersion") != "1.2":
        return False
    if bounded_text(record.get("verificationId"), 160) is None:
        return False
    if record.get("environment") != "isolated":
        return False
    if record.get("environmentId") != expected_environment_id:
        return False
    if bounded_text(record.get("environmentId"), 160) is None:
        return False
    if record.get("status") != "pass" or record.get("authoritative") is not True:
        return False
    if record.get("externalAuthorityTransferred") is not False:
        return False
    if record.get("everkeepSourceRevision") != expected_everkeep_revision:
        return False
    if record.get("everkeepSourceTree") != expected_everkeep_tree:
        return False
    if not exact_sha(record.get("everkeepSourceRevision"), 40) or not exact_sha(
        record.get("everkeepSourceTree"), 40
    ):
        return False

    target = record.get("target")
    recovery_point = record.get("recoveryPoint")
    execution = record.get("execution")
    if not closed_shape(target, TARGET_FIELDS):
        return False
    if not closed_shape(recovery_point, RECOVERY_POINT_FIELDS):
        return False
    if not closed_shape(execution, EXECUTION_FIELDS):
        return False
    if bounded_text(target.get("system"), 160) is None:
        return False
    if bounded_text(target.get("component"), 160) is None:
        return False
    if target.get("resourceId") != expected_resource_id:
        return False
    if bounded_text(target.get("resourceId"), 256) is None:
        return False
    if target.get("deployedRevision") != expected_target_revision or not exact_sha(
        target.get("deployedRevision"), 40
    ):
        return False
    recovery_point_id = bounded_text(recovery_point.get("id"), 256)
    if recovery_point_id is None or recovery_point_id != expected_recovery_point_id:
        return False
    artifact_sha256 = recovery_point.get("artifactSha256")
    if artifact_sha256 != expected_artifact_sha256 or not exact_sha(artifact_sha256, 64):
        return False
    if execution.get("mode") != "real_isolated_restore":
        return False
    if execution.get("sourceMutationAllowed") is not False:
        return False
    if execution.get("productionPromotionPerformed") is not False:
        return False
    if execution.get("integrityVerified") is not True or execution.get(
        "restoredStateVerified"
    ) is not True:
        return False

    evidence_refs = record.get("evidenceRefs")
    if (
        not isinstance(evidence_refs, list)
        or not evidence_refs
        or len(evidence_refs) > MAX_EVIDENCE_REFERENCES
    ):
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
    if not isinstance(checks, list) or not checks or len(checks) > 128:
        return False
    check_ids: set[str] = set()
    for check in checks:
        if not closed_shape(check, WORKLOAD_CHECK_FIELDS):
            return False
        check_id = bounded_text(check.get("id"), 160)
        if check_id is None or check_id in check_ids:
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
    return produced <= started < completed <= captured < fresh_until and captured <= current <= fresh_until


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
                {
                    "id": "service-start",
                    "status": "pass",
                    "evidenceRef": "evidence:service-start",
                },
                {
                    "id": "data-integrity",
                    "status": "pass",
                    "evidenceRef": "evidence:data-integrity",
                },
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
        expected_recovery_point_id="recovery-point-1",
        expected_artifact_sha256="d" * 64,
        now=datetime(2026, 9, 12, 5, 0, tzinfo=timezone.utc),
    )


def main() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    require(schema.get("additionalProperties") is False, "v1.2 restore contract must be closed")
    require(
        schema["properties"]["schemaVersion"]["const"] == "1.2",
        "v1.2 schema version mismatch",
    )
    require(
        schema["properties"]["environment"]["const"] == "isolated",
        "v1.2 must bind isolated environment",
    )
    require(
        schema["properties"]["externalAuthorityTransferred"]["const"] is False,
        "external authority must not transfer",
    )
    require(
        schema["properties"]["execution"]["properties"]["mode"]["const"]
        == "real_isolated_restore",
        "simulation must not satisfy v1.2",
    )
    require(
        schema["properties"]["execution"]["properties"]["sourceMutationAllowed"]["const"]
        is False,
        "restore verification must preserve source",
    )
    require(
        schema["properties"]["execution"]["properties"]["productionPromotionPerformed"]["const"]
        is False,
        "verification must not promote production",
    )
    require(
        schema["properties"]["evidenceRefs"]["maxItems"] == MAX_EVIDENCE_REFERENCES,
        "schema and consumer evidence-reference limits must match",
    )

    good = fixture()
    require(accepted(good), "valid exact isolated restore evidence must pass")

    mutations = []
    for path, value in (
        (("environmentId",), "other-sandbox"),
        (("everkeepSourceRevision",), "e" * 40),
        (("target", "deployedRevision"), "e" * 40),
        (("recoveryPoint", "id"), ""),
        (("recoveryPoint", "id"), "recovery-point-2"),
        (("recoveryPoint", "artifactSha256"), "e" * 64),
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
    orphan_check_evidence["execution"]["workloadChecks"][0]["evidenceRef"] = (
        "evidence:not-in-manifest"
    )
    mutations.append(orphan_check_evidence)
    malformed_evidence_manifest = json.loads(json.dumps(good))
    malformed_evidence_manifest["evidenceRefs"][0] = {"unexpected": "object"}
    mutations.append(malformed_evidence_manifest)
    duplicate_evidence_manifest = json.loads(json.dumps(good))
    duplicate_evidence_manifest["evidenceRefs"].append("evidence:service-start")
    mutations.append(duplicate_evidence_manifest)
    oversized_evidence_manifest = json.loads(json.dumps(good))
    oversized_evidence_manifest["evidenceRefs"] = [
        f"evidence:manifest:{index}" for index in range(MAX_EVIDENCE_REFERENCES + 1)
    ]
    oversized_evidence_manifest["evidenceRefs"].extend(
        ["evidence:service-start", "evidence:data-integrity"]
    )
    mutations.append(oversized_evidence_manifest)
    extra_top_level = json.loads(json.dumps(good))
    extra_top_level["productionReady"] = True
    mutations.append(extra_top_level)
    extra_target = json.loads(json.dumps(good))
    extra_target["target"]["authorityTransfer"] = True
    mutations.append(extra_target)
    extra_execution = json.loads(json.dumps(good))
    extra_execution["execution"]["directProductionWrite"] = True
    mutations.append(extra_execution)
    extra_workload_check = json.loads(json.dumps(good))
    extra_workload_check["execution"]["workloadChecks"][0]["accepted"] = True
    mutations.append(extra_workload_check)
    oversized_checks = json.loads(json.dumps(good))
    oversized_checks["execution"]["workloadChecks"] = [
        {
            "id": f"check-{index}",
            "status": "pass",
            "evidenceRef": "evidence:service-start",
        }
        for index in range(129)
    ]
    mutations.append(oversized_checks)
    for path, value in (
        (("verificationId",), " isolated-restore-1"),
        (("target", "system"), "GoreeCloud Example "),
        (("target", "component"), "example-runtime\n"),
        (("recoveryPoint", "id"), " recovery-point-1"),
        (("execution", "workloadChecks", 0, "id"), " service-start"),
        (("execution", "workloadChecks", 0, "evidenceRef"), "evidence:service-start "),
        (("evidenceRefs", 0), " evidence:restore-log"),
        (("capturedAt",), " 2026-09-12T04:45:00Z"),
        (("execution", "completedAt"), "2026-09-12T04:40:00Z\n"),
    ):
        bad = json.loads(json.dumps(good))
        target = bad
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        mutations.append(bad)
    zero_freshness = json.loads(json.dumps(good))
    zero_freshness["capturedAt"] = "2026-09-12T05:00:00Z"
    zero_freshness["freshUntil"] = "2026-09-12T05:00:00Z"
    mutations.append(zero_freshness)
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
