"""Authenticated runtime delivery for Everkeep Mesh evidence envelopes.

GoreeCloud Identity remains responsible for credential issuance. Production
callers should request a fresh short-lived service credential per delivery.
This client never persists, returns, logs, or chains credential-bearing errors.
"""
from __future__ import annotations

import json
from urllib import error, parse, request


_SERVICE_ID = "everkeep"
_AUDIENCE = "goreecloud-mesh"
_SCOPE = "mesh.evidence.write"
_MAX_CREDENTIAL_LENGTH = 16_384
_MAX_ERROR_BODY = 4_096


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


def _credential(*, bearer_token=None, credential_provider=None) -> str:
    if bearer_token is not None and credential_provider is not None:
        raise ValueError("Provide either bearer_token or credential_provider, not both")
    credential = bearer_token
    if credential_provider is not None:
        if not callable(credential_provider):
            raise ValueError("GoreeCloud Identity credential provider must be callable")
        try:
            credential = credential_provider(
                {
                    "service_id": _SERVICE_ID,
                    "audience": _AUDIENCE,
                    "scopes": (_SCOPE,),
                }
            )
        except Exception:
            raise RuntimeError("GoreeCloud Identity credential acquisition failed") from None
    token = credential.strip() if isinstance(credential, str) else ""
    if not token:
        raise ValueError("GoreeCloud Identity bearer credential is required")
    if len(token) > _MAX_CREDENTIAL_LENGTH:
        raise ValueError("GoreeCloud Identity bearer credential is oversized")
    if "\r" in token or "\n" in token:
        raise ValueError("GoreeCloud Identity bearer credential is malformed")
    return token


def _safe_error_code(exc: error.HTTPError) -> str:
    try:
        payload = json.loads(exc.read(_MAX_ERROR_BODY).decode("utf-8"))
    except Exception:
        return ""
    code = payload.get("error_code") if isinstance(payload, dict) else None
    if not isinstance(code, str):
        return ""
    code = code.strip()
    if not code or len(code) > 80 or any(not (c.isalnum() or c in "._-") for c in code):
        return ""
    return f" ({code})"


def deliver_mesh_evidence(
    envelope: dict,
    *,
    mesh_base_url: str,
    bearer_token: str | None = None,
    credential_provider=None,
    timeout_seconds: float = 5.0,
) -> dict:
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be an object")
    if (envelope.get("producer") or {}).get("system") != "everkeep":
        raise ValueError("Everkeep delivery only accepts everkeep envelopes")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    endpoint = _endpoint(mesh_base_url)
    token = _credential(bearer_token=bearer_token, credential_provider=credential_provider)
    body = json.dumps(envelope, separators=(",", ":")).encode("utf-8")
    req = request.Request(
        endpoint,
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
            raise RuntimeError("Mesh evidence delivery refused an HTTP redirect") from None
        reason = _safe_error_code(exc)
        raise RuntimeError(f"Mesh evidence delivery failed with HTTP {exc.code}{reason}") from None
    except error.URLError:
        raise RuntimeError("Mesh evidence delivery failed before acceptance") from None

    if status not in {200, 201}:
        raise RuntimeError(f"Mesh evidence delivery returned unexpected HTTP {status}")
    if not isinstance(payload, dict):
        raise RuntimeError("Mesh evidence delivery returned an invalid receipt")
    delivered = payload.get("envelope") or {}
    if delivered.get("id") != envelope.get("id"):
        raise RuntimeError("Mesh delivery receipt did not bind to the submitted evidence id")
    if payload.get("producer_service_id") != _SERVICE_ID:
        raise RuntimeError("Mesh delivery receipt did not bind to Everkeep service identity")
    return {
        "evidence_id": delivered.get("id"),
        "replayed": payload.get("replayed") is True,
        "accepted_at": payload.get("accepted_at"),
        "producer_service_id": payload.get("producer_service_id"),
    }
