#!/usr/bin/env python3
import json
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS resources (
  resource_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS policies (
  policy_id TEXT PRIMARY KEY,
  active_version INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS policy_versions (
  policy_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (policy_id, version),
  FOREIGN KEY (policy_id) REFERENCES policies(policy_id)
);
CREATE TABLE IF NOT EXISTS recovery_points (
  recovery_point_id TEXT PRIMARY KEY,
  resource_id TEXT NOT NULL,
  state TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (resource_id) REFERENCES resources(resource_id)
);
CREATE TABLE IF NOT EXISTS retention_decisions (
  decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
  resource_id TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (resource_id) REFERENCES resources(resource_id)
);
CREATE TABLE IF NOT EXISTS audit_events (
  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,
  resource_id TEXT,
  payload TEXT NOT NULL,
  occurred_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS adapter_state (
  adapter_id TEXT PRIMARY KEY,
  cursor TEXT,
  payload TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""


def now():
    return datetime.now(timezone.utc).isoformat()


class EverkeepStore:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.execute("PRAGMA journal_mode=WAL")

    def _audit(self, event_type, resource_id=None, payload=None):
        self.db.execute(
            "INSERT INTO audit_events(event_type, resource_id, payload, occurred_at) VALUES(?,?,?,?)",
            (event_type, resource_id, json.dumps(payload or {}, sort_keys=True), now()),
        )

    def register_resource(self, resource):
        rid = resource["resourceId"]
        ts = now()
        try:
            self.db.execute(
                "INSERT INTO resources(resource_id,payload,created_at,updated_at) VALUES(?,?,?,?)",
                (rid, json.dumps(resource, sort_keys=True), ts, ts),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"resource already exists: {rid}") from exc
        self._audit("everkeep.resource.registered", rid, {"resourceId": rid})
        self.db.commit()
        return resource

    def save_policy(self, policy):
        pid = policy["policyId"]
        ts = now()
        row = self.db.execute("SELECT active_version FROM policies WHERE policy_id=?", (pid,)).fetchone()
        version = 1 if row is None else int(row["active_version"]) + 1
        if row is None:
            self.db.execute("INSERT INTO policies(policy_id,active_version,created_at,updated_at) VALUES(?,?,?,?)", (pid, version, ts, ts))
        else:
            self.db.execute("UPDATE policies SET active_version=?, updated_at=? WHERE policy_id=?", (version, ts, pid))
        self.db.execute("INSERT INTO policy_versions(policy_id,version,payload,created_at) VALUES(?,?,?,?)", (pid, version, json.dumps(policy, sort_keys=True), ts))
        self._audit("everkeep.policy.version.created", None, {"policyId": pid, "version": version})
        self.db.commit()
        return version

    def get_policy(self, policy_id, version=None):
        if version is None:
            row = self.db.execute("SELECT active_version FROM policies WHERE policy_id=?", (policy_id,)).fetchone()
            if not row:
                return None
            version = row["active_version"]
        row = self.db.execute("SELECT payload FROM policy_versions WHERE policy_id=? AND version=?", (policy_id, version)).fetchone()
        return json.loads(row["payload"]) if row else None

    def ingest_recovery_point(self, point):
        rpid = point["recoveryPointId"]
        rid = point["resourceId"]
        state = point.get("state", "available")
        ts = now()
        try:
            self.db.execute("INSERT INTO recovery_points(recovery_point_id,resource_id,state,payload,created_at,updated_at) VALUES(?,?,?,?,?,?)", (rpid, rid, state, json.dumps(point, sort_keys=True), ts, ts))
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"recovery point already exists or resource missing: {rpid}") from exc
        self._audit("everkeep.recovery-point.created", rid, {"recoveryPointId": rpid, "state": state})
        self.db.commit()
        return point

    def transition_recovery_point(self, recovery_point_id, new_state):
        allowed = {
            "available": {"verifying", "expired", "blocked"},
            "verifying": {"available", "blocked"},
            "blocked": {"verifying", "expired"},
            "expired": set(),
        }
        row = self.db.execute("SELECT resource_id,state,payload FROM recovery_points WHERE recovery_point_id=?", (recovery_point_id,)).fetchone()
        if not row:
            raise KeyError(recovery_point_id)
        current = row["state"]
        if new_state not in allowed.get(current, set()):
            raise ValueError(f"invalid recovery-point transition: {current} -> {new_state}")
        payload = json.loads(row["payload"])
        payload["state"] = new_state
        self.db.execute("UPDATE recovery_points SET state=?,payload=?,updated_at=? WHERE recovery_point_id=?", (new_state, json.dumps(payload, sort_keys=True), now(), recovery_point_id))
        self._audit("everkeep.recovery-point.state.changed", row["resource_id"], {"recoveryPointId": recovery_point_id, "from": current, "to": new_state})
        self.db.commit()
        return new_state

    def record_retention_decision(self, resource_id, decision):
        self.db.execute("INSERT INTO retention_decisions(resource_id,payload,created_at) VALUES(?,?,?)", (resource_id, json.dumps(decision, sort_keys=True), now()))
        self._audit("everkeep.retention.decision.recorded", resource_id, decision)
        self.db.commit()

    def list_resources(self, limit=50, cursor=0, application=None, tier=None):
        clauses, args = [], []
        rows = self.db.execute("SELECT resource_id,payload FROM resources ORDER BY resource_id").fetchall()
        decoded = [json.loads(r["payload"]) for r in rows]
        if application:
            decoded = [r for r in decoded if r.get("application") == application]
        if tier:
            decoded = [r for r in decoded if r.get("preservationTier") == tier]
        start = int(cursor or 0)
        page = decoded[start:start + limit]
        next_cursor = start + len(page) if start + len(page) < len(decoded) else None
        return {"items": page, "nextCursor": next_cursor, "total": len(decoded)}

    def audit_events(self, after_sequence=0, limit=100):
        rows = self.db.execute("SELECT sequence,event_type,resource_id,payload,occurred_at FROM audit_events WHERE sequence>? ORDER BY sequence LIMIT ?", (after_sequence, limit)).fetchall()
        return [dict(r) | {"payload": json.loads(r["payload"])} for r in rows]

    def set_adapter_state(self, adapter_id, cursor, payload=None):
        self.db.execute(
            "INSERT INTO adapter_state(adapter_id,cursor,payload,updated_at) VALUES(?,?,?,?) ON CONFLICT(adapter_id) DO UPDATE SET cursor=excluded.cursor,payload=excluded.payload,updated_at=excluded.updated_at",
            (adapter_id, cursor, json.dumps(payload or {}, sort_keys=True), now()),
        )
        self.db.commit()

    def recovery_center_projection(self, resource_id):
        resource_row = self.db.execute("SELECT payload FROM resources WHERE resource_id=?", (resource_id,)).fetchone()
        if not resource_row:
            return None
        points = self.db.execute("SELECT recovery_point_id,state,payload,created_at FROM recovery_points WHERE resource_id=? ORDER BY created_at DESC", (resource_id,)).fetchall()
        latest_retention = self.db.execute("SELECT payload,created_at FROM retention_decisions WHERE resource_id=? ORDER BY decision_id DESC LIMIT 1", (resource_id,)).fetchone()
        return {
            "resource": json.loads(resource_row["payload"]),
            "recoveryPoints": [json.loads(p["payload"]) for p in points],
            "retentionDecision": json.loads(latest_retention["payload"]) if latest_retention else None,
            "auditSequence": self.db.execute("SELECT COALESCE(MAX(sequence),0) AS s FROM audit_events WHERE resource_id=?", (resource_id,)).fetchone()["s"],
        }
