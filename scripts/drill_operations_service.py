#!/usr/bin/env python3
"""Append-only reference persistence for Everkeep Phase 3.5 drill operations."""

from __future__ import annotations

import json
import sqlite3
from typing import Any


class DrillOperationsStoreError(ValueError):
    pass


class DrillOperationsStore:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS failover_drill_dispatches (
                dispatch_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                plan_id TEXT NOT NULL,
                state TEXT NOT NULL CHECK (state IN ('accepted','blocked')),
                artifact_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS failover_drill_dispatches_plan_idx
                ON failover_drill_dispatches(plan_id, created_at);

            CREATE TABLE IF NOT EXISTS rollback_plans (
                rollback_plan_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                plan_id TEXT NOT NULL,
                state TEXT NOT NULL CHECK (state IN ('ready-for-drill','blocked','unknown')),
                artifact_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS rollback_plans_execution_idx
                ON rollback_plans(execution_id, created_at);

            CREATE TABLE IF NOT EXISTS rollback_evidence (
                rollback_evidence_id TEXT PRIMARY KEY,
                rollback_plan_id TEXT NOT NULL,
                execution_id TEXT NOT NULL,
                state TEXT NOT NULL CHECK (state IN ('pass','fail','unknown')),
                artifact_json TEXT NOT NULL,
                evaluated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS rollback_evidence_execution_idx
                ON rollback_evidence(execution_id, evaluated_at);

            CREATE TABLE IF NOT EXISTS continuity_signal_deliveries (
                delivery_id TEXT PRIMARY KEY,
                channel TEXT NOT NULL CHECK (channel IN ('monitoring','notify')),
                projection_id TEXT NOT NULL,
                objective_id TEXT NOT NULL,
                state TEXT NOT NULL CHECK (state IN ('accepted','rejected','failed','unknown')),
                artifact_json TEXT NOT NULL,
                attempted_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS continuity_signal_deliveries_objective_idx
                ON continuity_signal_deliveries(objective_id, attempted_at);
            """
        )
        self.connection.commit()

    @staticmethod
    def _assert_no_effect(artifact: dict[str, Any]) -> None:
        if artifact.get("simulationOnly") is not True:
            raise DrillOperationsStoreError("artifact must remain simulation-only")
        for field in ("externalEffectsAuthorized", "sourceMutationAllowed", "trafficMutationAllowed", "credentialsEmbedded"):
            if artifact.get(field) is not False:
                raise DrillOperationsStoreError(f"unsafe drill artifact: {field}")

    def save_dispatch(self, artifact: dict[str, Any]) -> None:
        self._assert_no_effect(artifact)
        try:
            self.connection.execute(
                """INSERT INTO failover_drill_dispatches
                   (dispatch_id, execution_id, request_id, plan_id, state, artifact_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    artifact["dispatchId"], artifact["executionId"], artifact["requestId"], artifact["planId"],
                    artifact["state"], json.dumps(artifact, sort_keys=True, separators=(",", ":")), artifact["requestedAt"],
                ),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            raise DrillOperationsStoreError("duplicate or invalid drill dispatch") from exc

    def save_rollback_plan(self, artifact: dict[str, Any]) -> None:
        self._assert_no_effect(artifact)
        if artifact.get("executionAuthorized") is not False or artifact.get("requiresApproval") is not True:
            raise DrillOperationsStoreError("rollback plan authority boundary invalid")
        try:
            self.connection.execute(
                """INSERT INTO rollback_plans
                   (rollback_plan_id, execution_id, plan_id, state, artifact_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    artifact["rollbackPlanId"], artifact["executionId"], artifact["planId"], artifact["state"],
                    json.dumps(artifact, sort_keys=True, separators=(",", ":")), artifact["createdAt"],
                ),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            raise DrillOperationsStoreError("duplicate or invalid rollback plan") from exc

    def save_rollback_evidence(self, artifact: dict[str, Any]) -> None:
        if artifact.get("simulationOnly") is not True or artifact.get("externalEffectsObserved") is not False:
            raise DrillOperationsStoreError("rollback evidence must describe a no-effect simulation")
        if artifact.get("productionMutationAuthorized") is not False:
            raise DrillOperationsStoreError("rollback evidence cannot authorize production mutation")
        try:
            self.connection.execute(
                """INSERT INTO rollback_evidence
                   (rollback_evidence_id, rollback_plan_id, execution_id, state, artifact_json, evaluated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    artifact["rollbackEvidenceId"], artifact["rollbackPlanId"], artifact["executionId"], artifact["state"],
                    json.dumps(artifact, sort_keys=True, separators=(",", ":")), artifact["evaluatedAt"],
                ),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            raise DrillOperationsStoreError("duplicate or invalid rollback evidence") from exc

    def save_signal_delivery(self, artifact: dict[str, Any]) -> None:
        if artifact.get("deliveryAttempted") is not True or artifact.get("sensitivePayloadsExcluded") is not True:
            raise DrillOperationsStoreError("signal delivery evidence boundary invalid")
        if artifact.get("credentialsEmbedded") is not False:
            raise DrillOperationsStoreError("signal delivery evidence cannot embed credentials")
        try:
            self.connection.execute(
                """INSERT INTO continuity_signal_deliveries
                   (delivery_id, channel, projection_id, objective_id, state, artifact_json, attempted_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    artifact["deliveryId"], artifact["channel"], artifact["projectionId"], artifact["objectiveId"],
                    artifact["state"], json.dumps(artifact, sort_keys=True, separators=(",", ":")), artifact["attemptedAt"],
                ),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            raise DrillOperationsStoreError("duplicate or invalid signal delivery evidence") from exc

    def list_signal_deliveries(self, objective_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """SELECT artifact_json FROM continuity_signal_deliveries
               WHERE objective_id = ? ORDER BY attempted_at DESC, delivery_id ASC""",
            (objective_id,),
        ).fetchall()
        return [json.loads(row["artifact_json"]) for row in rows]
