#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Iterable

REQUIRED_CHECKS = {
    "everkeep.readiness",
    "postgres.migrations",
    "identity.authenticated-flow",
    "privacy.deliberate-denial",
    "wardveil.deliberate-denial",
    "mesh.delivery-retry",
    "adapter.cursor-restart",
    "runtime.durable-restart",
}

@dataclass(frozen=True)
class AcceptanceCheck:
    name: str
    status: str
    authoritative: bool
    evidence: dict[str, Any]


def evaluate(checks: Iterable[AcceptanceCheck], environment: str, source_revision: str) -> dict[str, Any]:
    checks = list(checks)
    by_name = {check.name: check for check in checks}
    complete = REQUIRED_CHECKS.issubset(by_name)
    accepted = complete and all(
        by_name[name].status == "pass" and by_name[name].authoritative
        for name in REQUIRED_CHECKS
    )
    return {
        "schemaVersion": "1.0",
        "environment": environment,
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "sourceRevision": source_revision,
        "checks": [asdict(check) for check in checks],
        "accepted": accepted,
    }


def failed_or_unknown(name: str, reason: str) -> AcceptanceCheck:
    return AcceptanceCheck(name=name, status="unknown", authoritative=False, evidence={"reason": reason})
