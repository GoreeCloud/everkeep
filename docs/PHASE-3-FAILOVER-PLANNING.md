# Everkeep Phase 3 — Recovery Topology and Failover Planning

## Purpose

This Phase 3 increment gives Everkeep a deterministic answer to a continuity question that recovery-point evidence alone cannot answer:

**If a node, dependency, failure domain, region, provider, or supporting platform component becomes unavailable, what is affected and what recovery path can be prepared safely?**

The implementation adds recovery-topology evidence, simulated failure scenarios, impact propagation, alternate-target selection, dependency-aware recovery ordering, and non-executable failover-plan generation.

It remains evidence bounded and fail closed. The presence of a plan never means failover is authorized, deployed, or safe to execute.

## Machine-readable contracts

This increment adds:

- `contracts/everkeep.recovery-topology.schema.json`
- `contracts/everkeep.failure-scenario.schema.json`
- `contracts/everkeep.failover-plan.schema.json`

### Recovery topology

A recovery topology records bounded evidence about:

- services;
- data stores;
- storage and compute;
- networking and DNS;
- identity dependencies;
- key-material dependencies;
- provider and region failure domains;
- dependency, hosting, usage, replication, recovery, and routing relationships;
- alternate recovery targets and the nodes each target can support.

Topology evidence is explicitly marked authoritative or non-authoritative. A non-authoritative topology cannot support a ready failover plan.

Raw backup contents, credentials, keys, private data, and other sensitive recovery payloads are outside the topology contract. `sensitivePayloadsExcluded: true` is mandatory.

## Failure scenarios

Failure scenarios are simulated planning inputs. Supported scenario classes include node loss, failure-domain loss, provider loss, region loss, network partition, DNS loss, identity loss, key-material loss, security-driven isolation, and custom scenarios.

Every scenario is explicitly marked:

- `simulated: true`
- `productionMutationAllowed: false`

A scenario may identify affected nodes, affected failure domains, or both. It does not claim that the represented failure is actually occurring.

## Deterministic impact analysis

`scripts/continuity_planner.py` builds an impact projection from topology evidence and a simulated scenario.

Direct impact includes explicitly affected nodes and nodes located inside an affected failure domain.

Transitive impact propagates through dependency-bearing relationships. When a service depends on an affected data store, identity service, network path, or other prerequisite, the dependent service becomes impacted as well.

Unknown topology nodes, unknown edge endpoints, non-authoritative topology evidence, or a scenario with no evidenced impact fail closed.

## Alternate recovery-target selection

A recovery target is eligible only when:

- its current state is `ready`;
- it has an evidence reference;
- its failure domain is not itself part of the simulated failure;
- it explicitly supports every recovery node required by the impact projection.

Everkeep does not infer that an arbitrary region, server, provider, or environment can host a recovery workload.

## Dependency-aware recovery order

Recovery nodes are ordered so evidenced dependencies are recovered and verified before their dependents.

Dependency cycles block plan generation rather than allowing an ambiguous restoration sequence.

## Failover plan semantics

A ready plan contains planning steps for:

1. isolating the failed scope;
2. validating the alternate recovery target;
3. recovering impacted nodes in dependency order;
4. verifying each recovered node;
5. verifying the overall service scope;
6. preparing rollback;
7. requesting promotion.

The plan intentionally stops at **request promotion**. It does not switch traffic or mutate production.

Every failover plan requires all of the following approval gates before a separate execution system could even consider runtime action:

- operator approval;
- GoreeCloud Identity authorization;
- Privacy Shield authorization;
- Wardveil Security clearance;
- current continuity evidence;
- target readiness;
- dependency readiness;
- key-material readiness.

The plan contract permanently sets:

- `requiresApproval: true`
- `executionAuthorized: false`
- `sourceMutationAllowed: false`

`plan_may_execute()` also returns false unconditionally. This artifact is a planning boundary, not an execution credential.

## Persistence

`scripts/continuity_planning_service.py` provides reference persistence for:

- recovery topology evidence;
- immutable simulated failure scenarios;
- failover-plan artifacts;
- per-objective plan history.

`db/postgres/004_continuity_planning.sql` defines the production-oriented PostgreSQL storage boundary and database constraints that prevent a stored planning artifact from representing execution authorization or source mutation permission.

## Recovery Center 1.3

Recovery Center schema 1.3 adds `topologyCurrent` to continuity coverage.

Evidence-backed actions now include:

- `inspect-recovery-topology` when topology evidence is stale, incomplete, or unavailable;
- `create-failover-plan` only when continuity state is ready, failover eligibility is true, and topology evidence is current.

Creating a plan is not failover execution.

## Platform integration boundaries

### GoreeCloud Mesh

Mesh may coordinate topology references, scenario identifiers, plan state, approval requests, and bounded evidence. Mesh does not become the authority that declares topology correctness or grants failover execution authority.

### Privacy Shield

Privacy Shield remains authoritative for whether data may be copied, restored, transferred, or placed into an alternate environment. A ready plan cannot override a privacy denial.

### Wardveil Security

Wardveil remains authoritative for security clearance, clean-recovery evidence, suspicious recovery activity, isolation requirements, and promotion safety. A plan cannot convert unknown or failed Wardveil evidence into authorization.

### GoreeCloud Identity

Identity remains authoritative for operator identity, administrative authorization, reauthentication, quorum, and high-impact approval requirements.

### Glaze UI

Glaze UI should distinguish topology evidence, simulated impact, planning readiness, approval state, and actual execution state. A `ready-for-approval` plan must never be presented as a completed or active failover.

## Explicit non-claims

This increment does not:

- perform failover;
- switch user or service traffic;
- provision alternate infrastructure;
- create replicas or backups;
- copy production data;
- mutate surviving source data;
- authorize promotion;
- prove that an alternate environment is deployed;
- prove multi-provider or cross-region resilience;
- establish live production continuity acceptance.

## Next implementation boundary

The next increment should connect the now-defined planning model to scheduled and live evidence producers while preserving the same authority boundaries:

- scheduled continuity-objective evaluation;
- topology freshness policy and expiry;
- live failure-domain and dependency inventory adapters;
- bounded disaster-recovery drill automation;
- GoreeCloud Monitoring continuity metrics;
- GoreeCloud Notify continuity alerts;
- separate approval and execution contracts for controlled failover;
- revision- and environment-bound failover acceptance evidence.
