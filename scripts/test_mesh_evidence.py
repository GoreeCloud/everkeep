#!/usr/bin/env python3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.mesh_evidence import (
    create_restore_verification_envelope,
    validate_mesh_evidence_refresh_intent,
)
from runtime.mesh_refresh_response import create_mesh_evidence_refresh_response


def fail(message: str) -> None:
    raise SystemExit(f"Everkeep Mesh evidence test failed: {message}")


now = datetime(2026, 8, 26, 23, 30, tzinfo=timezone.utc)
evidence = {
    "schemaVersion": "1.0",
    "verificationId": "restore-verify-001",
    "environment": "staging",
    "capturedAt": (now - timedelta(minutes=2)).isoformat(),
    "everkeepSourceRevision": "a" * 40,
    "target": {
        "system": "goreecloud-drive",
        "component": "document-store",
        "resourceId": "resource-42",
        "deployedRevision": "b" * 40,
    },
    "status": "fail",
    "authoritative": True,
    "exercise": {
        "recoveryPointId": "rp-001",
        "startedAt": (now - timedelta(minutes=8)).isoformat(),
        "completedAt": (now - timedelta(minutes=2)).isoformat(),
        "isolatedVerification": True,
        "integrityVerified": True,
        "restoredStateVerified": False,
        "promotionToProductionPerformed": False,
        "notes": "private operator notes must not be transported",
    },
    "evidenceRefs": ["private://sandbox/full-report"],
    "securityStateAuthorityTransferred": False,
}

envelope = create_restore_verification_envelope(
    evidence,
    valid_until=(now + timedelta(hours=2)).isoformat(),
    observed_at=now,
)

if envelope["version"] != "goreecloud.evidence-envelope.v1":
    fail("wrong envelope version")
if envelope["producer"]["system"] != "everkeep":
    fail("wrong producer")
if envelope["authority_domain"] != "recovery":
    fail("wrong authority domain")
if envelope["assertion"] != "restore-verification" or envelope["outcome"] != "fail":
    fail("restore verification truth was not preserved")
if envelope["subject"]["id"] != "resource-42":
    fail("resource scope not preserved")
if not envelope["payload_digest"].startswith("sha256:"):
    fail("payload digest missing")

serialized = json.dumps(envelope)
for forbidden in ("private operator notes", "private://sandbox/full-report", "recoveryPointId", "evidenceRefs"):
    if forbidden in serialized:
        fail(f"private/full evidence leaked into Mesh envelope: {forbidden}")

if envelope["contains_user_content"] or envelope["contains_secret_material"]:
    fail("minimization flags must remain false")

expired = dict(evidence)
try:
    create_restore_verification_envelope(
        expired,
        valid_until=(now - timedelta(seconds=1)).isoformat(),
        observed_at=now,
    )
except ValueError:
    pass
else:
    fail("expired restore verification evidence must be rejected")

non_authoritative = dict(evidence)
non_authoritative["authoritative"] = False
try:
    create_restore_verification_envelope(
        non_authoritative,
        valid_until=(now + timedelta(hours=1)).isoformat(),
        observed_at=now,
    )
except ValueError:
    pass
else:
    fail("non-authoritative restore evidence must be rejected")

refresh = {
    "version": "goreecloud.evidence-refresh-intent.v1",
    "id": "refresh-everkeep-resource-42",
    "coordinator": {
        "system": "goreecloud-mesh",
        "repository": "GoreeCloud/goreecloud-mesh",
        "revision": "c" * 40,
        "contract": "contracts/mesh.evidence-refresh-intent.schema.json",
    },
    "producer": "everkeep",
    "authority_domain": "recovery",
    "subject": {"kind": "resource", "id": "resource-42", "scope": "document-store"},
    "assertion": "restore-verification",
    "reason": "stale",
    "requested_at": now.isoformat(),
    "latest_observed_at": (now - timedelta(hours=2)).isoformat(),
    "contains_user_content": False,
    "contains_secret_material": False,
    "authority_transferred": False,
    "execution_authorized": False,
}
accepted = validate_mesh_evidence_refresh_intent(refresh, now=now)
if accepted["producer"] != "everkeep" or accepted["authority_domain"] != "recovery":
    fail("refresh intent changed Everkeep authority targeting")
if accepted["execution_authorized"] or accepted["authority_transferred"]:
    fail("refresh intent granted Everkeep execution or transferred authority")
for forbidden in ("outcome", "ready", "failover_authorized", "restore_authorized"):
    if forbidden in accepted:
        fail(f"refresh intent manufactured continuity/recovery truth: {forbidden}")

wrong_domain = dict(refresh)
wrong_domain["authority_domain"] = "security"
try:
    validate_mesh_evidence_refresh_intent(wrong_domain, now=now)
except ValueError:
    pass
else:
    fail("cross-authority Everkeep refresh intent must be rejected")

effecting = dict(refresh)
effecting["execution_authorized"] = True
try:
    validate_mesh_evidence_refresh_intent(effecting, now=now)
except ValueError:
    pass
else:
    fail("refresh intent must not authorize recovery or failover execution")

response = create_mesh_evidence_refresh_response(
    refresh,
    response_id="everkeep-refresh-response-001",
    revision="d" * 40,
    status="completed",
    reason_code="evidence-issued",
    responded_at=now,
    evidence_envelope_id="everkeep-restore-verify-002",
    now=now,
)
if response["version"] != "goreecloud.evidence-refresh-response.v1":
    fail("wrong refresh response version")
if response["intent"]["id"] != refresh["id"] or response["intent"]["coordinator_revision"] != refresh["coordinator"]["revision"]:
    fail("refresh response did not bind the exact Mesh intent")
if response["producer"]["system"] != "everkeep" or response["authority_domain"] != "recovery":
    fail("refresh response changed Everkeep authority targeting")
if not response["evidence_produced"] or response.get("evidence_envelope_id") != "everkeep-restore-verify-002":
    fail("completed refresh response did not preserve separate evidence reference")
for forbidden in ("outcome", "ready", "failover_authorized", "restore_authorized", "fresh"):
    if forbidden in response:
        fail(f"refresh response manufactured continuity/recovery truth: {forbidden}")
if response["execution_authorized"] or response["authority_transferred"]:
    fail("refresh response granted Everkeep execution or transferred authority")

try:
    create_mesh_evidence_refresh_response(
        refresh,
        response_id="everkeep-refresh-response-002",
        revision="d" * 40,
        status="received",
        evidence_envelope_id="everkeep-restore-verify-003",
        now=now,
    )
except ValueError:
    pass
else:
    fail("non-completed refresh response must not claim produced evidence")

print("Everkeep Mesh Evidence Envelope, refresh-intent, and refresh-response adapters: OK")
