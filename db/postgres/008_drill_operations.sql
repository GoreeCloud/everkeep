-- Everkeep Phase 3.5 drill operations and rollback assurance persistence.
-- Source contract only; deployment and production effects require separate evidence.

CREATE TABLE IF NOT EXISTS everkeep_failover_drill_dispatches (
    dispatch_id text PRIMARY KEY,
    execution_id text NOT NULL,
    request_id text NOT NULL,
    plan_id text NOT NULL,
    plan_digest text NOT NULL CHECK (plan_digest ~ '^[a-f0-9]{64}$'),
    objective_id text NOT NULL,
    state text NOT NULL CHECK (state IN ('accepted','blocked')),
    requested_at timestamptz NOT NULL,
    simulation_only boolean NOT NULL CHECK (simulation_only = true),
    external_effects_authorized boolean NOT NULL CHECK (external_effects_authorized = false),
    source_mutation_allowed boolean NOT NULL CHECK (source_mutation_allowed = false),
    traffic_mutation_allowed boolean NOT NULL CHECK (traffic_mutation_allowed = false),
    credentials_embedded boolean NOT NULL CHECK (credentials_embedded = false),
    artifact jsonb NOT NULL
);

CREATE INDEX IF NOT EXISTS everkeep_failover_drill_dispatches_plan_idx
    ON everkeep_failover_drill_dispatches(plan_id, requested_at DESC);

CREATE TABLE IF NOT EXISTS everkeep_rollback_plans (
    rollback_plan_id text PRIMARY KEY,
    execution_id text NOT NULL,
    plan_id text NOT NULL,
    plan_digest text NOT NULL CHECK (plan_digest ~ '^[a-f0-9]{64}$'),
    objective_id text NOT NULL,
    state text NOT NULL CHECK (state IN ('ready-for-drill','blocked','unknown')),
    created_at timestamptz NOT NULL,
    requires_approval boolean NOT NULL CHECK (requires_approval = true),
    execution_authorized boolean NOT NULL CHECK (execution_authorized = false),
    simulation_only boolean NOT NULL CHECK (simulation_only = true),
    external_effects_authorized boolean NOT NULL CHECK (external_effects_authorized = false),
    source_mutation_allowed boolean NOT NULL CHECK (source_mutation_allowed = false),
    traffic_mutation_allowed boolean NOT NULL CHECK (traffic_mutation_allowed = false),
    credentials_embedded boolean NOT NULL CHECK (credentials_embedded = false),
    artifact jsonb NOT NULL
);

CREATE INDEX IF NOT EXISTS everkeep_rollback_plans_execution_idx
    ON everkeep_rollback_plans(execution_id, created_at DESC);

CREATE TABLE IF NOT EXISTS everkeep_rollback_evidence (
    rollback_evidence_id text PRIMARY KEY,
    rollback_plan_id text NOT NULL REFERENCES everkeep_rollback_plans(rollback_plan_id),
    execution_id text NOT NULL,
    plan_id text NOT NULL,
    plan_digest text NOT NULL CHECK (plan_digest ~ '^[a-f0-9]{64}$'),
    state text NOT NULL CHECK (state IN ('pass','fail','unknown')),
    evaluated_at timestamptz NOT NULL,
    authoritative boolean NOT NULL,
    exact_revision_bound boolean NOT NULL,
    simulation_only boolean NOT NULL CHECK (simulation_only = true),
    external_effects_observed boolean NOT NULL CHECK (external_effects_observed = false),
    production_mutation_authorized boolean NOT NULL CHECK (production_mutation_authorized = false),
    artifact jsonb NOT NULL,
    CHECK (state <> 'pass' OR (authoritative = true AND exact_revision_bound = true))
);

CREATE INDEX IF NOT EXISTS everkeep_rollback_evidence_execution_idx
    ON everkeep_rollback_evidence(execution_id, evaluated_at DESC);

CREATE TABLE IF NOT EXISTS everkeep_continuity_signal_deliveries (
    delivery_id text PRIMARY KEY,
    channel text NOT NULL CHECK (channel IN ('monitoring','notify')),
    projection_id text NOT NULL,
    objective_id text NOT NULL,
    state text NOT NULL CHECK (state IN ('accepted','rejected','failed','unknown')),
    authority text NOT NULL CHECK (authority IN ('goreecloud-monitoring','goreecloud-notify')),
    attempted_at timestamptz NOT NULL,
    delivery_attempted boolean NOT NULL CHECK (delivery_attempted = true),
    sensitive_payloads_excluded boolean NOT NULL CHECK (sensitive_payloads_excluded = true),
    credentials_embedded boolean NOT NULL CHECK (credentials_embedded = false),
    artifact jsonb NOT NULL,
    CHECK ((channel = 'monitoring' AND authority = 'goreecloud-monitoring') OR
           (channel = 'notify' AND authority = 'goreecloud-notify'))
);

CREATE INDEX IF NOT EXISTS everkeep_continuity_signal_deliveries_objective_idx
    ON everkeep_continuity_signal_deliveries(objective_id, attempted_at DESC);
