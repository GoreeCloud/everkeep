#!/usr/bin/env python3
"""Deployable-reference HTTP host for Everkeep.

This host intentionally exposes only health/readiness and a minimal protected
resource query surface until production platform clients are configured.
"""

from __future__ import annotations

import json
import os
from wsgiref.simple_server import make_server


def _json(start_response, status, payload):
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(body)))])
    return [body]


def application(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    if path == "/health":
        return _json(start_response, "200 OK", {"status": "ok", "service": "everkeep"})
    if path == "/ready":
        required = ["EVERKEEP_DATABASE_URL", "EVERKEEP_IDENTITY_URL", "EVERKEEP_PRIVACY_URL", "EVERKEEP_WARDVEIL_URL", "EVERKEEP_MESH_URL"]
        missing = [name for name in required if not os.getenv(name)]
        status = "ready" if not missing else "not_ready"
        return _json(start_response, "200 OK" if not missing else "503 Service Unavailable", {"status": status, "missingConfiguration": missing})
    return _json(start_response, "404 Not Found", {"error": "not_found"})


def main():
    host = os.getenv("EVERKEEP_HOST", "0.0.0.0")
    port = int(os.getenv("EVERKEEP_PORT", "8080"))
    with make_server(host, port, application) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
