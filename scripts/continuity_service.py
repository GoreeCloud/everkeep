#!/usr/bin/env python3
"""Durable reference storage for Everkeep continuity objectives and exercises."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from continuity import evaluate_continuity


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ContinuityStoreExtension:
    """Attach Phase 3 continuity state to an existing EverkeepStore.

    The extension uses the store's existing SQLite/DB-API connection and audit
    boundary. It is intentionally transport-neutral and does not perform probes
    or failover itself.
    """

    def __init__(self, store):
        self.store = store
        self.db = store.db
        self._ensure_schema()

    def _ensure_schema(self):
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS continuity_objectives (
              objective_id TEXT PRIMARY KEY,
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recovery_exercises (
              exercise_id TEXT PRIMARY KEY,
              objective_id TEXT NOT NULL,
              result TEXT NOT NULL,
              payload TEXT NOT NULL,
              started_at TEXT NOT NULL,
              finished_at TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY (objective_id) REFERENCES continuity_objectives(objective_id)
            );
            CREATE INDEX IF NOT EXISTS recovery_exercises_objective_finished_idx
              ON recovery_exercises(objective_id, finished_at DESC);
            """
        )
        self.db.commit()

    def save_objective(self, objective: dict[str, Any]):
        objective_id = objective["objectiveId"]
        ts = _now()
        payload = json.dumps(objective, sort_keys=True)
        self.db.execute(
            """
            INSERT INTO continuity_objectives(objective_id,payload,created_at,updated_at)
            VALUES(?,?,?,?)
            ON CONFLICT(objective_id) DO UPDATE
              SET payload=excluded.payload, updated_at=excluded.updated_at
            """,
            (objective_id, payload, ts, ts),
        )
        if hasattr(self.store, "_audit"):
            self.store._audit("everkeep.continuity-objective.saved", None, {"objectiveId": objective_id})
        self.db.commit()
        return objective

    def get_objective(self, objective_id: str):
        row = self.db.execute(
            "SELECT payload FROM continuity_objectives WHERE objective_id=?",
            (objective_id,),
        ).fetchone()
        return json.loads(row["payload"]) if row else None

    def record_exercise(self, exercise: dict[str, Any]):
        exercise_id = exercise["exerciseId"]
        objective_id = exercise["objectiveId"]
        if self.get_objective(objective_id) is None:
            raise ValueError(f"continuity objective does not exist: {objective_id}")
        try:
            self.db.execute(
                """
                INSERT INTO recovery_exercises(
                  exercise_id,objective_id,result,payload,started_at,finished_at,created_at
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    exercise_id,
                    objective_id,
                    exercise["result"],
                    json.dumps(exercise, sort_keys=True),
                    exercise["startedAt"],
                    exercise["finishedAt"],
                    _now(),
                ),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise ValueError(f"recovery exercise already exists: {exercise_id}") from exc
            raise
        if hasattr(self.store, "_audit"):
            self.store._audit(
                "everkeep.recovery-exercise.recorded",
                None,
                {"exerciseId": exercise_id, "objectiveId": objective_id, "result": exercise["result"]},
            )
        self.db.commit()
        return exercise

    def list_exercises(self, objective_id: str, limit: int = 50):
        rows = self.db.execute(
            """
            SELECT payload FROM recovery_exercises
            WHERE objective_id=?
            ORDER BY finished_at DESC, exercise_id
            LIMIT ?
            """,
            (objective_id, max(1, min(int(limit), 200))),
        ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def posture(self, objective_id: str, evidence: dict[str, Any], observed_at: str | None = None):
        objective = self.get_objective(objective_id)
        if objective is None:
            return None
        return evaluate_continuity(objective, evidence, observed_at)
