-- Everkeep Phase 3.4 controlled failover executor persistence boundary.
-- Reference schema only; it does not authorize external effects or traffic mutation.

CREATE TABLE IF NOT EXISTS everkeep_failover_executor_requests (
    request_id text PRIMARY KEY,
    approval_id text NOT NULL,
    plan_id text NOT NULL,
    plan_digest text NOT NULL CHECK (plan_digest ~ '^[a-f0-9]{64}$'),
    objective_id text NOT NULL,
    mode text NOT NULL CHECK (mode = 'drill'),
    target_id text NOT NULL,
    environment text NOT NULL,
    expected_revision text NOT NULL,
    requested_at timestamptz NOT NULL,
    approval_expires_at timestamptz NOT NULL,
    handoff_accepted boolean NOT NULL,
    simulation_only boolean NOT NULL CHECK (simulation_only = true),
    external_effects_authorized boolean NOT NULL CHECK (external_effects_authorized = false),
    source_mutation_allowed boolean NOT NULL CHECK (source_mutation_allowed = false),
    traffic_mutation_allowed boolean NOT NULL CHECK (traffic_mutation_allowed = false),
    credentials_embedded boolean NOT NULL CHECK (credentials_embedded = false),
    artifact jsonb NOT NULL
);

CREATE INDEX IF NOT EXISTS everkeep_failover_executor_requests_plan_idx
    ON everkeep_failover_executor_requests(plan_id, requested_at DESC);

CREATE TABLE IF NOT EXISTS everkeep_failover_executor_states (
    execution_id text NOT NULL,
    sequence bigint NOT NULL,
    request_id text NOT NULL REFERENCES everkeep_failover_executor_requests(request_id),
    plan_id text NOT NULL,
    plan_digest text NOT NULL CHECK (plan_digest ~ '^[a-f0-9]{64}$'),
    state text NOT NULL CHECK (state IN ('pending','validating','authorized','staging','executing','verifying','completed','blocked','failed','cancelled')),
    current_step_index integer NOT NULL CHECK (current_step_index >= 0),
    observed_at timestamptz NOT NULL,
    simulation_only boolean NOT NULL CHECK (simulation_only = true),
    external_effects_authorized boolean NOT NULL CHECK (external_effects_authorized = false),
    source_mutation_allowed boolean NOT NULL CHECK (source_mutation_allowed = false),
    traffic_mutation_allowed boolean NOT NULL CHECK (traffic_mutation_allowed = false),
    credentials_embedded boolean NOT NULL CHECK (credentials_embedded = false),
    artifact jsonb NOT NULL,
    PRIMARY KEY (execution_id, sequence)
);

CREATE INDEX IF NOT EXISTS everkeep_failover_executor_states_plan_idx
    ON everkeep_failover_executor_states(plan_id, observed_at DESC);
