#!/usr/bin/env python3
"""Evidence-first Everkeep staging verifier.

The verifier never infers that staging is operational. Every required check must
produce authoritative pass evidence; fail or unknown keeps operational false.
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Callable


@dataclass
class Check:
    name: str
    status: str
    authoritative: bool
    detail: str = ""
    evidenceRef: str = ""


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def require_env(name: str) -> Check:
    value = os.getenv(name, "").strip()
    return Check(name=f"env:{name}", status="pass" if value else "fail", authoritative=True,
                 detail="configured" if value else "missing")


def https_probe(name: str, base_env: str, path: str) -> Check:
    base = os.getenv(base_env, "").strip().rstrip("/")
    if not base:
        return Check(name=name, status="unknown", authoritative=True, detail=f"{base_env} not configured")
    if not base.startswith("https://"):
        return Check(name=name, status="fail", authoritative=True, detail="endpoint must use HTTPS")
    url = base + path
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "goreecloud-everkeep-staging-verifier/1"})
    try:
        with urllib.request.urlopen(request, timeout=8, context=ssl.create_default_context()) as response:
            ok = 200 <= response.status < 300
            return Check(name=name, status="pass" if ok else "fail", authoritative=True,
                         detail=f"HTTP {response.status}", evidenceRef=url)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return Check(name=name, status="fail", authoritative=True, detail=str(exc), evidenceRef=url)


def service_probe() -> Check:
    base = os.getenv("EVERKEEP_BASE_URL", "").strip().rstrip("/")
    if not base:
        return Check("everkeep:ready", "unknown", True, "EVERKEEP_BASE_URL not configured")
    return https_probe("everkeep:ready", "EVERKEEP_BASE_URL", "/ready")


def postgres_probe() -> Check:
    dsn = os.getenv("EVERKEEP_POSTGRES_DSN", "").strip()
    if not dsn:
        return Check("postgres:connectivity", "unknown", True, "EVERKEEP_POSTGRES_DSN not configured")
    try:
        import psycopg  # type: ignore
    except ImportError:
        return Check("postgres:connectivity", "unknown", True, "psycopg not installed in verifier runtime")
    try:
        with psycopg.connect(dsn, connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
                cur.execute("SELECT version FROM everkeep_schema_migrations ORDER BY version DESC LIMIT 1")
                row = cur.fetchone()
        return Check("postgres:connectivity", "pass", True, f"reachable; latest migration={row[0] if row else 'none'}")
    except Exception as exc:
        return Check("postgres:connectivity", "fail", True, str(exc))


def build_evidence(checks: list[Check]) -> dict:
    operational = bool(checks) and all(c.status == "pass" and c.authoritative for c in checks)
    return {
        "schemaVersion": "1.0.0",
        "environment": "staging",
        "capturedAt": now(),
        "sourceRevision": os.getenv("EVERKEEP_SOURCE_REVISION", "unknown"),
        "checks": [asdict(c) for c in checks],
        "operational": operational,
    }


def main() -> int:
    checks = [
        require_env("EVERKEEP_IDENTITY_ENDPOINT"),
        require_env("EVERKEEP_PRIVACY_ENDPOINT"),
        require_env("EVERKEEP_WARDVEIL_ENDPOINT"),
        require_env("EVERKEEP_MESH_ENDPOINT"),
        service_probe(),
        postgres_probe(),
        https_probe("identity:health", "EVERKEEP_IDENTITY_ENDPOINT", "/health"),
        https_probe("privacy:health", "EVERKEEP_PRIVACY_ENDPOINT", "/health"),
        https_probe("wardveil:health", "EVERKEEP_WARDVEIL_ENDPOINT", "/health"),
        https_probe("mesh:health", "EVERKEEP_MESH_ENDPOINT", "/health"),
    ]
    evidence = build_evidence(checks)
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["operational"] else 2


if __name__ == "__main__":
    sys.exit(main())
