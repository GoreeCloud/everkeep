#!/usr/bin/env python3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.mesh_evidence import create_restore_verification_envelope


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

print("Everkeep Mesh Evidence Envelope adapter: OK")
