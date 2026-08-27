#!/usr/bin/env python3
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.mesh_delivery import deliver_mesh_evidence
from runtime.mesh_evidence import create_restore_verification_envelope


def fail(message: str) -> None:
    raise SystemExit(f"Everkeep Mesh delivery test failed: {message}")


def start_server(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


now = datetime.now(timezone.utc)
evidence = {
    "schemaVersion": "1.0",
    "verificationId": "delivery-restore-001",
    "environment": "staging",
    "capturedAt": (now - timedelta(minutes=1)).isoformat(),
    "everkeepSourceRevision": "a" * 40,
    "target": {"system": "goreecloud-drive", "component": "document-store", "resourceId": "resource-42", "deployedRevision": "b" * 40},
    "status": "pass",
    "authoritative": True,
    "exercise": {"recoveryPointId": "rp-private", "startedAt": (now - timedelta(minutes=8)).isoformat(), "completedAt": (now - timedelta(minutes=1)).isoformat(), "isolatedVerification": True, "integrityVerified": True, "restoredStateVerified": True, "promotionToProductionPerformed": False, "notes": "private operator notes"},
    "evidenceRefs": ["private://restore/full-report"],
    "securityStateAuthorityTransferred": False,
}
envelope = create_restore_verification_envelope(evidence, valid_until=(now + timedelta(hours=1)).isoformat(), observed_at=now)
received = {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        received["authorization"] = self.headers.get("Authorization")
        received["body"] = json.loads(self.rfile.read(length).decode("utf-8"))
        response = {"envelope": {**received["body"], "fresh": True}, "replayed": False, "accepted_at": now.isoformat().replace("+00:00", "Z"), "producer_service_id": "everkeep"}
        encoded = json.dumps(response).encode("utf-8")
        self.send_response(201); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(encoded))); self.end_headers(); self.wfile.write(encoded)


server, thread = start_server(Handler)
try:
    receipt = deliver_mesh_evidence(envelope, mesh_base_url=f"http://127.0.0.1:{server.server_port}", bearer_token="test-identity-credential")
finally:
    server.shutdown(); server.server_close(); thread.join(timeout=2)

if received.get("authorization") != "Bearer test-identity-credential":
    fail("Identity credential was not sent as bearer authorization")
if received.get("body") != envelope:
    fail("delivered envelope changed in transit")
serialized = json.dumps(received.get("body", {}))
for forbidden in ("private operator notes", "private://restore/full-report", "recoveryPointId", "evidenceRefs"):
    if forbidden in serialized:
        fail(f"private/full recovery evidence leaked into delivery: {forbidden}")
if receipt.get("producer_service_id") != "everkeep" or receipt.get("evidence_id") != envelope["id"]:
    fail("delivery receipt was not producer/evidence bound")

for unsafe in ("http://mesh.example.test", "https://user:pass@mesh.example.test", "https://mesh.example.test?target=other", "https://mesh.example.test#fragment"):
    try:
        deliver_mesh_evidence(envelope, mesh_base_url=unsafe, bearer_token="secret")
    except ValueError:
        pass
    else:
        fail(f"unsafe Mesh base URL must be rejected: {unsafe}")

sink = {"requests": 0, "authorization": None}

class SinkHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return
    def do_POST(self):
        sink["requests"] += 1
        sink["authorization"] = self.headers.get("Authorization")
        self.send_response(204); self.end_headers()

sink_server, sink_thread = start_server(SinkHandler)

class RedirectHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return
    def do_POST(self):
        self.send_response(307)
        self.send_header("Location", f"http://127.0.0.1:{sink_server.server_port}/capture")
        self.end_headers()

redirect_server, redirect_thread = start_server(RedirectHandler)
try:
    try:
        deliver_mesh_evidence(envelope, mesh_base_url=f"http://127.0.0.1:{redirect_server.server_port}", bearer_token="redirect-sensitive-proof")
    except RuntimeError:
        pass
    else:
        fail("Mesh redirects must be rejected")
finally:
    redirect_server.shutdown(); redirect_server.server_close(); redirect_thread.join(timeout=2)
    sink_server.shutdown(); sink_server.server_close(); sink_thread.join(timeout=2)

if sink["requests"] != 0 or sink["authorization"] is not None:
    fail("service identity proof must never be forwarded to a redirect target")

wrong = dict(envelope)
wrong["producer"] = dict(envelope["producer"])
wrong["producer"]["system"] = "wardveil-security"
try:
    deliver_mesh_evidence(wrong, mesh_base_url="https://mesh.example.test", bearer_token="secret")
except ValueError:
    pass
else:
    fail("cross-producer envelope must be rejected before transport")

print("Everkeep authenticated Mesh evidence delivery: OK")
