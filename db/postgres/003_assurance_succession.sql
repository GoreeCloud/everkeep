BEGIN;

CREATE TABLE IF NOT EXISTS everkeep_evidence_observations (
  observation_id text PRIMARY KEY,
  resource_id text NOT NULL REFERENCES everkeep_resources(resource_id) ON DELETE RESTRICT,
  category text NOT NULL CHECK (category IN ('protection','integrity','restore-test','policy','recovery','retention','dependency','key-material','preservation','portability','succession','other')),
  state text NOT NULL CHECK (state IN ('pass','fail','unknown','info')),
  current boolean NOT NULL DEFAULT false,
  observed_at timestamptz NOT NULL,
  evidence_ref text NOT NULL,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS everkeep_evidence_observations_resource_time_idx
  ON everkeep_evidence_observations(resource_id, observed_at DESC, observation_id DESC);

CREATE INDEX IF NOT EXISTS everkeep_evidence_observations_current_idx
  ON everkeep_evidence_observations(resource_id, category, observed_at DESC)
  WHERE current = true;

CREATE TABLE IF NOT EXISTS everkeep_restore_test_schedules (
  schedule_id text PRIMARY KEY,
  resource_id text NOT NULL REFERENCES everkeep_resources(resource_id) ON DELETE RESTRICT,
  policy_id text NOT NULL,
  temporal_state text NOT NULL CHECK (temporal_state IN ('scheduled','due','overdue','unknown')),
  dispatch_state text NOT NULL CHECK (dispatch_state IN ('ready','blocked','unknown')),
  next_due_at timestamptz,
  payload jsonb NOT NULL,
  evaluated_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS everkeep_restore_test_schedules_due_idx
  ON everkeep_restore_test_schedules(temporal_state, next_due_at)
  WHERE temporal_state IN ('due','overdue');

CREATE TABLE IF NOT EXISTS everkeep_succession_policies (
  policy_id text PRIMARY KEY,
  owner_subject text NOT NULL,
  status text NOT NULL CHECK (status IN ('draft','active','suspended','revoked')),
  version bigint NOT NULL DEFAULT 1,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS everkeep_succession_policies_owner_idx
  ON everkeep_succession_policies(owner_subject, status);

CREATE TABLE IF NOT EXISTS everkeep_succession_decisions (
  decision_id text PRIMARY KEY,
  policy_id text NOT NULL REFERENCES everkeep_succession_policies(policy_id) ON DELETE RESTRICT,
  state text NOT NULL CHECK (state IN ('inactive','eligible','blocked','unknown','revoked')),
  activation_eligible boolean NOT NULL DEFAULT false,
  payload jsonb NOT NULL,
  evaluated_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS everkeep_succession_decisions_policy_time_idx
  ON everkeep_succession_decisions(policy_id, evaluated_at DESC);

COMMIT;
