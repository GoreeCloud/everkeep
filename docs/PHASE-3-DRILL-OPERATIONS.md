# Everkeep Phase 3.5 — Drill Operations and Rollback Assurance

## Purpose

Phase 3.5 continues Everkeep from the Phase 3.4 controlled executor boundary into bounded disaster-recovery drill operations, explicit rollback assurance, Recovery Center operational visibility, read-only live-authority adapter boundaries, and runtime-capable GoreeCloud Monitoring and GoreeCloud Notify signal delivery.

This increment does not establish production failover. The drill worker remains simulation-only and performs no infrastructure provisioning, production data movement, DNS/routing changes, traffic switching, source mutation, or production rollback.

## Controlled drill dispatch

`contracts/everkeep.failover-drill-dispatch.schema.json` binds one accepted Phase 3.4 executor request to one controlled drill execution ID. Dispatch is tied to the exact plan digest, objective, target, expected revision, current request evidence, and the existing approval validity deadline.

Dispatch fails closed when:

- the Phase 3.4 handoff was not accepted;
- a safety invariant was modified;
- the plan digest changed;
- objective or target binding changed;
- approval expiry is missing;
- the approval validity deadline has passed.

Every dispatch permanently carries:

- `simulationOnly: true`;
- `externalEffectsAuthorized: false`;
- `sourceMutationAllowed: false`;
- `trafficMutationAllowed: false`;
- `credentialsEmbedded: false`.

## Bounded drill worker

`scripts/drill_operations.py` advances an accepted dispatch through the existing Phase 3.4 executor lifecycle:

1. pending;
2. validating;
3. authorized;
4. staging;
5. executing;
6. verifying;
7. completed.

The worker records each plan step while the state is `executing`. Step processing is evidence bookkeeping only. The worker does not invoke plan actions against an external system.

A dispatch that is blocked or unsafe produces a blocked execution record rather than an optimistic state. Exact plan digest binding is rechecked before the drill begins.

## Rollback assurance

### Rollback plan

`contracts/everkeep.rollback-plan.schema.json` defines a reverse-order rollback rehearsal plan derived from the completed step history of a controlled drill.

The rollback sequence reverses completed drill step identifiers and represents every rollback action as `simulate-rollback-step` with `externalEffect: false`.

A rollback plan can be `ready-for-drill`, `blocked`, or `unknown`. It permanently requires:

- `requiresApproval: true`;
- `executionAuthorized: false`;
- `simulationOnly: true`;
- `externalEffectsAuthorized: false`;
- `sourceMutationAllowed: false`;
- `trafficMutationAllowed: false`;
- `credentialsEmbedded: false`.

Rollback planning therefore cannot become a production rollback command.

### Rollback evidence

`contracts/everkeep.rollback-evidence.schema.json` records rollback-rehearsal assurance tied to the original execution, plan digest, target environment, expected revision, and observed revision.

Passing evidence requires exact revision equality plus authoritative pass evidence for:

- service health from the target runtime;
- data integrity from Everkeep;
- dependency health from Everkeep;
- Wardveil Security acceptance;
- Privacy Shield acceptance.

Wrong authority, missing evidence, a failed check, unknown evidence, an unready rollback plan, or an exact revision mismatch fails closed.

Passing rollback evidence still permanently records:

- `simulationOnly: true`;
- `externalEffectsObserved: false`;
- `productionMutationAuthorized: false`.

`rollback_evidence_may_authorize_production_mutation()` returns false unconditionally.

## Recovery Center 1.5 compatibility

Phase 3.5 intentionally does not force existing Recovery Center 1.5 summary consumers to migrate.

`contracts/everkeep.recovery-center.failover-operations.schema.json` and `scripts/recovery_center_operations.py` add a separate failover-operations projection covering:

- pending;
- validating;
- authorized-for-drill;
- staging;
- executing;
- verifying;
- completed;
- blocked;
- failed;
- cancelled;
- not applicable;
- rollback pass/fail/unknown/not-applicable coverage;
- active drill identifiers and state.

Evidence-backed Recovery Center actions add:

- `inspect-failover-drill`;
- `inspect-failover-drill-blocker`;
- `review-rollback-assurance`.

Recovery Center still defines no `execute-failover` action. Operational visibility cannot manufacture effecting authority.

## GoreeCloud Monitoring runtime boundary

Phase 3.2 Monitoring artifacts remain immutable projections with `projectionOnly: true`.

`runtime/continuity_signals.py` now provides a runtime-capable adapter that accepts only minimized, approved projection records and invokes an injected GoreeCloud Monitoring client. The outbound payload excludes raw evidence references, recovery payloads, credentials, keys, and secrets.

The result is stored separately as `contracts/everkeep.signal-delivery.schema.json` delivery evidence. Monitoring delivery evidence distinguishes accepted, rejected, failed, and unknown provider results.

GoreeCloud Monitoring remains authoritative for real ingestion, storage, metric processing, dashboards, retention, alert evaluation, and operational availability.

