# Everkeep Persistent Service Layer

This layer makes the Phase 1 execution model durable without claiming that production backup storage, isolated recovery infrastructure, or disaster-recovery environments are deployed.

## Persistence responsibilities

Everkeep persists normalized platform state for:

- protected-resource registration,
- active and historical protection-policy versions,
- recovery-point lifecycle state,
- retention decisions,
- append-only audit events,
- first-party application adapter cursors and synchronization state.

The reference implementation uses SQLite for deterministic local validation and small deployments. PostgreSQL is the intended compatible production-class relational target when multi-process or higher-scale deployment requires it.

## Transaction and integrity requirements

Persistent writes must be transactional. Resource identifiers, recovery-point identifiers, policy version numbers, and event sequence numbers must not be silently reused. Foreign-key constraints remain enabled. Recovery-point ingestion is idempotence-protected. Audit events are append-only from the Everkeep service boundary.

## Policy versioning

Updating a policy creates a new immutable policy version and advances the active version pointer. Historical versions remain addressable so Everkeep can explain which policy governed a prior recovery point, retention decision, or readiness calculation.

Policy migration must be explicit. A future schema migration service may transform policy payloads between supported schema generations, but migration must preserve source version, target version, migration timestamp, and migration evidence.

## Recovery-point lifecycle

Phase 1 persistent lifecycle states are:

- `available`
- `verifying`
- `blocked`
- `expired`

`expired` is terminal. Invalid transitions fail closed. Lifecycle changes emit audit evidence.

## Audit/event persistence

Each durable Everkeep mutation emits a monotonically ordered audit event. Consumers may resume after a known event sequence. Audit persistence is separate from user-facing notifications; GoreeCloud Mesh, GoreeCloud Monitoring, and GoreeCloud Notify may consume these events through dedicated adapters.

## Recovery Center query execution

Recovery Center reads normalized durable state rather than reconstructing truth from UI state. Resource listing supports deterministic ordering, bounded page size, cursor pagination, and first-stage filters such as source application and preservation tier.

A per-resource projection contains the protected resource, recovery points, latest retention decision, and latest related audit sequence. Readiness and evidence projections can be joined from the existing Phase 1 evaluation layer.

## First-party application adapters

Adapters connect authoritative application state to Everkeep. Every adapter declares:

- adapter identifier,
- source application,
- supported resource classes,
- supported capabilities,
- durable event cursor,
- authoritative fields or domains,
- read-only behavior when applicable.

Initial adapter targets should include GoreeCloud Drive, Documents, Photos, Vault, Mail, Messenger, Notes, Calendar, Contacts, Browser/Bookmarks, AI, Backup, and infrastructure services.

Adapters must not invent recovery evidence. A source application may register or describe a resource, while the system that actually performs a snapshot, backup, verification, restore test, or recovery operation remains authoritative for that evidence.

## Deployment boundary

The SQLite implementation is a reference persistent service and validation target. It establishes durable semantics and executable behavior. It does not by itself provide replicated databases, HA failover, immutable backup media, external object storage, cross-region durability, or production disaster recovery.
