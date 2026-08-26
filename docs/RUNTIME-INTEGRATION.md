# Everkeep Phase 1 Runtime Integration

This phase connects the validated Everkeep service boundary to runtime-facing platform dependencies while preserving evidence-backed claims.

## Runtime boundaries

- GoreeCloud Identity resolves authenticated principals and recent-reauth state.
- Privacy Shield authorizes data-lifecycle actions and may deny backup, retention, export, restore, succession, or deletion operations.
- Wardveil Security authorizes security-sensitive recovery and protection operations and may block unsafe or suspicious actions.
- GoreeCloud Mesh receives normalized Everkeep outbox events.
- First-party adapter executors collect authoritative application resource state without fabricating backup or recovery evidence.

## Fail-closed behavior

Runtime platform decisions are explicit. A Privacy Shield or Wardveil response other than `allow` blocks the operation. Missing authentication is rejected. Sensitive policy and destructive recovery-point transitions require recent reauthentication through the Identity provider boundary.

## Mesh delivery

Everkeep uses the transactional outbox boundary established by the service layer. Runtime publication reads unpublished events, sends them through a Mesh publisher, marks successful events published, and increments failed-attempt counters without falsely acknowledging delivery.

## PostgreSQL

`scripts/postgres_repository.py` defines the production-oriented DB-API repository boundary. It uses row locking for policy version changes and `FOR UPDATE SKIP LOCKED` for concurrent outbox workers. Production credentials and driver selection remain external runtime configuration.

## Runtime configuration

`contracts/everkeep.runtime-config.schema.json` defines environment, database secret references, platform endpoint references, outbox limits, and enabled adapters. Secret values are referenced rather than committed to the repository.

## Deployment boundary

This phase does not claim that GoreeCloud Identity, Privacy Shield, Wardveil, Mesh, PostgreSQL, immutable storage, or application adapters are deployed in production. It establishes validated integration boundaries that a deployable service can wire to real platform endpoints and credentials.
