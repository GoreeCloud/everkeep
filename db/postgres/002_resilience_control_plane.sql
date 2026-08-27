BEGIN;

CREATE TABLE IF NOT EXISTS everkeep_recovery_plans (
  plan_id text PRIMARY KEY,
  mode text NOT NULL CHECK (mode IN ('dry-run','sandbox','restore')),
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS everkeep_recovery_executions (
  execution_id text PRIMARY KEY,
  plan_id text NOT NULL REFERENCES everkeep_recovery_plans(plan_id) ON DELETE RESTRICT,
  state text NOT NULL CHECK (state IN ('pending','authorized','running','verifying','completed','blocked','failed','cancelled')),
  environment text NOT NULL,
  authorized boolean NOT NULL DEFAULT false,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);

CREATE INDEX IF NOT EXISTS everkeep_recovery_executions_plan_idx
  ON everkeep_recovery_executions(plan_id, created_at DESC);

CREATE TABLE IF NOT EXISTS everkeep_preservation_capsules (
  capsule_id text PRIMARY KEY,
  preservation_tier text NOT NULL CHECK (preservation_tier IN ('protected','archive','permanent')),
  integrity_state text NOT NULL CHECK (integrity_state IN ('verified','failed','unknown')),
  capsule_digest text NOT NULL,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS everkeep_preservation_capsule_digest_idx
  ON everkeep_preservation_capsules(capsule_digest);

CREATE TABLE IF NOT EXISTS everkeep_portability_exports (
  export_id text PRIMARY KEY,
  capsule_id text NOT NULL REFERENCES everkeep_preservation_capsules(capsule_id) ON DELETE RESTRICT,
  authority_state text NOT NULL CHECK (authority_state IN ('pass','fail','unknown')),
  integrity_state text NOT NULL CHECK (integrity_state IN ('verified','failed','unknown')),
  portable boolean NOT NULL DEFAULT false,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS everkeep_portability_exports_capsule_idx
  ON everkeep_portability_exports(capsule_id, created_at DESC);

COMMIT;
