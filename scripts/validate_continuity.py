#!/usr/bin/env python3
"""Validate the Everkeep identity repository."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "continuity.identity.json"
STATUS_SCHEMA_PATH = ROOT / "contracts" / "continuity.status.schema.json"
ADOPTION_SCHEMA_PATH = ROOT / "contracts" / "continuity.adoption.schema.json"
ACCEPTANCE_SCHEMA_PATH = ROOT / "contracts" / "continuity.acceptance.schema.json"

EXPECTED_NAME = "Everkeep"
EXPECTED_SHORT = "Everkeep"
EXPECTED_STATES = ["ready", "attention", "degraded", "unknown", "not_applicable"]
EXPECTED_DIMENSIONS = [
    "backup_coverage",
    "restore_capability",
    "recovery_freshness",
    "portability",
    "migration",
    "dependency_recovery",
    "redundancy",
    "documentation",
    "ownership_custody",
    "succession",
    "preservation",
    "provenance",
]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path, label: str) -> dict:
    if not path.is_file():
        fail(f"missing {path.relative_to(ROOT)}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{label} is not valid JSON: {exc}")
    if not isinstance(value, dict):
        fail(f"{label} must contain a JSON object")
    return value


def validate_reference_adoption(path: Path, adoption_schema: dict) -> None:
    manifest = load_json(path, f"adoption manifest {path.name}")
    required = set(adoption_schema.get("required", []))
    if not required.issubset(manifest):
        fail(f"{path.name} is missing required adoption fields")

    properties = adoption_schema.get("properties", {})
    allowed_roles = set(properties.get("role", {}).get("enum", []))
    allowed_dimensions = set(properties.get("dimensions", {}).get("items", {}).get("enum", []))

    if manifest.get("schema_version") != 1:
        fail(f"{path.name} schema_version must be 1")
    if manifest.get("role") not in allowed_roles:
        fail(f"{path.name} has an unsupported adoption role")
    if manifest.get("read_only") is not True:
        fail(f"{path.name} must preserve the read-only Everkeep boundary")
    if manifest.get("fail_closed") is not True:
        fail(f"{path.name} must fail closed")
    if manifest.get("status_schema") != "contracts/continuity.status.schema.json":
        fail(f"{path.name} does not pin the canonical status schema")

    dimensions = manifest.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        fail(f"{path.name} must declare at least one continuity dimension")
    if len(dimensions) != len(set(dimensions)):
        fail(f"{path.name} contains duplicate continuity dimensions")
    if any(dimension not in allowed_dimensions for dimension in dimensions):
        fail(f"{path.name} declares an unsupported continuity dimension")


def validate_reference_acceptance(path: Path, acceptance_schema: dict) -> None:
    policy = load_json(path, f"acceptance policy {path.name}")
    required = set(acceptance_schema.get("required", []))
    if not required.issubset(policy):
        fail(f"{path.name} is missing required acceptance fields")
    if policy.get("schema_version") != 1:
        fail(f"{path.name} schema_version must be 1")
    if policy.get("status_schema") != "contracts/continuity.status.schema.json":
        fail(f"{path.name} does not pin the canonical status schema")

    freshness = policy.get("freshness", {})
    if freshness.get("required_for_ready") is not True:
        fail(f"{path.name} must require freshness before ready")
    rule = freshness.get("rule")
    if not isinstance(rule, str) or not rule.strip():
        fail(f"{path.name} must define a freshness rule")

    failure = policy.get("failure_behavior", {})
    non_ready = {"unknown", "degraded", "attention"}
    for key in (
        "producer_unavailable",
        "malformed_evidence",
        "missing_required_evidence",
        "failed_restore_validation",
    ):
        if failure.get(key) not in non_ready:
            fail(f"{path.name} {key} must fail to a non-ready state")
    summary_rule = failure.get("summary_rule", "")
    if "never be more favorable" not in summary_rule:
        fail(f"{path.name} must prevent optimistic summary state")

    ready_evidence = policy.get("required_ready_evidence")
    if not isinstance(ready_evidence, dict) or not ready_evidence:
        fail(f"{path.name} must map required ready evidence")
    if any(dimension not in EXPECTED_DIMENSIONS for dimension in ready_evidence):
        fail(f"{path.name} maps an unsupported continuity dimension")
    for dimension, evidence in ready_evidence.items():
        if not isinstance(evidence, list) or not evidence:
            fail(f"{path.name} {dimension} must require explicit evidence")

    forbidden = policy.get("sensitive_evidence", {}).get("forbidden")
    if not isinstance(forbidden, list) or not forbidden:
        fail(f"{path.name} must forbid sensitive evidence")
    normalized_forbidden = {str(item).lower() for item in forbidden}
    for expected in ("passwords", "tokens", "private keys", "secret values"):
        if expected not in normalized_forbidden:
            fail(f"{path.name} must forbid {expected}")

    acceptance = policy.get("acceptance", {})
    for key in (
        "everkeep_integrated",
        "everkeep_ready",
        "target_runtime_acceptance_required",
        "exact_revision_acceptance_required",
    ):
        if not isinstance(acceptance.get(key), bool):
            fail(f"{path.name} acceptance.{key} must be boolean")
    if acceptance.get("everkeep_ready") is True and acceptance.get("everkeep_integrated") is not True:
        fail(f"{path.name} cannot be Everkeep ready without integration acceptance")


def main() -> None:
    contract = load_json(CONTRACT_PATH, "identity contract")
    status_schema = load_json(STATUS_SCHEMA_PATH, "status schema")
    adoption_schema = load_json(ADOPTION_SCHEMA_PATH, "adoption schema")
    acceptance_schema = load_json(ACCEPTANCE_SCHEMA_PATH, "acceptance schema")

    identity = contract.get("identity", {})
    boundaries = contract.get("boundaries", {})
    fail_closed = contract.get("fail_closed", {})
    visual_identity = contract.get("visual_identity", {})
    contracts = contract.get("contracts", {})

    if identity.get("official_name") != EXPECTED_NAME:
        fail("official identity name drifted")
    if identity.get("short_name") != EXPECTED_SHORT:
        fail("short identity name drifted")
    if contract.get("normalized_states") != EXPECTED_STATES:
        fail("normalized state contract drifted")

    if contracts.get("status_schema") != "contracts/continuity.status.schema.json":
        fail("identity contract must pin the canonical status schema")
    if contracts.get("adoption_schema") != "contracts/continuity.adoption.schema.json":
        fail("identity contract must pin the canonical adoption schema")
    if contracts.get("acceptance_schema") != "contracts/continuity.acceptance.schema.json":
        fail("identity contract must pin the canonical acceptance schema")

    for key in ("is_backup_engine", "is_storage_platform", "is_secret_store", "is_generic_remediation_api"):
        if boundaries.get(key) is not False:
            fail(f"boundary {key} must remain false")
    if boundaries.get("read_only_by_default") is not True:
        fail("Everkeep integrations must remain read-only by default")

    for key in (
        "missing_required_evidence_blocks_ready",
        "stale_required_evidence_blocks_ready",
        "unavailable_required_evidence_blocks_ready",
        "unverified_required_evidence_blocks_ready",
    ):
        if fail_closed.get(key) is not True:
            fail(f"fail-closed invariant {key} must remain true")

    for relative_path in contract.get("required_documents", []):
        path = ROOT / relative_path
        if not path.is_file():
            fail(f"required document missing: {relative_path}")
        if EXPECTED_NAME not in path.read_text(encoding="utf-8"):
            fail(f"required document does not identify {EXPECTED_NAME}: {relative_path}")

    status_properties = status_schema.get("properties", {})
    if status_properties.get("state", {}).get("enum") != EXPECTED_STATES:
        fail("status schema state enum drifted from identity contract")
    if status_properties.get("dimension", {}).get("enum") != EXPECTED_DIMENSIONS:
        fail("status schema dimension enum drifted")

    required_status_fields = {
        "record_id",
        "producer",
        "scope",
        "dimension",
        "state",
        "observed_at",
        "required_evidence",
        "verification_method",
    }
    if not required_status_fields.issubset(set(status_schema.get("required", []))):
        fail("status schema is missing required continuity evidence fields")

    adoption_dimensions = adoption_schema.get("properties", {}).get("dimensions", {}).get("items", {}).get("enum")
    if adoption_dimensions != EXPECTED_DIMENSIONS:
        fail("adoption schema dimension enum drifted from status contract")

    acceptance_dimensions = acceptance_schema.get("properties", {}).get("required_ready_evidence", {}).get("propertyNames", {}).get("enum")
    if acceptance_dimensions != EXPECTED_DIMENSIONS:
        fail("acceptance schema dimension enum drifted from status contract")

    reference_adoptions = contract.get("reference_adoptions", [])
    if not reference_adoptions:
        fail("identity contract must declare reference adoption manifests")
    for relative_path in reference_adoptions:
        validate_reference_adoption(ROOT / relative_path, adoption_schema)

    reference_acceptance = contract.get("reference_acceptance_policies", [])
    if not reference_acceptance:
        fail("identity contract must declare reference acceptance policies")
    for relative_path in reference_acceptance:
        validate_reference_acceptance(ROOT / relative_path, acceptance_schema)

    canonical_asset = visual_identity.get("canonical_asset")
    visual_status = visual_identity.get("status")
    if visual_status not in {"pending", "approved"}:
        fail("visual identity status must be pending or approved")
    if not isinstance(canonical_asset, str) or not canonical_asset:
        fail("canonical visual asset path is missing")
    asset_path = ROOT / canonical_asset
    if visual_status == "approved" and not asset_path.is_file():
        fail("approved visual identity requires the canonical SVG asset")
    if visual_status == "pending" and asset_path.is_file():
        fail("canonical asset exists while visual identity is still marked pending")

    print("Everkeep validation passed.")


if __name__ == "__main__":
    main()
