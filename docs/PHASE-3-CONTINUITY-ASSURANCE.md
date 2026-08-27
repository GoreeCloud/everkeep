# Everkeep Phase 3 — Scheduled Continuity Assurance and Signals

## Purpose

This Phase 3 increment turns Everkeep continuity posture from an on-demand calculation into a **scheduled continuity assurance** model.

It answers three operational questions without claiming live infrastructure that has not been evidenced:

1. When must a continuity objective be evaluated again?
2. When does authoritative recovery-topology evidence become too old to support planning?
3. What bounded state should be projected to GoreeCloud Monitoring and GoreeCloud Notify?

The implementation remains evidence bounded and **fail closed**. It does not schedule workers by itself, probe infrastructure, deliver alerts, send notifications, mutate recovery state, switch traffic, or authorize failover.

## Machine-readable contracts

This increment adds:

- `contracts/everkeep.continuity-assurance-policy.schema.json`
- `contracts/everkeep.continuity-assurance-state.schema.json`
- `contracts/everkeep.monitoring-metric.schema.json`
- `contracts/everkeep.notify-intent.schema.json`

### Assurance policy

A continuity assurance policy binds to one continuity objective and defines:

- evaluation interval;
- maximum recovery-topology age;
- warning lead time;
- whether Monitoring metric projections are enabled;
- whether Notify intent projections are enabled.

The policy does not invent an RPO, RTO, recovery-exercise cadence, or failure-domain target. Those remain owned by the continuity objective.

## Evaluation schedule

`scripts/continuity_assurance.py` derives one of four schedule states:

- `scheduled` — the next policy deadline is outside the warning window;
- `due` — evaluation is within the warning window or no prior evaluation is recorded;
- `overdue` — the policy deadline has passed;
- `unknown` — supplied evaluation timing evidence is malformed or cannot be verified.

A due or overdue schedule sets `evaluationDispatchEligible: true`. This is permission for a scheduler boundary to request evaluation work only; it is not recovery, failover, deployment, or notification authority.

## Recovery-topology freshness

Topology freshness is evaluated independently from continuity posture:

- `current` — authoritative topology evidence is inside the policy freshness window;
- `attention` — topology evidence is approaching expiry;
- `stale` — the maximum policy age has been exceeded;
- `unknown` — authoritative topology timing cannot be established.

Non-authoritative topology evidence remains unknown for assurance purposes. Stale topology cannot be converted into current state by documentation, a failover plan, or a consumer-side assumption.

## Aggregate assurance state

The aggregate assurance state uses conservative precedence:

- degraded continuity posture, overdue evaluation, or stale topology produces `degraded`;
- otherwise unknown posture, schedule, or topology produces `unknown`;
- otherwise attention posture, due evaluation, or topology nearing expiry produces `attention`;
- only current evidence with a scheduled evaluation and ready posture produces `ready`.

This state is an assurance projection. It does not replace the underlying continuity posture or its evidence.

## GoreeCloud Monitoring

`build_monitoring_metrics` emits bounded metric projections for:

- continuity assurance state;
- evaluation overdue seconds;
- recovery-topology age;
- failover eligibility.

Every Monitoring metric is marked `projectionOnly: true` and `sensitivePayloadsExcluded: true`.

Everkeep does not claim that GoreeCloud Monitoring has ingested, retained, alerted on, or displayed these metrics until an actual Monitoring adapter provides runtime evidence.

## GoreeCloud Notify

`build_notify_intents` produces deduplicated Notify intents for:

- degraded, unknown, or attention continuity posture;
- due, overdue, or unknown continuity evaluation timing;
- stale, unknown, or expiring recovery topology.

Every intent identifies `deliveryAuthority: goreecloud-notify`, sets `projectionOnly: true`, sets `deliveryAttempted: false`, and excludes sensitive recovery payloads.

Everkeep **does not deliver alerts**. GoreeCloud Notify remains responsible for downstream delivery policy, destinations, quiet-hours behavior, user preferences, escalation, retries, and proof of successful delivery.

## Durable reference storage

`scripts/continuity_assurance_service.py` adds reference persistence for:

- assurance policies;
- assurance evaluation history;
- Monitoring metric projections;
- Notify intent projections.

`db/postgres/005_continuity_assurance.sql` defines a PostgreSQL-oriented storage boundary with database constraints that prevent stored signal projections from representing actual publication or alert delivery.

These tables are evidence and projection storage, not a job scheduler or message-delivery system.

## Recovery Center 1.4

Recovery Center schema 1.4 adds fleet-level continuity assurance schedule coverage:

- scheduled;
- due;
- overdue;
- unknown.

Evidence-backed actions now include:

- `evaluate-continuity-now` when an assurance evaluation is due or overdue;
- `inspect-continuity-assurance` when scheduling state cannot be verified.

The existing failover-plan gate remains unchanged: continuity must be ready, failover eligibility must be true, and topology evidence must be current before Recovery Center may expose plan creation.

## Platform boundaries

### GoreeCloud Mesh

Mesh may coordinate assurance policy identifiers, evaluation requests, evaluation state, metric projections, and Notify intents. Mesh cannot manufacture freshness, extend evidence validity, or grant failover authority.

### Privacy Shield

Privacy Shield remains authoritative over copying, retention, restoration, transfer, and alternate-environment placement. Scheduled assurance cannot override a privacy denial.

### Wardveil Security

Wardveil remains authoritative for security evidence used by recovery and promotion decisions. An assurance schedule cannot convert unknown or failed security evidence into readiness.

### GoreeCloud Identity

Identity remains authoritative for principals, service identities, reauthentication, privileged operations, and future approval workflows.

### Glaze UI

Glaze UI should distinguish continuity posture from assurance timing. A resource can have a currently ready posture while its next evaluation is due; those states must not be collapsed into a single decorative badge.

## Explicit non-claims

This increment does not:

- run a background scheduler;
- poll live infrastructure;
- discover failure domains automatically;
- refresh topology automatically;
- execute a disaster-recovery drill;
- publish a Monitoring metric;
- deliver a Notify alert;
- switch traffic;
- execute or approve failover;
- provision an alternate environment;
- establish production continuity acceptance.

## Next implementation boundary

The next Phase 3 increment should connect these projections to authoritative runtime producers while preserving the same evidence rules:

- live failure-domain and dependency inventory adapters;
- bounded disaster-recovery drill automation;
- actual GoreeCloud Monitoring ingestion adapter;
- actual GoreeCloud Notify delivery adapter;
- separate operator/Identity/Privacy Shield/Wardveil approval contracts;
- controlled failover execution state machine;
- revision- and environment-bound failover acceptance evidence.

None of those capabilities should be represented as deployed until runtime evidence proves them.
