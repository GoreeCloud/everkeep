# Everkeep Phase 3 — Continuous Continuity Control Plane

## Purpose

Phase 3 expands Everkeep from recovery-point and recovery-plan semantics into continuous, evidence-backed service continuity posture.

The central question is no longer only whether a protected resource can be restored. Everkeep must also be able to determine whether the protected scope is meeting its RPO and RTO objectives, whether recent recovery exercises prove those objectives, whether required failure-domain diversity still exists, whether dependencies and key material remain recoverable, and whether an alternate recovery target is actually ready when policy requires one.

This layer remains fail closed. Missing, stale, malformed, conflicting, or unverified required evidence cannot produce a ready continuity posture or authorize failover.

## New machine-readable contracts

Phase 3 adds:

- `contracts/everkeep.continuity-objective.schema.json`
- `contracts/everkeep.continuity-posture.schema.json`
- `contracts/everkeep.recovery-exercise.schema.json`

A continuity objective defines policy targets. A continuity posture is a deterministic evaluation of those targets against authoritative evidence. A recovery exercise records bounded proof produced by a tabletop exercise, dry run, Recovery Sandbox rehearsal, failover drill, or restore test.

## Continuity objective dimensions

A continuity objective can define:

- RPO target in seconds.
- RTO target in seconds.
- Maximum age of acceptable recovery exercise evidence.
- Minimum independent failure-domain count.
- Requirement for an alternate recovery target.
- Requirement for dependency readiness.
- Requirement for key-material readiness.

Targets are explicit policy inputs. Everkeep does not invent an RPO, RTO, redundancy requirement, exercise cadence, or alternate-target requirement when policy does not provide one.

## Deterministic continuity posture

`scripts/continuity.py` evaluates the following dimensions:

1. **RPO** — age of the latest evidenced protection point against the configured RPO.
2. **RTO** — measured recovery duration from authoritative exercise evidence against the configured RTO.
3. **Recovery exercise freshness** — age of the latest recovery exercise against its policy cadence.
4. **Failure-domain diversity** — distinct evidenced recovery failure domains against the configured minimum.
5. **Alternate recovery target** — explicit readiness evidence when policy requires an alternate target.
6. **Dependencies** — recovery dependency readiness when required.
7. **Key material** — availability of required recovery key material when required.

Each dimension resolves to `ready`, `attention`, `degraded`, or `unknown`.

The aggregate state is conservative:

- any `degraded` required dimension produces `degraded`;
- otherwise any `unknown` required dimension produces `unknown`;
- otherwise any `attention` dimension produces `attention`;
- only all-ready dimensions produce `ready`.

An `attention` result is used for near-threshold evidence. It is not equivalent to ready.

## RPO and RTO semantics

RPO measurement uses the age of the latest authoritative protection evidence. A stale protection timestamp is an RPO miss; a missing or invalid timestamp is unknown.

RTO measurement uses recovery duration measured by an authoritative recovery exercise. A configured RTO cannot be considered satisfied solely from architecture documentation, a theoretical estimate, or the existence of a backup.

Near-threshold RPO and RTO measurements are surfaced as attention so operators can act before the objective is missed.

## Recovery exercise evidence

`build_exercise_record` normalizes exercise evidence across:

- tabletop exercises;
- dry runs;
- Recovery Sandbox rehearsals;
- failover drills;
- restore tests.

A passing recovery exercise requires passing evidence for integrity, service health, dependencies, Wardveil-relevant security checks, and Privacy Shield-relevant privacy checks.

Missing checks result in unknown. Any failed check results in fail.

Recovery exercise records set `productionMutationAllowed: false`. The record describes evidence from the exercise; it does not authorize production mutation.

## Durable continuity extension

`scripts/continuity_service.py` adds reference persistence for continuity objectives and recovery exercises on top of the existing Everkeep store.

It provides:

- objective create/update and retrieval;
- recovery-exercise recording with duplicate protection;
- per-objective exercise history;
- continuity posture evaluation from persisted objective plus supplied evidence;
- reuse of the existing Everkeep append-oriented audit boundary when available.

