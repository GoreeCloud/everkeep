BEGIN;

CREATE TABLE IF NOT EXISTS everkeep_continuity_topologies (
  topology_id text PRIMARY KEY,
  scope jsonb NOT NULL,
  observed_at timestamptz NOT NULL,
  authoritative boolean NOT NULL DEFAULT false,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS everkeep_continuity_topologies_observed_idx
  ON everkeep_continuity_topologies(observed_at DESC);

CREATE TABLE IF NOT EXISTS everkeep_failure_scenarios (
  scenario_id text PRIMARY KEY,
  failure_type text NOT NULL,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS everkeep_failover_plans (
  plan_id text PRIMARY KEY,
  objective_id text NOT NULL,
  topology_id text NOT NULL REFERENCES everkeep_continuity_topologies(topology_id) ON DELETE RESTRICT,
  scenario_id text NOT NULL REFERENCES everkeep_failure_scenarios(scenario_id) ON DELETE RESTRICT,
  state text NOT NULL CHECK (state IN ('ready-for-approval','blocked','unknown')),
  execution_authorized boolean NOT NULL DEFAULT false CHECK (execution_authorized = false),
  source_mutation_allowed boolean NOT NULL DEFAULT false CHECK (source_mutation_allowed = false),
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS everkeep_failover_plans_objective_time_idx
  ON everkeep_failover_plans(objective_id, created_at DESC);

CREATE INDEX IF NOT EXISTS everkeep_failover_plans_state_idx
  ON everkeep_failover_plans(state, created_at DESC);

COMMIT;
