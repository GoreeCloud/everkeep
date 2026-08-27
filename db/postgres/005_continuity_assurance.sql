BEGIN;

CREATE TABLE IF NOT EXISTS everkeep_continuity_assurance_policies (
  policy_id text PRIMARY KEY,
  objective_id text NOT NULL,
  evaluation_interval_seconds bigint NOT NULL CHECK (evaluation_interval_seconds > 0),
  max_topology_age_seconds bigint NOT NULL CHECK (max_topology_age_seconds > 0),
  warning_lead_seconds bigint NOT NULL CHECK (warning_lead_seconds >= 0),
  monitoring_enabled boolean NOT NULL DEFAULT true,
  notify_enabled boolean NOT NULL DEFAULT true,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS everkeep_continuity_assurance_policies_objective_idx
  ON everkeep_continuity_assurance_policies(objective_id);

CREATE TABLE IF NOT EXISTS everkeep_continuity_assurance_evaluations (
  assurance_id text PRIMARY KEY,
  policy_id text NOT NULL REFERENCES everkeep_continuity_assurance_policies(policy_id) ON DELETE RESTRICT,
  objective_id text NOT NULL,
  state text NOT NULL CHECK (state IN ('ready','attention','degraded','unknown')),
  schedule_state text NOT NULL CHECK (schedule_state IN ('scheduled','due','overdue','unknown')),
  topology_state text NOT NULL CHECK (topology_state IN ('current','attention','stale','unknown')),
  evaluation_dispatch_eligible boolean NOT NULL DEFAULT false,
  payload jsonb NOT NULL,
  evaluated_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS everkeep_continuity_assurance_evaluations_objective_time_idx
  ON everkeep_continuity_assurance_evaluations(objective_id, evaluated_at DESC);

CREATE TABLE IF NOT EXISTS everkeep_continuity_signal_projections (
  signal_id text PRIMARY KEY,
  objective_id text NOT NULL,
  signal_type text NOT NULL CHECK (signal_type IN ('monitoring-metric','notify-intent')),
  projection_only boolean NOT NULL DEFAULT true CHECK (projection_only = true),
  delivery_attempted boolean NOT NULL DEFAULT false CHECK (delivery_attempted = false),
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS everkeep_continuity_signal_projections_objective_time_idx
  ON everkeep_continuity_signal_projections(objective_id, created_at DESC);

COMMIT;
