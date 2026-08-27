#!/usr/bin/env python3
"""Append-only reference persistence for controlled Everkeep executor artifacts."""

from __future__ import annotations

import json
import sqlite3
from typing import Any


class FailoverExecutorStoreError(ValueError):
    pass


class FailoverExecutorStore:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS failover_executor_requests (
                request_id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                approval_id TEXT NOT NULL,
                plan_digest TEXT NOT NULL,
                state TEXT NOT NULL,
                artifact_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                CHECK (state IN ('accepted', 'blocked'))
            );
            CREATE INDEX IF NOT EXISTS failover_executor_requests_plan_idx
                ON failover_executor_requests(plan_id, created_at);

            CREATE TABLE IF NOT EXISTS failover_executor_states (
                execution_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                request_id TEXT NOT NULL,
                plan_id TEXT NOT NULL,
                state TEXT NOT NULL,
                artifact_json TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                PRIMARY KEY (execution_id, sequence),
                CHECK (state IN ('pending','validating','authorized','staging','executing','verifying','completed','blocked','failed','cancelled'))
            );
            CREATE INDEX IF NOT EXISTS failover_executor_states_plan_idx
                ON failover_executor_states(plan_id, observed_at);
            """
        )
        self.connection.commit()

    @staticmethod
    def _assert_safe(artifact: dict[str, Any]) -> None:
        if artifact.get("simulationOnly") is not True:
            raise FailoverExecutorStoreError("executor artifact must remain simulation-only")
        for field in ("externalEffectsAuthorized", "sourceMutationAllowed", "trafficMutationAllowed", "credentialsEmbedded"):
            if artifact.get(field) is not False:
                raise FailoverExecutorStoreError(f"unsafe executor artifact: {field}")

    def record_request(self, artifact: dict[str, Any]) -> None:
        self._assert_safe(artifact)
        state = "accepted" if artifact.get("handoffAccepted") is True else "blocked"
        try:
            self.connection.execute(
                """INSERT INTO failover_executor_requests
                   (request_id, plan_id, approval_id, plan_digest, state, artifact_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    artifact["requestId"], artifact["planId"], artifact["approvalId"], artifact["planDigest"], state,
                    json.dumps(artifact, sort_keys=True, separators=(",", ":")), artifact["requestedAt"],
                ),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            raise FailoverExecutorStoreError("duplicate or invalid executor request") from exc

    def append_state(self, artifact: dict[str, Any]) -> int:
        self._assert_safe(artifact)
        current = self.connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) AS sequence FROM failover_executor_states WHERE execution_id = ?",
            (artifact["executionId"],),
        ).fetchone()
        sequence = int(current["sequence"]) + 1
        self.connection.execute(
            """INSERT INTO failover_executor_states
               (execution_id, sequence, request_id, plan_id, state, artifact_json, observed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                artifact["executionId"], sequence, artifact["requestId"], artifact["planId"], artifact["state"],
                json.dumps(artifact, sort_keys=True, separators=(",", ":")), artifact["updatedAt"],
            ),
        )
        self.connection.commit()
        return sequence

    def latest_state(self, execution_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            """SELECT artifact_json FROM failover_executor_states
               WHERE execution_id = ? ORDER BY sequence DESC LIMIT 1""",
            (execution_id,),
        ).fetchone()
        return json.loads(row["artifact_json"]) if row else None

    def execution_history(self, execution_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """SELECT artifact_json FROM failover_executor_states
               WHERE execution_id = ? ORDER BY sequence ASC""",
            (execution_id,),
        ).fetchall()
        return [json.loads(row["artifact_json"]) for row in rows]
