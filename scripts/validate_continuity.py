#!/usr/bin/env python3
"""Validate the GoreeCloud Continuity identity repository."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "continuity.identity.json"
STATUS_SCHEMA_PATH = ROOT / "contracts" / "continuity.status.schema.json"

EXPECTED_NAME = "GoreeCloud Continuity"
EXPECTED_SHORT = "Continuity"
EXPECTED_STATES = [
    "ready",
    "attention",
    "degraded",
    "unknown",
    "not_applicable",
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


def main() -> None:
    contract = load_json(CONTRACT_PATH, "identity contract")
    status_schema = load_json(STATUS_SCHEMA_PATH, "status schema")

    identity = contract.get("identity", {})
    boundaries = contract.get("boundaries", {})
    fail_closed = contract.get("fail_closed", {})
    visual_identity = contract.get("visual_identity", {})

    if identity.get("official_name") != EXPECTED_NAME:
        fail("official identity name drifted")
    if identity.get("short_name") != EXPECTED_SHORT:
        fail("short identity name drifted")
    if contract.get("normalized_states") != EXPECTED_STATES:
        fail("normalized state contract drifted")

    forbidden_true = (
        "is_backup_engine",
        "is_storage_platform",
        "is_secret_store",
        "is_generic_remediation_api",
    )
    for key in forbidden_true:
        if boundaries.get(key) is not False:
            fail(f"boundary {key} must remain false")

    if boundaries.get("read_only_by_default") is not True:
        fail("Continuity integrations must remain read-only by default")

    for key in (
        "missing_required_evidence_blocks_ready",
        "stale_required_evidence_blocks_ready",
        "unavailable_required_evidence_blocks_ready",
        "unverified_required_evidence_blocks_ready",
    ):
        if fail_closed.get(key) is not True:
            fail(f"fail-closed invariant {key} must remain true")

    required_documents = contract.get("required_documents", [])
    for relative_path in required_documents:
        path = ROOT / relative_path
        if not path.is_file():
            fail(f"required document missing: {relative_path}")
        text = path.read_text(encoding="utf-8")
        if EXPECTED_NAME not in text and relative_path != "SECURITY.md":
            fail(f"required document does not identify {EXPECTED_NAME}: {relative_path}")

    state_property = status_schema.get("properties", {}).get("state", {})
    if state_property.get("enum") != EXPECTED_STATES:
        fail("status schema state enum drifted from identity contract")

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

    print("GoreeCloud Continuity validation passed.")


if __name__ == "__main__":
    main()
