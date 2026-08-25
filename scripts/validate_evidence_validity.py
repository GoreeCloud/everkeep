#!/usr/bin/env python3
"""Fail-closed validation for Everkeep continuity evidence freshness."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_SCHEMA = ROOT / "contracts" / "continuity.status.schema.json"
ACCEPTANCE_SCHEMA = ROOT / "contracts" / "continuity.acceptance.schema.json"
DOC = ROOT / "docs" / "evidence-validity.md"


def fail(message: str) -> None:
    raise SystemExit(f"Everkeep evidence-validity validation failed: {message}")


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"{path.relative_to(ROOT)} is unreadable or invalid JSON: {exc}")
    if not isinstance(value, dict):
        fail(f"{path.relative_to(ROOT)} must contain an object")
    return value


def main() -> None:
    schema = load(STATUS_SCHEMA)
    properties = schema.get("properties", {})
    if properties.get("observed_at", {}).get("format") != "date-time":
        fail("observed_at must remain a date-time")
    fresh_until = properties.get("fresh_until", {})
    if fresh_until.get("format") != "date-time":
        fail("fresh_until must remain a date-time")

    rules = schema.get("allOf")
    if not isinstance(rules, list) or not rules:
        fail("status schema must contain a ready-state freshness rule")
    serialized = json.dumps(rules, sort_keys=True)
    for marker in ('"ready"', '"fresh_until"', '"string"'):
        if marker not in serialized:
            fail(f"ready-state freshness rule is missing {marker}")

    acceptance = load(ACCEPTANCE_SCHEMA)
    acceptance_text = json.dumps(acceptance, sort_keys=True)
    if "required_for_ready" not in acceptance_text:
        fail("acceptance schema must preserve required-for-ready freshness semantics")

    try:
        documentation = DOC.read_text(encoding="utf-8").lower()
    except OSError as exc:
        fail(f"missing evidence-validity documentation: {exc}")
    for phrase in ("fresh_until", "ready", "producer", "mesh", "extend"):
        if phrase not in documentation:
            fail(f"evidence-validity documentation is missing required concept: {phrase}")

    print("Everkeep evidence-validity contract validation passed.")


if __name__ == "__main__":
    main()
