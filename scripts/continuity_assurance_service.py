#!/usr/bin/env python3
"""Durable reference storage for Everkeep continuity assurance evaluations."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ContinuityAssuranceStoreExtension:
    """Attach Phase 3 assurance policy, evaluation, and signal records to EverkeepStore.

    The extension stores reference artifacts only. It does not schedule workers,
    publish Monitoring metrics, deliver Notify alerts, or grant recovery authority.
    """

    def __init__(self, store):
        self.store = store
        self.db = store.db
        self._ensure_schema()

    def _ensure_schema(self):
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS continuity_assurance_policies (
              policy_id TEXT PRIMARY KEY,
              objective_id TEXT NOT NULL,
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS continuity_assurance_policies_objective_idx
              ON continuity_assurance_policies(objective_id);

            CREATE TABLE IF NOT EXISTS continuity_assurance_evaluations (
              assurance_id TEXT PRIMARY KEY,
              policy_id TEXT NOT NULL,
              objective_id TEXT NOT NULL,
              state TEXT NOT NULL,
              schedule_state TEXT NOT NULL,
              topology_state TEXT NOT NULL,
              payload TEXT NOT NULL,
              evaluated_at TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY (policy_id) REFERENCES continuity_assurance_policies(policy_id)
            );
            CREATE INDEX IF NOT EXISTS continuity_assurance_evaluations_objective_time_idx
              ON continuity_assurance_evaluations(objective_id, evaluated_at DESC);

            CREATE TABLE IF NOT EXISTS continuity_signal_projections (
              signal_id TEXT PRIMARY KEY,
              objective_id TEXT NOT NULL,
              signal_type TEXT NOT NULL CHECK(signal_type IN ('monitoring-metric','notify-intent')),
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS continuity_signal_projections_objective_time_idx
              ON continuity_signal_projections(objective_id, created_at DESC);
            """
        )
        self.db.commit()

    def save_policy(self, policy: dict[str, Any]):
        policy_id = policy["policyId"]
        objective_id = policy["objectiveId"]
        ts = _now()
        payload = json.dumps(policy, sort_keys=True)
        self.db.execute(
            """
            INSERT INTO continuity_assurance_policies(policy_id,objective_id,payload,created_at,updated_at)
            VALUES(?,?,?,?,?)
            ON CONFLICT(policy_id) DO UPDATE
              SET objective_id=excluded.objective_id,
                  payload=excluded.payload,
                  updated_at=excluded.updated_at
            """,
            (policy_id, objective_id, payload, ts, ts),
        )
        if hasattr(self.store, "_audit"):
            self.store._audit(
                "everkeep.continuity-assurance-policy.saved",
                None,
                {"policyId": policy_id, "objectiveId": objective_id},
            )
        self.db.commit()
        return policy

    def get_policy(self, policy_id: str):
        row = self.db.execute(
            "SELECT payload FROM continuity_assurance_policies WHERE policy_id=?",
            (policy_id,),
        ).fetchone()
        return json.loads(row["payload"]) if row else None

    def record_evaluation(self, assurance: dict[str, Any]):
        policy_id = assurance["policyId"]
        if self.get_policy(policy_id) is None:
            raise ValueError(f"continuity assurance policy does not exist: {policy_id}")
        assurance_id = assurance["assuranceId"]
        try:
            self.db.execute(
                """
                INSERT INTO continuity_assurance_evaluations(
                  assurance_id,policy_id,objective_id,state,schedule_state,topology_state,
                  payload,evaluated_at,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    assurance_id,
                    policy_id,
                    assurance["objectiveId"],
                    assurance["state"],
                    assurance["schedule"]["state"],
                    assurance["topologyFreshness"]["state"],
                    json.dumps(assurance, sort_keys=True),
                    assurance["evaluatedAt"],
                    _now(),
                ),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise ValueError(f"continuity assurance evaluation already exists: {assurance_id}") from exc
            raise
        if hasattr(self.store, "_audit"):
            self.store._audit(
                "everkeep.continuity-assurance.evaluated",
                None,
                {"assuranceId": assurance_id, "objectiveId": assurance["objectiveId"], "state": assurance["state"]},
            )
        self.db.commit()
        return assurance

    def list_evaluations(self, objective_id: str, limit: int = 50):
        rows = self.db.execute(
            """
            SELECT payload FROM continuity_assurance_evaluations
            WHERE objective_id=?
            ORDER BY evaluated_at DESC, assurance_id DESC
            LIMIT ?
            """,
            (objective_id, max(1, min(int(limit), 200))),
        ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def record_signal(self, signal_type: str, signal: dict[str, Any]):
        if signal_type == "monitoring-metric":
            signal_id = signal["metricId"]
        elif signal_type == "notify-intent":
            signal_id = signal["intentId"]
            if signal.get("deliveryAttempted") is not False:
                raise ValueError("notify intent must not claim delivery")
        else:
            raise ValueError("unsupported continuity signal type")

        if signal.get("projectionOnly") is not True:
            raise ValueError("continuity signal persistence accepts projection artifacts only")

        try:
            self.db.execute(
                """
                INSERT INTO continuity_signal_projections(signal_id,objective_id,signal_type,payload,created_at)
                VALUES(?,?,?,?,?)
                """,
                (signal_id, signal["objectiveId"], signal_type, json.dumps(signal, sort_keys=True), _now()),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise ValueError(f"continuity signal already exists: {signal_id}") from exc
            raise
        if hasattr(self.store, "_audit"):
            self.store._audit(
                "everkeep.continuity-signal.recorded",
                None,
                {"signalId": signal_id, "signalType": signal_type, "objectiveId": signal["objectiveId"]},
            )
        self.db.commit()
        return signal

    def list_signals(self, objective_id: str, limit: int = 100):
        rows = self.db.execute(
            """
            SELECT signal_type,payload FROM continuity_signal_projections
            WHERE objective_id=?
            ORDER BY created_at DESC, signal_id DESC
            LIMIT ?
            """,
            (objective_id, max(1, min(int(limit), 500))),
        ).fetchall()
        return [{"signalType": row["signal_type"], "payload": json.loads(row["payload"])} for row in rows]
