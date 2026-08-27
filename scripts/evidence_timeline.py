#!/usr/bin/env python3
"""Build deterministic, evidence-bounded per-resource timelines."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

CATEGORIES = {
    "protection", "integrity", "restore-test", "policy", "recovery", "retention",
    "dependency", "key-material", "preservation", "portability", "succession", "other",
}
STATES = {"pass", "fail", "unknown", "info"}


def _parse(value):
    if not value:
        raise ValueError("evidence observation requires observedAt")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def build_timeline(resource_id, records, generated_at=None):
    items = []
    for record in records:
        if record.get("resourceId") != resource_id:
            continue
        evidence_id = record.get("evidenceId")
        evidence_ref = record.get("evidenceRef")
        summary = record.get("summary")
        if not evidence_id or not evidence_ref or not summary:
            raise ValueError("timeline evidence requires evidenceId, evidenceRef, and summary")
        observed = _parse(record.get("observedAt"))
        category = record.get("category") if record.get("category") in CATEGORIES else "other"
        state = record.get("state") if record.get("state") in STATES else "unknown"
        items.append({
            "evidenceId": evidence_id,
            "category": category,
            "observedAt": observed.isoformat().replace("+00:00", "Z"),
            "state": state,
            "current": record.get("current") is True,
            "summary": summary,
            "evidenceRef": evidence_ref,
            "producer": record.get("producer"),
            "recoveryPointId": record.get("recoveryPointId"),
            "freshnessDeadline": record.get("freshnessDeadline"),
        })

    items.sort(key=lambda item: (_parse(item["observedAt"]), item["evidenceId"]), reverse=True)
    counts = Counter(item["state"] for item in items)
    latest = {}
    for item in items:
        if not item["current"] or item["category"] in latest:
            continue
        latest[item["category"]] = {
            "evidenceId": item["evidenceId"],
            "observedAt": item["observedAt"],
            "state": item["state"],
            "summary": item["summary"],
            "evidenceRef": item["evidenceRef"],
        }

    return {
        "schemaVersion": "1.0",
        "resourceId": resource_id,
        "generatedAt": generated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "counts": {
            "total": len(items),
            "pass": counts["pass"],
            "fail": counts["fail"],
            "unknown": counts["unknown"],
            "info": counts["info"],
        },
        "latestByCategory": dict(sorted(latest.items())),
        "items": items,
    }
