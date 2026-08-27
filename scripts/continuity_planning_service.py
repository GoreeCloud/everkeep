#!/usr/bin/env python3
"""Durable reference persistence for Everkeep recovery topology and plans."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ContinuityPlanningStoreExtension:
    def __init__(self, store):
        self.store = store
        self.db = store.db
        self._ensure_schema()

    def _ensure_schema(self):
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS continuity_topologies (
              topology_id TEXT PRIMARY KEY,
              payload TEXT NOT NULL,
              observed_at TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS continuity_failure_scenarios (
              scenario_id TEXT PRIMARY KEY,
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS continuity_failover_plans (
              plan_id TEXT PRIMARY KEY,
              objective_id TEXT NOT NULL,
              topology_id TEXT NOT NULL,
              scenario_id TEXT NOT NULL,
              state TEXT NOT NULL,
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS continuity_failover_plans_objective_time_idx
              ON continuity_failover_plans(objective_id, created_at DESC);
            """
        )
        self.db.commit()

    def _audit(self, event_type: str, payload: dict[str, Any]):
        if hasattr(self.store, "_audit"):
            self.store._audit(event_type, None, payload)

    def save_topology(self, topology: dict[str, Any]):
        topology_id = topology["topologyId"]
        ts = _now()
        self.db.execute(
            """
            INSERT INTO continuity_topologies(topology_id,payload,observed_at,created_at,updated_at)
            VALUES(?,?,?,?,?)
            ON CONFLICT(topology_id) DO UPDATE
              SET payload=excluded.payload, observed_at=excluded.observed_at, updated_at=excluded.updated_at
            """,
            (topology_id, json.dumps(topology, sort_keys=True), topology["observedAt"], ts, ts),
        )
        self._audit("everkeep.recovery-topology.saved", {"topologyId": topology_id})
        self.db.commit()
        return topology

    def get_topology(self, topology_id: str):
        row = self.db.execute(
            "SELECT payload FROM continuity_topologies WHERE topology_id=?",
            (topology_id,),
        ).fetchone()
        return json.loads(row["payload"]) if row else None

    def save_scenario(self, scenario: dict[str, Any]):
        scenario_id = scenario["scenarioId"]
        try:
            self.db.execute(
                "INSERT INTO continuity_failure_scenarios(scenario_id,payload,created_at) VALUES(?,?,?)",
                (scenario_id, json.dumps(scenario, sort_keys=True), _now()),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise ValueError(f"failure scenario already exists: {scenario_id}") from exc
            raise
        self._audit("everkeep.failure-scenario.saved", {"scenarioId": scenario_id})
        self.db.commit()
        return scenario

    def get_scenario(self, scenario_id: str):
        row = self.db.execute(
            "SELECT payload FROM continuity_failure_scenarios WHERE scenario_id=?",
            (scenario_id,),
        ).fetchone()
        return json.loads(row["payload"]) if row else None

    def save_plan(self, plan: dict[str, Any]):
        plan_id = plan["planId"]
        try:
            self.db.execute(
                """
                INSERT INTO continuity_failover_plans(
                  plan_id,objective_id,topology_id,scenario_id,state,payload,created_at
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    plan_id,
                    plan["objectiveId"],
                    plan["topologyId"],
                    plan["scenarioId"],
                    plan["state"],
                    json.dumps(plan, sort_keys=True),
                    plan["createdAt"],
                ),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise ValueError(f"failover plan already exists: {plan_id}") from exc
            raise
        self._audit(
            "everkeep.failover-plan.saved",
            {"planId": plan_id, "objectiveId": plan["objectiveId"], "state": plan["state"]},
        )
        self.db.commit()
        return plan

    def get_plan(self, plan_id: str):
        row = self.db.execute(
            "SELECT payload FROM continuity_failover_plans WHERE plan_id=?",
            (plan_id,),
        ).fetchone()
        return json.loads(row["payload"]) if row else None

    def list_plans(self, objective_id: str, limit: int = 50):
        rows = self.db.execute(
            """
            SELECT payload FROM continuity_failover_plans
            WHERE objective_id=?
            ORDER BY created_at DESC, plan_id
            LIMIT ?
            """,
            (objective_id, max(1, min(int(limit), 200))),
        ).fetchall()
        return [json.loads(row["payload"]) for row in rows]
