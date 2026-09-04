"""Producer-bound GoreeCloud Mesh Platform Registry publication for Everkeep.

The transport accepts an already-normalized platform record. It does not infer
recoverability from backup success, compute canonical platform conformance, or
transfer Everkeep recovery authority to Mesh or Manager.
"""
from __future__ import annotations

import json
from urllib import error, parse, request


SCHEMA = "goreecloud.mesh.platform-record.v1"
COMPONENT_ID = "goreecloud-everkeep"
REPOSITORY = "GoreeCloud/goreecloud-everkeep"
AUDIENCE = "goreecloud-mesh"
SCOPE = "mesh.platform-registry.write"
MAX_RECORD_BYTES = 256 * 1024
MAX_CREDENTIAL_LENGTH = 16_384
MAX_ERROR_BODY = 4_096


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
    loopback = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme != "https" and not (parsed.scheme == "http" and loopback):
        raise ValueError("Mesh Platform Registry publication requires HTTPS except for loopback development")
    if not parsed.hostname:
        raise ValueError("Mesh base URL must include a host")
    return raw + "/v1/platform-registry"


def _record_body(record: dict) -> bytes:
    if not isinstance(record, dict):
        raise ValueError("platform record must be an object")
    if record.get("schema") != SCHEMA:
        raise ValueError("unsupported Mesh platform record schema")
    component = record.get("component") or {}
    source = record.get("source") or {}
    recovery = record.get("recovery")
    if component.get("id") != COMPONENT_ID:
        raise ValueError("Everkeep may publish only its own platform record")
    if component.get("repository") != REPOSITORY or source.get("repository") != REPOSITORY:
        raise ValueError("Everkeep platform record repository authority mismatch")
    if source.get("authority_transfer") is not False:
        raise ValueError("platform record authority_transfer must remain false")
    revision = source.get("revision")
    if not isinstance(revision, str) or len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("platform record source revision must be an exact lowercase Git revision")
    if not isinstance(recovery, dict):
        raise ValueError("Everkeep platform record requires explicit recovery state")

    backup_status = recovery.get("backup_status")
    restore_status = recovery.get("restore_status")
    last_verified_restore = recovery.get("last_verified_restore")
    allowed = {"verified", "implemented_unverified", "required_missing", "not_applicable", "unknown"}
    if backup_status not in allowed or restore_status not in allowed:
        raise ValueError("backup and restore status must use approved verification-state vocabulary")
    if restore_status == "verified" and not last_verified_restore:
        raise ValueError("verified restore requires last_verified_restore")
    if restore_status != "verified" and last_verified_restore is not None:
        raise ValueError("last_verified_restore cannot be set when restore_status is not verified")

    # Intentionally no rule upgrades restore_status when backup_status is
    # verified. Successful backup and verified restoration are distinct facts.
    body = json.dumps(record, separators=(",", ":")).encode("utf-8")
    if len(body) > MAX_RECORD_BYTES:
        raise ValueError("platform record is oversized")
    return body


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
                    "service_id": COMPONENT_ID,
                    "audience": AUDIENCE,
                    "scopes": (SCOPE,),
                }
            )
        except Exception:
            raise RuntimeError("GoreeCloud Identity credential acquisition failed") from None
    token = credential.strip() if isinstance(credential, str) else ""
    if not token:
        raise ValueError("GoreeCloud Identity bearer credential is required")
    if len(token) > MAX_CREDENTIAL_LENGTH:
        raise ValueError("GoreeCloud Identity bearer credential is oversized")
    if "\r" in token or "\n" in token:
        raise ValueError("GoreeCloud Identity bearer credential is malformed")
    return token


def _safe_error_code(exc: error.HTTPError) -> str:
    try:
        payload = json.loads(exc.read(MAX_ERROR_BODY).decode("utf-8"))
    except Exception:
        return ""
    code = payload.get("error_code") if isinstance(payload, dict) else None
    if not isinstance(code, str):
        return ""
    code = code.strip()
    if not code or len(code) > 80 or any(not (c.isalnum() or c in "._-") for c in code):
        return ""
    return f" ({code})"


def publish_platform_record(
    record: dict,
    *,
    mesh_base_url: str,
    bearer_token: str | None = None,
    credential_provider=None,
    timeout_seconds: float = 5.0,
) -> dict:
    """Publish one Everkeep-owned platform record to GoreeCloud Mesh."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    body = _record_body(record)
    endpoint = _endpoint(mesh_base_url)
    token = _credential(bearer_token=bearer_token, credential_provider=credential_provider)
    req = request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "goreecloud-everkeep/platform-registry",
        },
    )
    opener = request.build_opener(_NoRedirectHandler())
    try:
        with opener.open(req, timeout=timeout_seconds) as response:
            status = response.status
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        if 300 <= exc.code < 400:
            raise RuntimeError("Mesh Platform Registry publication refused an HTTP redirect") from None
        reason = _safe_error_code(exc)
        raise RuntimeError(f"Mesh Platform Registry publication failed with HTTP {exc.code}{reason}") from None
    except error.URLError:
        raise RuntimeError("Mesh Platform Registry publication failed before acceptance") from None

    if status != 201 or not isinstance(payload, dict):
        raise RuntimeError(f"Mesh Platform Registry returned unexpected HTTP {status}")
    returned = payload.get("record") or {}
    if payload.get("producer_service_id") != COMPONENT_ID:
        raise RuntimeError("Mesh Platform Registry receipt did not bind to Everkeep service identity")
    if (returned.get("component") or {}).get("id") != COMPONENT_ID:
        raise RuntimeError("Mesh Platform Registry receipt did not bind to Everkeep component id")
    if payload.get("authority_transfer") is not False:
        raise RuntimeError("Mesh Platform Registry receipt violated the no-authority-transfer boundary")
    return {
        "component_id": COMPONENT_ID,
        "accepted_at": payload.get("accepted_at"),
        "producer_service_id": payload.get("producer_service_id"),
        "authority_transfer": False,
    }
