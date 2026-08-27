-- Everkeep Phase 3.3 failover governance persistence boundary.
-- These tables store governance evidence only. They never grant execution authority.

CREATE TABLE IF NOT EXISTS everkeep_failover_approvals (
    approval_id text PRIMARY KEY,
    plan_id text NOT NULL,
    plan_digest text NOT NULL CHECK (plan_digest ~ '^[a-f0-9]{64}$'),
    objective_id text NOT NULL,
    state text NOT NULL CHECK (state IN ('approved', 'denied', 'expired', 'unknown')),
    evaluated_at timestamptz NOT NULL,
    expires_at timestamptz,
    handoff_eligible boolean NOT NULL,
    execution_authorized boolean NOT NULL DEFAULT false CHECK (execution_authorized = false),
    execution_credential boolean NOT NULL DEFAULT false CHECK (execution_credential = false),
    source_mutation_allowed boolean NOT NULL DEFAULT false CHECK (source_mutation_allowed = false),
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((state = 'approved' AND handoff_eligible = true) OR (state <> 'approved' AND handoff_eligible = false))
);

CREATE INDEX IF NOT EXISTS everkeep_failover_approvals_plan_time_idx
    ON everkeep_failover_approvals(plan_id, evaluated_at DESC);
CREATE INDEX IF NOT EXISTS everkeep_failover_approvals_objective_time_idx
    ON everkeep_failover_approvals(objective_id, evaluated_at DESC);

CREATE TABLE IF NOT EXISTS everkeep_failover_acceptance (
    acceptance_id text PRIMARY KEY,
    plan_id text NOT NULL,
    plan_digest text NOT NULL CHECK (plan_digest ~ '^[a-f0-9]{64}$'),
    execution_id text NOT NULL,
    objective_id text NOT NULL,
    target_id text NOT NULL,
    environment text NOT NULL,
    expected_revision text NOT NULL,
    observed_revision text NOT NULL,
    state text NOT NULL CHECK (state IN ('pass', 'fail', 'unknown')),
    authoritative boolean NOT NULL,
    exact_revision_bound boolean NOT NULL,
    production_mutation_authorized boolean NOT NULL DEFAULT false CHECK (production_mutation_authorized = false),
    observed_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (state <> 'pass' OR (authoritative = true AND exact_revision_bound = true))
);

CREATE INDEX IF NOT EXISTS everkeep_failover_acceptance_plan_time_idx
    ON everkeep_failover_acceptance(plan_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS everkeep_failover_acceptance_execution_time_idx
    ON everkeep_failover_acceptance(execution_id, observed_at DESC);
