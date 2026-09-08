#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "acceptance" / "goreecloud-care.0.1.0.prequalification.json"

EXPECTED_SOURCE = "bbc4779454c2887b810aa0ddc9e8a686a4c68ebd"
EXPECTED_TREE = "ebe028347c978b6d09fb1d2af011729249f63bc3"
EXPECTED_PACKAGE_SHA = "819cff6e0132bf6b09df0986682995c25b14c39e74982f725efd0b5a21b71160"
EXPECTED_PREDECESSOR_EVERKEEP = "d6192dc2a38d5749df561f0638860c974faae8ff"
EXPECTED_PREDECESSOR_CARE = "334b53102c5fe0bd5d348397ba8b13cc5608ada2"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Care Everkeep prequalification invalid: {message}")


def immutable_sha(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def main() -> None:
    require(RECORD.is_file(), "missing prequalification record")
    record = json.loads(RECORD.read_text(encoding="utf-8"))

    require(record.get("schema_version") == 1, "unexpected schema version")
    require(record.get("record_type") == "care-continuity-prequalification", "unexpected record type")
    require(record.get("application") == "GoreeCloud Care", "unexpected application")
    require(record.get("producer") == "GoreeCloud/goreecloud-zorin-os/apps/goreecloud-care", "unexpected producer")

    candidate = record.get("candidate") or {}
    require(candidate.get("source_revision") == EXPECTED_SOURCE, "candidate source mismatch")
    require(candidate.get("source_tree") == EXPECTED_TREE, "candidate tree mismatch")
    require(candidate.get("runtime_version") == "0.1.0", "unexpected runtime version")
    require(candidate.get("package_version") == "0.1.0", "unexpected package version")
    require(candidate.get("package_sha256") == EXPECTED_PACKAGE_SHA, "candidate package SHA mismatch")
    require(immutable_sha(candidate.get("source_revision")), "source revision must be immutable")
    require(immutable_sha(candidate.get("source_tree")), "source tree must be immutable")
    require(sha256(candidate.get("package_sha256")), "package SHA-256 must be explicit")

    target = record.get("target") or {}
    require(target.get("name") == "Zorin OS 17.3 representative laptop", "unexpected target")
    require(target.get("representative") is True, "target must be representative")
    require(target.get("status") == "pending", "target must remain pending before physical acceptance")

    dimensions = set(record.get("dimensions") or [])
    require({"restore_capability", "migration", "documentation", "provenance"} <= dimensions, "required continuity dimensions missing")

    automated = record.get("automated_prequalification") or {}
    for key in (
        "care_ci_run_id",
        "care_ci_run_number",
        "care_test_count",
        "platform_contract_run_id",
        "primary_artifact_id",
        "cross_environment_artifact_id",
    ):
        require(positive_int(automated.get(key)), f"missing positive integer evidence: {key}")
    require(automated.get("care_ci_run_id") == 34180765807, "unexpected Care CI run")
    require(automated.get("care_ci_run_number") == 421, "unexpected Care CI run number")
    require(automated.get("care_test_count", 0) >= 143, "143-test checkpoint missing")
    require(automated.get("platform_contract_run_id") == 34180766156, "unexpected Platform Contract run")
    require(automated.get("primary_artifact_id") == 10038827656, "unexpected primary artifact")
    require(automated.get("cross_environment_artifact_id") == 10038821545, "unexpected cross-environment artifact")
    require(sha256(automated.get("primary_artifact_digest")), "invalid primary artifact digest")
    require(sha256(automated.get("cross_environment_artifact_digest")), "invalid cross-environment artifact digest")
    for key in (
        "source_validation",
        "same_environment_reproducibility",
        "cross_umask_package_identity",
        "cross_environment_package_identity",
        "package_lifecycle_prequalification",
        "same_version_exact_package_reinstall",
    ):
        require(automated.get(key) == "passed", f"automated evidence must remain passed: {key}")
    require(automated.get("rollback_package") == "0.1.0~dev17", "rollback package must remain the accepted dev17 checkpoint")
    require(automated.get("care_cleanup_invoked") is False, "prequalification must not invoke Care cleanup")

    acceptance = record.get("acceptance") or {}
    require(acceptance.get("target_runtime_status") == "pending", "target runtime must remain pending")
    require(acceptance.get("exact_revision_accepted") is False, "exact revision must not be accepted before physical target evidence")
    require(acceptance.get("everkeep_integration_promoted") is False, "Everkeep integration must not self-promote")
    require(acceptance.get("everkeep_ready_promoted") is False, "Everkeep ready must not self-promote")
    require(acceptance.get("local_governance_record_installed") is False, "local governance install must remain false")
    require(acceptance.get("local_continuity_expected_state") == "attention", "continuity must remain fail-closed before governance")
    require(acceptance.get("stable_promotion_authorized") is False, "Stable promotion must remain unauthorized")

    requirements = record.get("remaining_requirements") or []
    require(isinstance(requirements, list) and len(requirements) >= 6, "remaining continuity requirements must remain explicit")
    joined = "\n".join(str(item).lower() for item in requirements)
    for token in (
        "zorin os 17.3",
        "representative target handoff",
        "separate everkeep governance record",
        "/var/lib/goreecloud/everkeep/acceptance",
        "ready / everkeep-promoted",
        "stable promotion",
    ):
        require(token in joined, f"missing remaining requirement: {token}")

    predecessor = record.get("predecessor_authority") or {}
    require(predecessor.get("everkeep_revision") == EXPECTED_PREDECESSOR_EVERKEEP, "unexpected predecessor Everkeep authority")
    require(predecessor.get("care_revision") == EXPECTED_PREDECESSOR_CARE, "unexpected predecessor Care authority")
    require(predecessor.get("historical_only") is True, "predecessor authority must be historical only")

    print("Care Everkeep exact-candidate prequalification: passed")
    print("Representative target: pending")
    print("Everkeep integration promoted: false")
    print("Everkeep ready promoted: false")
    print("Local governance installed: false")


if __name__ == "__main__":
    main()
