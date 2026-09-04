#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.mesh_delivery import deliver_mesh_evidence


def fail(message: str) -> None:
    raise SystemExit(f"Everkeep Mesh Identity boundary test failed: {message}")


def start_server(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


envelope = {
    "id": "everkeep-identity-boundary-001",
    "producer": {"system": "everkeep"},
    "assertion": "restore-verification",
}
provider_calls = []
received = {}


class AcceptedHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def do_POST(self):
        received["authorization"] = self.headers.get("Authorization")
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        payload = {
            "envelope": {**body, "fresh": True},
            "replayed": False,
            "accepted_at": "2026-09-04T06:50:00Z",
            "producer_service_id": "everkeep",
        }
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


server, thread = start_server(AcceptedHandler)
try:
    receipt = deliver_mesh_evidence(
        envelope,
        mesh_base_url=f"http://127.0.0.1:{server.server_port}",
        credential_provider=lambda requested: provider_calls.append(requested) or "fresh-everkeep-token",
    )
finally:
    server.shutdown(); server.server_close(); thread.join(timeout=2)

expected_request = {
    "service_id": "everkeep",
    "audience": "goreecloud-mesh",
    "scopes": ("mesh.evidence.write",),
}
if provider_calls != [expected_request]:
    fail(f"unexpected Identity credential request: {provider_calls!r}")
if received.get("authorization") != "Bearer fresh-everkeep-token":
    fail("fresh Identity credential was not used")
if "fresh-everkeep-token" in json.dumps(receipt):
    fail("credential leaked into receipt")

try:
    deliver_mesh_evidence(
        envelope,
        mesh_base_url="https://mesh.example.test",
        bearer_token="direct",
        credential_provider=lambda _request: "provider",
    )
except ValueError:
    pass
else:
    fail("ambiguous credential ownership must fail closed")

for invalid in ("bad\r\ntoken", "x" * 16_385):
    try:
        deliver_mesh_evidence(
            envelope,
            mesh_base_url="https://mesh.example.test",
            credential_provider=lambda _request, value=invalid: value,
        )
    except ValueError:
        pass
    else:
        fail("malformed or oversized credential must fail before transport")

try:
    deliver_mesh_evidence(
        envelope,
        mesh_base_url="https://mesh.example.test",
        credential_provider=lambda _request: (_ for _ in ()).throw(
            RuntimeError("credential=everkeep-private-material")
        ),
    )
except RuntimeError as exc:
    if str(exc) != "GoreeCloud Identity credential acquisition failed":
        fail("provider failure was not sanitized")
    if exc.__cause__ is not None or not exc.__suppress_context__:
        fail("provider failure did not suppress sensitive exception context")
    if "everkeep-private-material" in repr(exc):
        fail("provider secret leaked into local error")
else:
    fail("provider failure must fail closed")

provider_called = False

def should_not_issue(_request):
    global provider_called
    provider_called = True
    return "should-not-be-issued"

try:
    deliver_mesh_evidence(
        envelope,
        mesh_base_url="http://mesh.example.test",
        credential_provider=should_not_issue,
    )
except ValueError:
    pass
else:
    fail("unsafe destination must be rejected")
if provider_called:
    fail("unsafe destination triggered Identity credential issuance")


class RejectionHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def do_POST(self):
        body = json.dumps({
            "error": f"Authorization: {self.headers.get('Authorization')}",
            "error_code": "scope_denied",
        }).encode("utf-8")
        self.send_response(403)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


rejection_server, rejection_thread = start_server(RejectionHandler)
try:
    try:
        deliver_mesh_evidence(
            envelope,
            mesh_base_url=f"http://127.0.0.1:{rejection_server.server_port}",
            credential_provider=lambda _request: "everkeep-reflection-secret",
        )
    except RuntimeError as exc:
        if str(exc) != "Mesh evidence delivery failed with HTTP 403 (scope_denied)":
            fail(f"unexpected sanitized rejection: {exc}")
        if exc.__cause__ is not None or not exc.__suppress_context__ or "everkeep-reflection-secret" in repr(exc):
            fail("remote rejection leaked credential material")
    else:
        fail("Mesh rejection must fail closed")
finally:
    rejection_server.shutdown(); rejection_server.server_close(); rejection_thread.join(timeout=2)

print("Everkeep Mesh Identity credential boundary: OK")
