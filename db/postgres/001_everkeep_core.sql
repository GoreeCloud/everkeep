BEGIN;

CREATE TABLE IF NOT EXISTS everkeep_resources (
  resource_id text PRIMARY KEY,
  payload jsonb NOT NULL,
  version bigint NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS everkeep_policies (
  policy_id text PRIMARY KEY,
  active_version bigint NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS everkeep_policy_versions (
  policy_id text NOT NULL REFERENCES everkeep_policies(policy_id) ON DELETE RESTRICT,
  version bigint NOT NULL,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (policy_id, version)
);

CREATE TABLE IF NOT EXISTS everkeep_recovery_points (
  recovery_point_id text PRIMARY KEY,
  resource_id text NOT NULL REFERENCES everkeep_resources(resource_id) ON DELETE RESTRICT,
  state text NOT NULL CHECK (state IN ('available','verifying','blocked','expired')),
  payload jsonb NOT NULL,
  version bigint NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS everkeep_recovery_points_resource_idx
  ON everkeep_recovery_points(resource_id, created_at DESC);

CREATE TABLE IF NOT EXISTS everkeep_retention_decisions (
  decision_id bigserial PRIMARY KEY,
  resource_id text NOT NULL REFERENCES everkeep_resources(resource_id) ON DELETE RESTRICT,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS everkeep_audit_events (
  sequence bigserial PRIMARY KEY,
  event_type text NOT NULL,
  resource_id text,
  actor_subject text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS everkeep_audit_resource_sequence_idx
  ON everkeep_audit_events(resource_id, sequence);

CREATE TABLE IF NOT EXISTS everkeep_adapter_state (
  adapter_id text PRIMARY KEY,
  cursor text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS everkeep_outbox (
  outbox_id bigserial PRIMARY KEY,
  event_id uuid NOT NULL UNIQUE,
  event_type text NOT NULL,
  aggregate_id text,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  available_at timestamptz NOT NULL DEFAULT now(),
  published_at timestamptz,
  attempts integer NOT NULL DEFAULT 0,
  last_error text
);

CREATE INDEX IF NOT EXISTS everkeep_outbox_pending_idx
  ON everkeep_outbox(available_at, outbox_id)
  WHERE published_at IS NULL;

CREATE TABLE IF NOT EXISTS everkeep_idempotency (
  idempotency_key text PRIMARY KEY,
  operation text NOT NULL,
  request_hash text NOT NULL,
  response jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz
);

CREATE TABLE IF NOT EXISTS everkeep_schema_migrations (
  version text PRIMARY KEY,
  checksum text NOT NULL,
  applied_at timestamptz NOT NULL DEFAULT now()
);

COMMIT;
