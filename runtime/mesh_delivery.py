"""Authenticated runtime delivery for Everkeep Mesh evidence envelopes.

GoreeCloud Identity remains responsible for credential issuance. This client
expects a short-lived bearer credential for service ``everkeep`` carrying the
``mesh.evidence.write`` scope and never persists or returns that credential.
"""
from __future__ import annotations

import json
from urllib import error, parse, request


class _NoRedirectHandler(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _endpoint(mesh_base_url: str) -> str:
    raw = str(mesh_base_url or "").strip().rstrip("/")
    parsed = parse.urlparse(raw)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Mesh base URL must not contain user information")
    if parsed.query or parsed.fragment or parsed.params:
        raise ValueError("Mesh base URL must not contain query, fragment, or path parameters")
    if parsed.scheme == "https" and parsed.hostname:
        return raw + "/v1/evidence/envelopes"
    if parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}:
        return raw + "/v1/evidence/envelopes"
    raise ValueError("Mesh evidence delivery requires HTTPS except for loopback development")


def deliver_mesh_evidence(
    envelope: dict,
    *,
    mesh_base_url: str,
    bearer_token: str,
    timeout_seconds: float = 5.0,
) -> dict:
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be an object")
    if (envelope.get("producer") or {}).get("system") != "everkeep":
        raise ValueError("Everkeep delivery only accepts everkeep envelopes")
    token = str(bearer_token or "").strip()
    if not token:
        raise ValueError("GoreeCloud Identity bearer credential is required")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    body = json.dumps(envelope, separators=(",", ":")).encode("utf-8")
    req = request.Request(
        _endpoint(mesh_base_url),
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "goreecloud-everkeep/mesh-evidence",
        },
    )
    opener = request.build_opener(_NoRedirectHandler())
    try:
        with opener.open(req, timeout=timeout_seconds) as response:
            status = response.status
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        if 300 <= exc.code < 400:
            raise RuntimeError("Mesh evidence delivery refused an HTTP redirect") from exc
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("error", "Mesh rejected evidence delivery")
        except Exception:
            detail = "Mesh rejected evidence delivery"
        raise RuntimeError(f"Mesh evidence delivery failed with HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError("Mesh evidence delivery failed before acceptance") from exc

    if status not in {200, 201}:
        raise RuntimeError(f"Mesh evidence delivery returned unexpected HTTP {status}")
    delivered = payload.get("envelope") or {}
    if delivered.get("id") != envelope.get("id"):
        raise RuntimeError("Mesh delivery receipt did not bind to the submitted evidence id")
    if payload.get("producer_service_id") != "everkeep":
        raise RuntimeError("Mesh delivery receipt did not bind to Everkeep service identity")
    return {
        "evidence_id": delivered.get("id"),
        "replayed": payload.get("replayed") is True,
        "accepted_at": payload.get("accepted_at"),
        "producer_service_id": payload.get("producer_service_id"),
    }
