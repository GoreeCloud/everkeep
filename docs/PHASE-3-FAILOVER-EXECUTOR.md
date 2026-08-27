# Everkeep Phase 3.4 — Controlled Failover Executor

## Purpose

This Phase 3.4 increment closes the architectural gap between Phase 3.3 executor-handoff eligibility and a controlled execution lifecycle without claiming or enabling live production failover.

Everkeep now has a separate reference executor state machine that can accept an exact-plan, currently approved handoff for a bounded disaster-recovery drill, revalidate fresh executor-time authority evidence, record deterministic execution-state transitions, and preserve evidence history.

The Phase 3.4 reference executor is simulation-only and has no external effects. It cannot provision infrastructure, move production data, mutate a surviving source, change DNS or routing, perform traffic switching, embed reusable credentials, or turn a governance artifact into a bearer execution credential.

## Exact plan and approval binding

`contracts/everkeep.failover-executor-request.schema.json` binds a request to:

- `approvalId`;
- `planId`;
- the exact plan digest produced by the canonical SHA-256 plan serializer;
- `objectiveId`;
- exact target identity, environment, and failure domain;
- the expected target revision;
- request time and approval expiry;
- fresh executor-time authority evidence.

A changed plan produces a different digest and is rejected even when the plan identifier is unchanged. A stale, denied, unknown, mismatched, or non-handoff-eligible approval cannot produce an accepted executor request.

The Phase 3.3 approval remains governance evidence only. The executor independently checks that `executionAuthorized`, `executionCredential`, and `sourceMutationAllowed` remain false on the approval artifact.

## Fresh authority revalidation

Approval-time evidence is not sufficient by itself. Immediately before accepting a drill handoff, `scripts/failover_executor.py` requires fresh executor-time authority evidence for:

- GoreeCloud Identity authorization;
- Privacy Shield authorization;
- Wardveil Security clearance;
- current Everkeep continuity evidence;
- alternate-target readiness;
- dependency readiness;
- key-material readiness.

Each gate must carry the expected authority, a non-empty evidence reference, observation time, and a future validity deadline. Expired, malformed, missing, failed, or incorrectly attributed evidence fails closed.

This prevents a previously approved plan from being treated as executable after a material authority or readiness condition changes.

## Executor request contract

`contracts/everkeep.failover-executor-request.schema.json` defines the handoff boundary.

Phase 3.4 intentionally fixes `mode` to `drill` and permanently requires:

- `simulationOnly: true`;
- `externalEffectsAuthorized: false`;
- `sourceMutationAllowed: false`;
- `trafficMutationAllowed: false`;
- `credentialsEmbedded: false`.

`handoffAccepted: true` means only that the request passed the Phase 3.4 reference-executor checks and may enter the drill state machine. It does not mean production effects are authorized.

## Controlled state machine

`contracts/everkeep.failover-executor-state.schema.json` and `scripts/failover_executor.py` define these states:

1. `pending`
2. `validating`
3. `authorized`
4. `staging`
5. `executing`
6. `verifying`
7. `completed`

Terminal non-success states are:

- `blocked`;
- `failed`;
- `cancelled`.

Transitions are explicit and fail closed. Terminal states cannot transition again. State records may collect completed drill-step identifiers, evidence references, blocker codes, and timestamps.

The `authorized` state means authorized to continue the bounded simulation-only drill workflow. It does not grant external-effect authority.

`executor_may_produce_external_effects()` returns false unconditionally.

## Persistence

`scripts/failover_executor_service.py` adds append-only SQLite reference persistence for:

- executor requests;
- executor state history.

The store rejects artifacts that weaken any Phase 3.4 safety invariant.

`db/postgres/007_failover_executor.sql` defines the PostgreSQL-oriented persistence boundary. Database constraints require drill mode, simulation-only execution, and false values for external effects, source mutation, traffic mutation, and embedded credentials.

The persistence model records the control-plane history; it does not contain recovery payloads or execution credentials.

## Relationship to the existing recovery-execution contract

`contracts/everkeep.recovery-execution.schema.json` remains the generic recovery execution evidence contract used by existing acceptance boundaries. Phase 3.4 does not silently redefine its semantics or manufacture a completed recovery record.

The new executor-request and executor-state contracts define a stricter controlled drill orchestration boundary. A future production-effect executor would require a separate explicit contract and runtime acceptance evidence rather than changing the meaning of the Phase 3.4 drill artifacts.

## Platform authority boundaries

### GoreeCloud Identity

GoreeCloud Identity remains authoritative for authenticated operator/service identity, recent reauthentication, privileged authorization, quorum, and any future high-impact production-effect authorization. Everkeep does not mint Identity authority.

### Privacy Shield

Privacy Shield remains authoritative for whether data may be restored, copied, transferred, retained, exposed, or placed in an alternate environment. A Privacy Shield denial or unknown result blocks executor handoff.

### Wardveil Security

Wardveil Security remains authoritative for clean-recovery security state, isolation, compromise status, promotion safety, and post-recovery security acceptance. A failed, stale, missing, or unknown Wardveil result blocks executor handoff.

### GoreeCloud Mesh

GoreeCloud Mesh may coordinate bounded request identifiers, state transitions, and minimized evidence references. Mesh cannot extend authority validity, change a decision, inject an execution credential, or convert a drill artifact into production authority.

### Glaze UI

Glaze UI should distinguish approval, handoff accepted, drill pending, validating, authorized-for-drill, staging, executing, verifying, completed, blocked, failed, cancelled, and post-execution acceptance. `authorized` must never be rendered as production failover authorization.

## Recovery Center

Recovery Center remains the evidence and operator-awareness surface. This increment deliberately does not add an `execute-failover` action or imply that Recovery Center can cause runtime effects.

Future Recovery Center work may project current executor-request and executor-state evidence, but any production-affecting action requires a separately evidenced execution boundary and must not reuse Phase 3.4 drill authorization.

## Explicit non-claims

This increment does not establish:

- production failover;
- live failover execution adapters;
- DNS, route, load-balancer, or traffic switching;
- alternate-environment provisioning;
- production data movement or restoration;
- source mutation;
- replica or backup creation;
- embedded or bearer execution credentials;
- automated rollback execution;
- deployed multi-region or multi-provider resilience;
- actual GoreeCloud Monitoring ingestion;
- actual GoreeCloud Notify delivery;
- production-environment failover acceptance.

No external effects are performed by the Phase 3.4 reference executor.

## Validation

`scripts/validate_phase3_failover_executor.py` covers:

- valid exact-plan drill handoff;
- fresh executor-time authority evidence;
- deterministic state progression;
- terminal-state enforcement;
- changed-plan digest rejection;
- expired approval rejection;
- wrong-authority rejection;
- unsafe traffic-mutation request blocking;
- persistence rejection of unsafe artifacts;
- append-only state history;
- contract safety invariants;
- PostgreSQL safety constraints;
- documentation boundaries.

## Next implementation boundary

A future phase may add evidence-only Recovery Center executor projections, controlled disaster-recovery drill workers, live but read-only authority adapters, rollback-plan and rollback-evidence contracts, actual GoreeCloud Monitoring/Notify delivery integration, and production-environment acceptance collection.

Any executor capable of external effects must be introduced as a separate, explicitly production-effect-aware contract with current GoreeCloud Identity, Privacy Shield, Wardveil Security, Everkeep, and environment-specific authorization evidence. It must not inherit production authority from a Phase 3.4 drill request.