This is reference persistence. It does not prove that production PostgreSQL, recovery workers, alternate environments, or failover infrastructure are deployed.

## Recovery Center expansion

Recovery Center schema version 1.3 provides:

- ready / attention / degraded / unknown continuity posture counts;
- RPO compliance coverage;
- RTO compliance coverage;
- recovery-exercise freshness coverage;
- failure-domain diversity coverage;
- recovery-topology freshness coverage.

Evidence-authorized recommendations include:

- inspect continuity objective;
- run disaster-recovery drill;
- inspect failure domains;
- inspect alternate recovery target;
- inspect recovery topology;
- create a non-executable failover plan when continuity and topology evidence are both ready.

These recommendations do not execute a failover. Restore exposure remains gated by the existing Recovery Ready and `recoveryEligible: true` requirements.

## GoreeCloud platform integration

### GoreeCloud Mesh

GoreeCloud Mesh may coordinate bounded continuity-objective, posture, recovery-exercise, topology, scenario, and plan events. Mesh does not become the authority that decides whether an RPO, RTO, recovery drill, failure domain, alternate target, topology observation, or failover plan is valid. The authoritative producer and applicable Everkeep policy remain responsible for the evidence.

### Privacy Shield

Privacy Shield remains authoritative for whether protected information may be copied, retained, restored, migrated, or placed into an alternate environment. A continuity objective or failover plan cannot override a Privacy Shield denial.

### Wardveil Security

Wardveil Security supplies security evidence relevant to recovery exercises, clean recovery, repository protection, suspicious recovery activity, isolation, and promotion of recovered state. A continuity posture or plan cannot convert unknown or failed Wardveil evidence into readiness.

### GoreeCloud Identity

GoreeCloud Identity remains responsible for authenticated principals, reauthentication, administrative authorization, quorum, and other identity-backed recovery controls.

### Glaze UI

Glaze UI should present continuity state as evidence-backed status, never as decorative uptime or resilience branding. RPO/RTO measurements, drill freshness, failure-domain limitations, topology freshness, simulated impact, and plan approval state must remain inspectable without relying on color alone.

## Recovery topology and failover planning follow-on

Phase 3 now also implements the next planning boundary through `docs/PHASE-3-FAILOVER-PLANNING.md`:

- authoritative recovery-topology evidence;
- simulated node and failure-domain scenarios;
- dependency-aware direct and transitive impact analysis;
- alternate recovery-target selection with explicit coverage checks;
- dependency-aware recovery ordering and cycle blocking;
- durable topology, scenario, and plan persistence;
- PostgreSQL continuity-planning tables;
- approval-only failover-plan generation;
- Recovery Center topology coverage and plan-creation exposure.

A generated failover plan always has `requiresApproval: true`, `executionAuthorized: false`, and `sourceMutationAllowed: false`.

## Explicit boundary

Phase 3 code evaluates and stores continuity evidence and can prepare approval-only recovery plans. It does not perform failover, switch traffic, provision disaster-recovery infrastructure, copy production data, mutate production state, create immutable storage, or claim multi-provider resilience.

A ready continuity posture means that supplied authoritative evidence satisfies the declared objective at the evaluation time. A ready-for-approval plan means only that the planning prerequisites are currently satisfied. Neither state substitutes for live-environment acceptance or runtime authorization, and both expire when underlying evidence becomes stale.

## Next implementation boundary

The next continuity increment should connect these contracts to current runtime evidence and operational workflows while preserving the same evidence rules:

- scheduled continuity-objective evaluation;
- topology freshness and expiry policy;
- live RPO/RTO measurements from authoritative producers;
- live failure-domain, alternate-target, and dependency inventory adapters;
- bounded recovery-exercise automation;
- GoreeCloud Monitoring continuity metrics;
- GoreeCloud Notify continuity alerts;
- a separate approval and execution contract for controlled failover;
- environment- and revision-bound failover acceptance evidence.

None of those capabilities should be represented as deployed until runtime evidence proves them.
