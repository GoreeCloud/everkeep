#!/usr/bin/env python3
"""PostgreSQL repository boundary for Everkeep.

The connection is injected and must implement Python DB-API 2.0 semantics. This
keeps production credentials and driver selection outside the repository layer.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class PostgresEverkeepRepository:
    def __init__(self, connection):
        self.db = connection

    def register_resource(self, resource: dict[str, Any]) -> dict[str, Any]:
        rid = resource["resourceId"]
        ts = now()
        with self.db.cursor() as cur:
            cur.execute(
                "INSERT INTO everkeep_resources(resource_id,payload,created_at,updated_at) VALUES(%s,%s::jsonb,%s,%s)",
                (rid, canonical(resource), ts, ts),
            )
            cur.execute(
                "INSERT INTO everkeep_audit_events(event_type,resource_id,payload,occurred_at) VALUES(%s,%s,%s::jsonb,%s)",
                ("everkeep.resource.registered", rid, canonical({"resourceId": rid}), ts),
            )
        self.db.commit()
        return resource

    def save_policy_version(self, policy: dict[str, Any]) -> int:
        pid = policy["policyId"]
        ts = now()
        with self.db.cursor() as cur:
            cur.execute("SELECT active_version FROM everkeep_policies WHERE policy_id=%s FOR UPDATE", (pid,))
            row = cur.fetchone()
            version = 1 if row is None else int(row[0]) + 1
            if row is None:
                cur.execute(
                    "INSERT INTO everkeep_policies(policy_id,active_version,created_at,updated_at) VALUES(%s,%s,%s,%s)",
                    (pid, version, ts, ts),
                )
            else:
                cur.execute(
                    "UPDATE everkeep_policies SET active_version=%s,updated_at=%s WHERE policy_id=%s",
                    (version, ts, pid),
                )
            cur.execute(
                "INSERT INTO everkeep_policy_versions(policy_id,version,payload,created_at) VALUES(%s,%s,%s::jsonb,%s)",
                (pid, version, canonical(policy), ts),
            )
        self.db.commit()
        return version

    def ingest_recovery_point(self, point: dict[str, Any]) -> dict[str, Any]:
        ts = now()
        with self.db.cursor() as cur:
            cur.execute(
                "INSERT INTO everkeep_recovery_points(recovery_point_id,resource_id,state,payload,created_at,updated_at) VALUES(%s,%s,%s,%s::jsonb,%s,%s)",
                (point["recoveryPointId"], point["resourceId"], point.get("state", "available"), canonical(point), ts, ts),
            )
        self.db.commit()
        return point

    def enqueue_event(self, event_type: str, aggregate_id: str | None, payload: dict[str, Any]) -> None:
        with self.db.cursor() as cur:
            cur.execute(
                "INSERT INTO everkeep_outbox(event_type,aggregate_id,payload,created_at) VALUES(%s,%s,%s::jsonb,%s)",
                (event_type, aggregate_id, canonical(payload), now()),
            )
        self.db.commit()

    def claim_outbox(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT outbox_id,event_type,aggregate_id,payload,attempts FROM everkeep_outbox WHERE published_at IS NULL ORDER BY outbox_id FOR UPDATE SKIP LOCKED LIMIT %s",
                (max(1, min(int(limit), 500)),),
            )
            rows = cur.fetchall()
        return [
            {"outbox_id": r[0], "event_type": r[1], "aggregate_id": r[2], "payload": r[3], "attempts": r[4]}
            for r in rows
        ]

    def mark_outbox_published(self, outbox_id: int) -> None:
        with self.db.cursor() as cur:
            cur.execute(
                "UPDATE everkeep_outbox SET published_at=%s,attempts=attempts+1 WHERE outbox_id=%s AND published_at IS NULL",
                (now(), outbox_id),
            )
        self.db.commit()
