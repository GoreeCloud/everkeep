#!/usr/bin/env python3
"""Reference Everkeep service/API boundary.

This module deliberately avoids claiming production deployment. It provides
request/authorization/concurrency/outbox semantics that can sit behind HTTP or
GoreeCloud Mesh transports while reusing the persistent reference store.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from persistent_service import EverkeepStore


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def etag_for(value: Any) -> str:
    return '"' + hashlib.sha256(canonical_json(value).encode()).hexdigest() + '"'


@dataclass(frozen=True)
class Principal:
    subject: str
    permissions: frozenset[str]
    authenticated: bool = True
    reauthenticated: bool = False


class AuthorizationError(PermissionError):
    pass


class PreconditionFailed(RuntimeError):
    pass


class ServiceUnavailable(RuntimeError):
    pass


PERMISSIONS = {
    "resource.read": "everkeep.resource.read",
    "resource.write": "everkeep.resource.write",
    "policy.read": "everkeep.policy.read",
    "policy.write": "everkeep.policy.write",
    "recovery.read": "everkeep.recovery.read",
    "recovery.write": "everkeep.recovery.write",
    "recovery.transition": "everkeep.recovery.transition",
    "retention.write": "everkeep.retention.write",
    "audit.read": "everkeep.audit.read",
    "adapter.write": "everkeep.adapter.write",
}


class EverkeepService:
    """Transport-neutral service facade over EverkeepStore."""

    def __init__(self, store: EverkeepStore):
        self.store = store
        self._ensure_service_schema()

    def _ensure_service_schema(self) -> None:
        self.store.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS service_outbox (
              outbox_id INTEGER PRIMARY KEY AUTOINCREMENT,
              event_type TEXT NOT NULL,
              aggregate_id TEXT,
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL,
              published_at TEXT,
              attempts INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS idempotency_keys (
              key TEXT PRIMARY KEY,
              operation TEXT NOT NULL,
              request_hash TEXT NOT NULL,
              response TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS schema_migrations (
              version TEXT PRIMARY KEY,
              applied_at TEXT NOT NULL
            );
            """
        )
        self.store.db.commit()

    @staticmethod
    def _require(principal: Principal, permission: str, *, reauth: bool = False) -> None:
        if not principal.authenticated:
            raise AuthorizationError("authentication required")
        if permission not in principal.permissions:
            raise AuthorizationError(f"missing permission: {permission}")
        if reauth and not principal.reauthenticated:
            raise AuthorizationError("recent reauthentication required")

    def _enqueue(self, event_type: str, aggregate_id: str | None, payload: dict[str, Any]) -> None:
        self.store.db.execute(
            "INSERT INTO service_outbox(event_type,aggregate_id,payload,created_at) VALUES(?,?,?,?)",
            (event_type, aggregate_id, canonical_json(payload), utc_now()),
        )

    def _idempotent(self, key: str | None, operation: str, request: dict[str, Any], fn):
        if not key:
            return fn()
        request_hash = hashlib.sha256(canonical_json(request).encode()).hexdigest()
        row = self.store.db.execute(
            "SELECT operation,request_hash,response FROM idempotency_keys WHERE key=?", (key,)
        ).fetchone()
        if row:
            if row["operation"] != operation or row["request_hash"] != request_hash:
                raise PreconditionFailed("idempotency key reused with different request")
            return json.loads(row["response"])
        result = fn()
        self.store.db.execute(
            "INSERT INTO idempotency_keys(key,operation,request_hash,response,created_at) VALUES(?,?,?,?,?)",
            (key, operation, request_hash, canonical_json(result), utc_now()),
        )
        self.store.db.commit()
        return result

    def register_resource(self, principal: Principal, resource: dict[str, Any], idempotency_key: str | None = None):
        self._require(principal, PERMISSIONS["resource.write"])

        def action():
            result = self.store.register_resource(resource)
            self._enqueue("everkeep.resource.registered", resource["resourceId"], {"resourceId": resource["resourceId"]})
            self.store.db.commit()
            return {"resource": result, "etag": etag_for(result)}

        return self._idempotent(idempotency_key, "register_resource", resource, action)

    def get_resource(self, principal: Principal, resource_id: str):
        self._require(principal, PERMISSIONS["resource.read"])
        row = self.store.db.execute("SELECT payload FROM resources WHERE resource_id=?", (resource_id,)).fetchone()
        if not row:
            return None
        resource = json.loads(row["payload"])
        return {"resource": resource, "etag": etag_for(resource)}

    def save_policy(self, principal: Principal, policy: dict[str, Any], if_match: str | None = None):
        self._require(principal, PERMISSIONS["policy.write"], reauth=True)
        existing = self.store.get_policy(policy["policyId"])
        if existing is not None and if_match is not None and etag_for(existing) != if_match:
            raise PreconditionFailed("policy ETag mismatch")
        version = self.store.save_policy(policy)
        self._enqueue("everkeep.policy.version.created", policy["policyId"], {"policyId": policy["policyId"], "version": version})
        self.store.db.commit()
        return {"policy": policy, "version": version, "etag": etag_for(policy)}

    def get_policy(self, principal: Principal, policy_id: str, version: int | None = None):
        self._require(principal, PERMISSIONS["policy.read"])
        policy = self.store.get_policy(policy_id, version)
        return None if policy is None else {"policy": policy, "etag": etag_for(policy)}

    def ingest_recovery_point(self, principal: Principal, point: dict[str, Any], idempotency_key: str | None = None):
        self._require(principal, PERMISSIONS["recovery.write"])

        def action():
            result = self.store.ingest_recovery_point(point)
            self._enqueue("everkeep.recovery-point.created", point["resourceId"], {"recoveryPointId": point["recoveryPointId"]})
            self.store.db.commit()
            return {"recoveryPoint": result, "etag": etag_for(result)}

        return self._idempotent(idempotency_key, "ingest_recovery_point", point, action)

    def transition_recovery_point(self, principal: Principal, recovery_point_id: str, new_state: str):
        self._require(principal, PERMISSIONS["recovery.transition"], reauth=new_state in {"expired", "blocked"})
        state = self.store.transition_recovery_point(recovery_point_id, new_state)
        self._enqueue("everkeep.recovery-point.state.changed", recovery_point_id, {"recoveryPointId": recovery_point_id, "state": state})
        self.store.db.commit()
        return {"recoveryPointId": recovery_point_id, "state": state}

    def record_retention_decision(self, principal: Principal, resource_id: str, decision: dict[str, Any]):
        self._require(principal, PERMISSIONS["retention.write"], reauth=decision.get("decision") in {"delete", "expire"})
        self.store.record_retention_decision(resource_id, decision)
        self._enqueue("everkeep.retention.decision.recorded", resource_id, decision)
        self.store.db.commit()
        return {"resourceId": resource_id, "decision": decision}

    def recovery_center(self, principal: Principal, resource_id: str):
        self._require(principal, PERMISSIONS["recovery.read"])
        projection = self.store.recovery_center_projection(resource_id)
        return None if projection is None else {"projection": projection, "etag": etag_for(projection)}

    def list_resources(self, principal: Principal, limit=50, cursor=0, application=None, tier=None):
        self._require(principal, PERMISSIONS["resource.read"])
        limit = max(1, min(int(limit), 200))
        return self.store.list_resources(limit=limit, cursor=cursor, application=application, tier=tier)

    def audit_events(self, principal: Principal, after_sequence=0, limit=100):
        self._require(principal, PERMISSIONS["audit.read"])
        return self.store.audit_events(after_sequence=max(0, int(after_sequence)), limit=max(1, min(int(limit), 500)))

    def pending_outbox(self, limit=100):
        rows = self.store.db.execute(
            "SELECT outbox_id,event_type,aggregate_id,payload,created_at,attempts FROM service_outbox WHERE published_at IS NULL ORDER BY outbox_id LIMIT ?",
            (max(1, min(int(limit), 500)),),
        ).fetchall()
        return [dict(row) | {"payload": json.loads(row["payload"])} for row in rows]

    def mark_outbox_published(self, outbox_id: int):
        self.store.db.execute(
            "UPDATE service_outbox SET published_at=?, attempts=attempts+1 WHERE outbox_id=? AND published_at IS NULL",
            (utc_now(), outbox_id),
        )
        self.store.db.commit()

    def health(self) -> dict[str, Any]:
        try:
            self.store.db.execute("SELECT 1").fetchone()
            return {"status": "ok", "database": "reachable"}
        except sqlite3.Error:
            return {"status": "degraded", "database": "unreachable"}

    def readiness(self) -> dict[str, Any]:
        health = self.health()
        migration_table = self.store.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        ready = health["status"] == "ok" and migration_table is not None
        return {"status": "ready" if ready else "not_ready", "database": health["database"], "schema": "available" if migration_table else "missing"}
