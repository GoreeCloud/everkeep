# Everkeep Phase 3 — Failover Approval and Acceptance Governance

## Purpose

This Phase 3 increment closes the governance gap between a non-executable failover plan and any future runtime executor.

Everkeep can now represent two distinct evidence boundaries:

1. whether the exact failover plan has current approval evidence from every required authority and may be handed to a separate executor for consideration; and
2. whether a separately completed recovery execution produced authoritative, environment- and revision-bound acceptance evidence.

Neither boundary executes failover, switches traffic, provisions infrastructure, copies production data, or grants source-mutation authority.

## Exact-plan binding

`scripts/failover_governance.py` computes a canonical SHA-256 digest across the full failover-plan artifact. Approval and acceptance records both carry this `planDigest`.

A later plan edit therefore produces a different digest and requires new governance evidence. Approval of one plan revision cannot silently authorize a modified sequence, target, dependency graph, or promotion request.

## Failover approval decision

`contracts/everkeep.failover-approval.schema.json` records the current decision for a specific plan digest and target.

The required approval gates correspond to the non-executable failover plan:

- operator approval;
- GoreeCloud Identity authorization;
- Privacy Shield authorization;
- Wardveil Security clearance;
- current Everkeep continuity evidence;
- alternate-target readiness;
- dependency readiness;
- key-material readiness.

Each gate carries its own authority, evidence reference, observation time, and validity deadline. The approval expires when the earliest required gate evidence expires.

Approval states are:

- `approved` — every required gate is an authoritative current pass and the plan remains ready for approval;
- `denied` — the plan is blocked or at least one authority explicitly denies the request;
- `expired` — all required gates otherwise pass but at least one required approval-evidence validity window has ended;
- `unknown` — required plan structure, authority, evidence, or timing cannot be established.

An approved record may set `handoffEligible: true`. This means only that a separate executor may consider the request. It does not mean the executor must run it.

Every approval record permanently carries:

- `executionAuthorized: false`
- `executionCredential: false`
- `sourceMutationAllowed: false`

`approval_may_execute()` returns false unconditionally.

## Separate recovery executor boundary

Everkeep already defines the generic `contracts/everkeep.recovery-execution.schema.json` boundary. Phase 3.3 does not replace or weaken it.

A future failover executor must independently validate its execution record, current platform authorities, environment, recovery points, dependencies, key material, runtime preconditions, and any additional high-impact controls. The approval artifact is evidence for governance history, not a bearer credential or command token.

## Revision- and environment-bound acceptance

`contracts/everkeep.failover-acceptance.schema.json` records acceptance evidence after a separate execution record reports completion.

A passing acceptance requires:

- the execution to reference the same plan;
- the execution to report `state: completed` and `authorized: true` under its own contract;
- the execution environment to match the failover plan target environment;
- `sourceMutationAllowed: false` to remain intact;
- the expected deployed revision to exactly equal the observed revision, binding acceptance to the exact deployed revision rather than a branch, tag, release family, or intended version;
- authoritative pass evidence for service health;
- authoritative pass evidence for data integrity;
- authoritative pass evidence for dependency health;
- Wardveil Security clearance;
- Privacy Shield acceptance;
- rollback readiness evidence.

The resulting record is bound to the plan digest, execution ID, target, environment, expected revision, observed revision, and evidence references.

A revision mismatch, environment mismatch, incomplete execution, failed check, missing evidence, or wrong authority fails closed.

Every acceptance record permanently carries `productionMutationAuthorized: false`. Acceptance records describe verified state; they do not authorize new mutations.

## Persistence

`scripts/failover_governance_service.py` adds append-only reference persistence for:

- failover approval decisions;
- approval history by plan;
- failover acceptance evidence;
- acceptance history by plan.

The store rejects approval artifacts that claim execution authority, credential status, or source mutation, and rejects acceptance artifacts that claim production-mutation authority.

`db/postgres/006_failover_governance.sql` defines the PostgreSQL-oriented persistence boundary and enforces the same restrictions with database constraints.

## Recovery Center 1.5

Recovery Center schema 1.5 adds `failoverGovernance` coverage with separate approval and acceptance counts.

Approval coverage distinguishes:

- approved;
- denied;
- expired;
- unknown;
- not applicable.

Acceptance coverage distinguishes:

- pass;
- fail;
- unknown;
- not applicable.

Legacy resources with no failover plan or completed failover execution are `not-applicable`, not failed.

Evidence-backed actions include:

- `review-failover-approval` when a ready-for-approval plan lacks current approval evidence or that evidence has expired;
- `inspect-failover-denial` when an explicit current denial exists;
- `evaluate-failover-acceptance` when a completed execution lacks passing acceptance evidence.

Recovery Center intentionally adds no `execute-failover` action.

## Platform authority boundaries

### GoreeCloud Identity

Identity remains authoritative for authenticated operator identity, service identity, recent reauthentication, privileged authorization, quorum, and future high-impact approval requirements.

### Privacy Shield

Privacy Shield remains authoritative for whether data may be restored, copied, transferred, exposed, retained, or placed into an alternate environment. Everkeep cannot convert a privacy denial into approval or acceptance.

### Wardveil Security

Wardveil remains authoritative for clean-recovery security evidence, compromise/isolation state, promotion safety, and post-recovery security acceptance. Everkeep cannot convert failed or unknown Wardveil evidence into pass state.

### GoreeCloud Mesh

Mesh may coordinate plan digests, approval IDs, bounded decisions, execution references, and acceptance evidence. Mesh may not extend validity windows, change authority results, or turn approval evidence into an execution credential.

### Glaze UI

Glaze UI should present `ready-for-approval`, `approved`, `executor handoff eligible`, `executing`, `completed`, and `accepted` as distinct states. An approved plan must never be rendered as running, and a completed execution must never be rendered as accepted until exact environment/revision evidence passes.

## Explicit non-claims

This increment does not:

- execute failover;
- invoke a runtime executor;
- switch DNS, routing, or user traffic;
- provision alternate infrastructure;
- create replicas or backups;
- copy production data;
- authorize source mutation;
- grant a bearer credential for failover;
- prove that any production failover has occurred;
- prove that any target environment is currently accepted;
- establish multi-region or multi-provider resilience.

## Next implementation boundary

Future increments may add a separate controlled executor state machine, explicit executor-request contracts, live authority adapters, bounded disaster-recovery drill automation, actual Monitoring/Notify runtime integration, rollback execution evidence, and production environment acceptance collection.

Those capabilities must remain unclaimed until runtime evidence proves them.