This integration is implemented but not deployed by this repository change. Source validation with an injected fake client does not prove a live Monitoring service accepted any Everkeep metric.

## GoreeCloud Notify runtime boundary

Phase 3.2 Notify intents remain undelivered projection artifacts with `deliveryAttempted: false`.

The Phase 3.5 adapter accepts only an approved intent whose delivery authority is `goreecloud-notify`, sends a minimized intent through an injected GoreeCloud Notify client, and records a distinct delivery-evidence artifact.

GoreeCloud Notify remains authoritative for preferences, destinations, quiet hours, escalation, retries, deduplication policy, provider selection, and proof of actual delivery.

This integration is implemented but not deployed by this repository change. A fake-client CI acceptance proves adapter behavior only and does not prove that a user notification was delivered.

## Read-only authority adapters

`runtime/continuity_authority.py` adds a read-only authority adapter boundary for future live GoreeCloud Identity, Privacy Shield, Wardveil Security, and other continuity-evidence producers.

The adapter calls only an injected provider `read_decision` operation. It does not:

- modify provider state;
- mint or upgrade authority;
- extend `validUntil`;
- issue credentials;
- store reusable credentials;
- convert expired evidence into pass state.

A wrong authority, missing evidence reference, malformed validity deadline, or expired decision normalizes to `unknown`.

This read-only authority integration is implemented but not deployed until a target environment provides independently verified provider connectivity and evidence.

## Persistence

`scripts/drill_operations_service.py` provides append-only SQLite reference persistence for:

- drill dispatches;
- rollback plans;
- rollback evidence;
- Monitoring/Notify signal-delivery evidence.

`db/postgres/008_drill_operations.sql` defines the PostgreSQL-oriented persistence contract and database constraints for the same evidence boundaries.

Storage rejects drill artifacts that permit external effects, source mutation, traffic mutation, or embedded credentials. Rollback evidence cannot authorize production mutation. Signal-delivery evidence cannot embed credentials and must preserve sensitive-payload exclusion.

## Validation

`scripts/validate_phase3_drill_operations.py` covers:

- exact-plan accepted dispatch;
- expired-approval dispatch blocking;
- changed-plan digest blocking;
- multi-step controlled drill completion;
- reverse-order rollback planning;
- exact revision rollback pass;
- revision mismatch failure;
- rollback production-mutation denial;
- Recovery Center operational state counts;
- active, blocked, and rollback-review actions;
- absence of an `execute-failover` action;
- minimized Monitoring delivery through a fake client;
- minimized Notify delivery through a fake client;
- provider-failure evidence;
- current and stale read-only authority evidence;
- append-only persistence and duplicate rejection;
- unsafe rollback-plan persistence rejection;
- machine-readable safety invariants;
- PostgreSQL constraints;
- CI and documentation coverage.

The complete `Validate Everkeep` workflow remains authoritative for source-revision validation before merge.

## Platform boundaries

### GoreeCloud Identity

Identity remains authoritative for authenticated operators and services, recent reauthentication, privileged authorization, quorum, and any future production-effect executor authorization.

### Privacy Shield

Privacy Shield remains authoritative for whether data may be restored, copied, transferred, retained, exposed, or placed into an alternate environment. Rollback rehearsal evidence cannot override a Privacy Shield denial or unknown result.

### Wardveil Security

Wardveil Security remains authoritative for clean-recovery state, isolation, compromise evidence, target promotion safety, and post-recovery security acceptance.

### GoreeCloud Mesh

Mesh may coordinate minimized drill identifiers, state projections, rollback evidence references, and signal-delivery references. It may not turn these records into production execution credentials or extend producer validity.

### Glaze UI

Glaze UI should distinguish a simulation-only drill from production failover, and distinguish executor state, rollback readiness, rollback evidence, Monitoring submission evidence, and Notify submission evidence without relying on color alone.

## Explicit non-claims

Phase 3.5 does not prove or establish:

- production failover;
- production rollback;
- DNS, routing, load-balancer, or traffic switching;
- alternate-environment provisioning;
- production data movement;
- source mutation;
- effecting disaster-recovery workers;
- deployed multi-region or multi-provider resilience;
- live GoreeCloud Identity/Privacy Shield/Wardveil authority adapter connectivity;
- live GoreeCloud Monitoring ingestion;
- live GoreeCloud Notify delivery;
- production recovery acceptance;
- application-specific production continuity acceptance.

Runtime-capable source boundaries introduced here remain implemented but not deployed until authoritative environment evidence proves otherwise.

## Next implementation boundary

Future work may add deployed read-only authority connectivity, authenticated Monitoring/Notify transport configuration, controlled drill scheduling, environment-specific Recovery Center operational APIs, rollback acceptance collection, and a separate production-effect executor architecture.

Any production-effect executor must use a new explicit authority contract and current environment-specific evidence. It must not inherit production authority from Phase 3.4 or Phase 3.5 simulation-only artifacts.
