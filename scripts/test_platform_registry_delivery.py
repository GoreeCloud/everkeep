#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.platform_registry_delivery import publish_platform_record


def fail(message: str) -> None:
    raise SystemExit(f"Everkeep Platform Registry delivery test failed: {message}")


def start_server(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


record = {
    "schema": "goreecloud.mesh.platform-record.v1",
    "source": {
        "repository": "GoreeCloud/goreecloud-everkeep",
        "revision": "d" * 40,
        "contract_schema_version": "0.2",
        "authority_transfer": False,
    },
    "component": {
        "id": "goreecloud-everkeep",
        "product_name": "Everkeep",
        "kind": "service",
        "repository": "GoreeCloud/goreecloud-everkeep",
        "lifecycle": "development",
        "version": "0.3.5",
        "supported_platforms": ["linux-server"],
    },
    "recovery": {
        "backup_status": "verified",
        "restore_status": "implemented_unverified",
    },
}
provider_calls = []
received = {}


class AcceptedHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def do_POST(self):
        received["path"] = self.path
        received["authorization"] = self.headers.get("Authorization")
        length = int(self.headers.get("Content-Length", "0"))
        received["record"] = json.loads(self.rfile.read(length).decode("utf-8"))
        payload = {
            "record": received["record"],
            "accepted_at": "2026-09-04T06:55:00Z",
            "producer_service_id": "goreecloud-everkeep",
            "authority_transfer": False,
        }
        body = json.dumps(payload).encode("utf-8")
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


server, thread = start_server(AcceptedHandler)
try:
    receipt = publish_platform_record(
        record,
        mesh_base_url=f"http://127.0.0.1:{server.server_port}",
        credential_provider=lambda requested: provider_calls.append(requested) or "everkeep-registry-token",
    )
finally:
    server.shutdown(); server.server_close(); thread.join(timeout=2)

expected_request = {
    "service_id": "goreecloud-everkeep",
    "audience": "goreecloud-mesh",
    "scopes": ("mesh.platform-registry.write",),
}
if provider_calls != [expected_request]:
    fail(f"unexpected Identity credential request: {provider_calls!r}")
if received.get("path") != "/v1/platform-registry":
    fail("publisher used the wrong Mesh endpoint")
if received.get("authorization") != "Bearer everkeep-registry-token":
    fail("publisher did not use the scoped Identity credential")
if received.get("record", {}).get("recovery") != {
    "backup_status": "verified",
    "restore_status": "implemented_unverified",
}:
    fail("publisher mutated backup/restore truth")
if received["record"]["recovery"]["restore_status"] == "verified":
    fail("verified backup was incorrectly promoted to verified restore")
if receipt.get("authority_transfer") is not False:
    fail("receipt violated the no-authority-transfer boundary")
if "everkeep-registry-token" in json.dumps(receipt):
    fail("credential leaked into receipt")

invalid_restore_records = [
    {
        **record,
        "recovery": {"backup_status": "verified", "restore_status": "verified"},
    },
    {
        **record,
        "recovery": {
            "backup_status": "verified",
            "restore_status": "required_missing",
            "last_verified_restore": "2026-09-04T01:00:00Z",
        },
    },
]
for invalid in invalid_restore_records:
    try:
        publish_platform_record(
            invalid,
            mesh_base_url="https://mesh.example.test",
            bearer_token="never-sent",
        )
    except ValueError:
        pass
    else:
        fail("inconsistent restore verification state must fail before transport")

verified_restore = {
    **record,
    "recovery": {
        "backup_status": "verified",
        "restore_status": "verified",
        "last_verified_restore": "2026-09-04T01:00:00Z",
    },
}
# A correctly attributed verified restore is allowed by the producer transport;
# Mesh and the canonical platform evaluator still validate the full record.
try:
    from runtime.platform_registry_delivery import _record_body
    _record_body(verified_restore)
except ValueError as exc:
    fail(f"valid verified restore state was rejected: {exc}")

invalid_producers = [
    {**record, "component": {**record["component"], "id": "goreecloud-manager"}},
    {**record, "source": {**record["source"], "authority_transfer": True}},
]
for invalid in invalid_producers:
    try:
        publish_platform_record(
            invalid,
            mesh_base_url="https://mesh.example.test",
            bearer_token="never-sent",
        )
    except ValueError:
        pass
    else:
        fail("cross-producer or authority-transfer record must fail before transport")


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
        publish_platform_record(
            record,
            mesh_base_url=f"http://127.0.0.1:{rejection_server.server_port}",
            credential_provider=lambda _request: "everkeep-registry-reflection-secret",
        )
    except RuntimeError as exc:
        if str(exc) != "Mesh Platform Registry publication failed with HTTP 403 (scope_denied)":
            fail(f"unexpected sanitized rejection: {exc}")
        if "everkeep-registry-reflection-secret" in repr(exc):
            fail("remote rejection leaked credential material")
    else:
        fail("Mesh registry rejection must fail closed")
finally:
    rejection_server.shutdown(); rejection_server.server_close(); rejection_thread.join(timeout=2)

print("Everkeep producer-bound Platform Registry delivery: OK")
