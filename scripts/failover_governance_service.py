#!/usr/bin/env python3
"""Durable reference persistence for Everkeep failover governance artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FailoverGovernanceStoreExtension:
    def __init__(self, store):
        self.store = store
        self.db = store.db
        self._ensure_schema()

    def _ensure_schema(self):
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS failover_approval_decisions (
              approval_id TEXT PRIMARY KEY,
              plan_id TEXT NOT NULL,
              plan_digest TEXT NOT NULL,
              objective_id TEXT NOT NULL,
              state TEXT NOT NULL,
              evaluated_at TEXT NOT NULL,
              expires_at TEXT,
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS failover_approval_plan_time_idx
              ON failover_approval_decisions(plan_id, evaluated_at DESC);
            CREATE INDEX IF NOT EXISTS failover_approval_objective_time_idx
              ON failover_approval_decisions(objective_id, evaluated_at DESC);

            CREATE TABLE IF NOT EXISTS failover_acceptance_evidence (
              acceptance_id TEXT PRIMARY KEY,
              plan_id TEXT NOT NULL,
              plan_digest TEXT NOT NULL,
              execution_id TEXT NOT NULL,
              objective_id TEXT NOT NULL,
              environment TEXT NOT NULL,
              expected_revision TEXT NOT NULL,
              observed_revision TEXT NOT NULL,
              state TEXT NOT NULL,
              observed_at TEXT NOT NULL,
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS failover_acceptance_plan_time_idx
              ON failover_acceptance_evidence(plan_id, observed_at DESC);
            CREATE INDEX IF NOT EXISTS failover_acceptance_execution_time_idx
              ON failover_acceptance_evidence(execution_id, observed_at DESC);
            """
        )
        self.db.commit()

    def _audit(self, event_type: str, payload: dict[str, Any]):
        if hasattr(self.store, "_audit"):
            self.store._audit(event_type, None, payload)

    def save_approval(self, approval: dict[str, Any]):
        if approval.get("executionAuthorized") is not False:
            raise ValueError("failover approval cannot grant execution authority")
        if approval.get("executionCredential") is not False:
            raise ValueError("failover approval cannot be an execution credential")
        if approval.get("sourceMutationAllowed") is not False:
            raise ValueError("failover approval cannot permit source mutation")
        approval_id = approval["approvalId"]
        try:
            self.db.execute(
                """
                INSERT INTO failover_approval_decisions(
                  approval_id,plan_id,plan_digest,objective_id,state,evaluated_at,expires_at,payload,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    approval_id,
                    approval["planId"],
                    approval["planDigest"],
                    approval["objectiveId"],
                    approval["state"],
                    approval["evaluatedAt"],
                    approval.get("expiresAt"),
                    json.dumps(approval, sort_keys=True),
                    _now(),
                ),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise ValueError(f"failover approval already exists: {approval_id}") from exc
            raise
        self._audit(
            "everkeep.failover-approval.saved",
            {
                "approvalId": approval_id,
                "planId": approval["planId"],
                "state": approval["state"],
                "handoffEligible": approval["handoffEligible"],
            },
        )
        self.db.commit()
        return approval

    def get_approval(self, approval_id: str):
        row = self.db.execute(
            "SELECT payload FROM failover_approval_decisions WHERE approval_id=?",
            (approval_id,),
        ).fetchone()
        return json.loads(row["payload"]) if row else None

    def list_approvals(self, plan_id: str, limit: int = 50):
        rows = self.db.execute(
            """
            SELECT payload FROM failover_approval_decisions
            WHERE plan_id=?
            ORDER BY evaluated_at DESC, approval_id
            LIMIT ?
            """,
            (plan_id, max(1, min(int(limit), 200))),
        ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def save_acceptance(self, acceptance: dict[str, Any]):
        if acceptance.get("productionMutationAuthorized") is not False:
            raise ValueError("failover acceptance cannot authorize production mutation")
        acceptance_id = acceptance["acceptanceId"]
        try:
            self.db.execute(
                """
                INSERT INTO failover_acceptance_evidence(
                  acceptance_id,plan_id,plan_digest,execution_id,objective_id,environment,
                  expected_revision,observed_revision,state,observed_at,payload,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    acceptance_id,
                    acceptance["planId"],
                    acceptance["planDigest"],
                    acceptance["executionId"],
                    acceptance["objectiveId"],
                    acceptance["environment"],
                    acceptance["expectedRevision"],
                    acceptance["observedRevision"],
                    acceptance["state"],
                    acceptance["observedAt"],
                    json.dumps(acceptance, sort_keys=True),
                    _now(),
                ),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise ValueError(f"failover acceptance already exists: {acceptance_id}") from exc
            raise
        self._audit(
            "everkeep.failover-acceptance.saved",
            {
                "acceptanceId": acceptance_id,
                "planId": acceptance["planId"],
                "executionId": acceptance["executionId"],
                "state": acceptance["state"],
            },
        )
        self.db.commit()
        return acceptance

    def get_acceptance(self, acceptance_id: str):
        row = self.db.execute(
            "SELECT payload FROM failover_acceptance_evidence WHERE acceptance_id=?",
            (acceptance_id,),
        ).fetchone()
        return json.loads(row["payload"]) if row else None

    def list_acceptance_for_plan(self, plan_id: str, limit: int = 50):
        rows = self.db.execute(
            """
            SELECT payload FROM failover_acceptance_evidence
            WHERE plan_id=?
            ORDER BY observed_at DESC, acceptance_id
            LIMIT ?
            """,
            (plan_id, max(1, min(int(limit), 200))),
        ).fetchall()
        return [json.loads(row["payload"]) for row in rows]
