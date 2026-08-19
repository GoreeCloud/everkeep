#!/usr/bin/env python3
"""Validate the GoreeCloud Continuity identity repository."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "continuity.identity.json"

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


def main() -> None:
    if not CONTRACT_PATH.is_file():
        fail("missing contracts/continuity.identity.json")

    try:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"identity contract is not valid JSON: {exc}")

    identity = contract.get("identity", {})
    boundaries = contract.get("boundaries", {})
    fail_closed = contract.get("fail_closed", {})

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

    print("GoreeCloud Continuity validation passed.")


if __name__ == "__main__":
    main()
