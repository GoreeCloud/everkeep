#!/usr/bin/env python3
"""Fail-closed, non-executing Everkeep plan for a Wardveil isolated restore.

This CLI NEVER calls a backup, restore, Cloudflare API, or live target. Gate
metadata are self-reported until independently verified by Everkeep and
therefore can only request review, never authorize a restore or emit evidence.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from recovery_orchestrator import REQUIRED_GATES, build_plan, evaluate_execution

TARGET_ID = "goreecloud-wardveil-persistence"
SOURCE_SHA = "cc493530c02925a4404c54d2767c15d9fbfa0835"
PROVIDER_SCHEMA = "1.1"
ADDITIONAL_GATES = (
    "everkeep-runtime-verified",
    "source-revision-observed",
    "independent-recovery-point-verified",
    "nonproduction-isolated-target-verified",
    "source-write-fenced",
    "cross-object-restore-mechanism-verified",
    "restore-integrity-witness-ready",
)
ALL_GATES = (*REQUIRED_GATES, *ADDITIONAL_GATES)


def evaluate_preflight(manifest: dict | None = None) -> dict:
    """Return a plan and non-authorizing blocker report; never perform a restore."""
    manifest = manifest or {}
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be an object")
    exact_revision = manifest.get("deployedRevision", SOURCE_SHA)
    if exact_revision != SOURCE_SHA or not re.fullmatch(r"[a-f0-9]{40}", exact_revision):
        raise ValueError("Manifest deployedRevision must match the frozen Wardveil Seal source")

    proposed_target = manifest.get("isolatedTargetId")
    if proposed_target is not None and (not isinstance(proposed_target, str) or not proposed_target.strip()):
        raise ValueError("Isolated target ID must be a nonempty string")
    if proposed_target == TARGET_ID:
        raise ValueError("Refusing restore plan that names the live production source as isolated target")

    plan = build_plan(
        plan_id="everkeep-wardveil-cloudflare-isolated-restore-preflight",
        target_resource_ids=[TARGET_ID],
        resources={TARGET_ID: {"resourceId": TARGET_ID, "relationships": []}},
        mode="sandbox",
        created_at="2026-10-14T00:00:00Z",
    )
    if plan["sourceMutationAllowed"] is not False or plan["mode"] != "sandbox":
        raise ValueError("Everkeep plan unexpectedly allows source mutation")

    # The existing engine must also remain explicitly blocked. The manifest
    # is NOT plugged into its authorization evaluator: arbitrary JSON proof
    # pointers are not independently validated Everkeep gate evidence.
    engine = evaluate_execution(
        plan, gate_evidence={}, execution_id="preflight-only-no-execution",
        environment="production",
    )
    if engine["authorized"] is not False or engine["state"] != "blocked":
        raise ValueError("Missing authoritative engine evidence must block")

    data = manifest.get("gates", {})
    if not isinstance(data, dict):
        raise ValueError("Manifest gates must be an object")
    blockers = []
    supplied_pass_gates = []
    for gate in ALL_GATES:
        item = data.get(gate, {})
        if not isinstance(item, dict):
            raise ValueError("Gate entries must be objects")
        state = item.get("state", "unknown")
        if state not in {"unknown", "fail", "pass"}:
            raise ValueError("Unrecognized gate state")
        ref = item.get("evidenceRef")
        if state != "pass" or not isinstance(ref, str) or not ref.strip():
            blockers.append(f"gate:{gate}:missing_verified_evidence")
        else:
            supplied_pass_gates.append(gate)

    if not proposed_target:
        blockers.append("isolated_target_id_missing")

    # Metadata passing is at most a request for independent review, not
    # proof of a safe recovery target, backup export or completed restore.
    return {
        "schemaVersion": "1.0",
        "kind": "everkeep_wardveil_isolated_restore_preflight",
        "environment": "production",
        "target": {
            "system": "Wardveil Security",
            "component": "Cloudflare persistence runtime",
            "resourceId": TARGET_ID,
            "deployedRevision": SOURCE_SHA,
        },
        "everkeepRestoreEvidenceSchemaVersion": PROVIDER_SCHEMA,
        "requestedMode": "sandbox",
        "isolatedTargetIdProvided": bool(proposed_target),
        "sourceMutationAllowed": False,
        "proposedStepOrder": [step["operation"] for step in plan["steps"]],
        "providedGateMetadataCount": len(supplied_pass_gates),
        "requiredGateCount": len(ALL_GATES),
        "blockerCodes": sorted(blockers),
        "planningStatus": "blocked" if blockers else "requires_independent_authoritative_review",
        "engineExecutionAuthorized": False,
        "restorePerformed": False,
        "integrityVerified": False,
        "restoredStateVerified": False,
        "authoritativeRestoreEvidenceIssued": False,
        "wardveilRuntimeAccepted": False,
        "securityStateAuthorityTransferred": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, help="Optional nonsecret gate metadata JSON")
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text()) if args.manifest else {}
    result = evaluate_preflight(data)
    print(json.dumps(result, sort_keys=True))
    # A non-executing blocked preflight is a successful CLI evaluation,
    # NOT a successful restore or release acceptance.


if __name__ == "__main__":
    main()
