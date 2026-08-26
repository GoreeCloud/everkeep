# Everkeep Service/API Layer

This boundary turns the Phase 1 persistent reference implementation into a transport-ready service contract without claiming production deployment.

## Service Responsibilities

The service facade provides authentication and permission gates, recent-reauthentication requirements for high-impact mutations, idempotency keys for create operations, ETag-based optimistic concurrency for policy updates, health/readiness checks, audit access, Recovery Center queries, and transactional-outbox semantics.

## Transport Model

The service is transport-neutral. `scripts/service_api.py` can sit behind GoreeCloud Mesh, HTTP, an internal RPC boundary, or a future GoreeCloud-native service transport. `api/openapi.yaml` defines the first HTTP contract. Mesh operations continue to use the canonical Everkeep Mesh schemas.

## Authorization

Every protected operation requires a GoreeCloud Identity principal and explicit Everkeep permission. Policy writes and destructive/high-impact recovery-point or retention state changes require recent reauthentication in the reference layer. Production integrations must also apply Privacy Shield policy decisions and Wardveil Security trust/risk gates before carrying out sensitive operations.

## Concurrency and Idempotency

Create-style operations support idempotency keys. Reuse of an idempotency key with a different request fails closed. Policy updates support ETags and `If-Match`; a stale ETag is rejected instead of overwriting a newer policy version.

## Event Delivery

Domain changes are written to an outbox after the underlying state mutation. The PostgreSQL model includes a durable `everkeep_outbox` table for at-least-once publication to GoreeCloud Mesh. Consumers must deduplicate by event ID. Publishing infrastructure is not claimed as deployed by this phase.

## PostgreSQL Production Model

`db/postgres/001_everkeep_core.sql` defines the initial production-oriented relational model for resources, immutable policy versions, recovery points, retention decisions, audit events, adapter state, idempotency records, schema migrations, and transactional outbox entries.

The migration is a schema contract, not evidence that a production PostgreSQL cluster exists. Deployment must add connection pooling, encrypted connections, credentials/secrets management, backup/restore of the database itself, replication as required, migration orchestration, observability, capacity controls, and disaster-recovery procedures.

## First-Party Adapters

The first adapter contract covers GoreeCloud Drive, GoreeCloud Documents, GoreeCloud Photos, GoreeCloud Vault, and GoreeCloud Backup. Each adapter declares discover/snapshot/restore/verify/export capabilities, cursor semantics, required permissions, privacy purposes, and supported resource classes.

GoreeCloud Vault is intentionally stricter: Everkeep must preserve the encryption boundary and should not require plaintext secret material merely to provide resilience.

## Health and Readiness

`/health` reports whether the service process can reach its persistence layer. `/ready` reports whether the service has the schema prerequisites required to accept traffic. These signals are operational probes only and must not be interpreted as evidence that protected resources are Recovery Ready.

## Production Boundary Still Outstanding

This phase does not claim deployed PostgreSQL, production HTTP ingress, GoreeCloud Identity token verification, Privacy Shield/Wardveil runtime calls, a running Mesh event publisher, high availability, backup repositories, immutable storage, or real restoration infrastructure. Those require separate runtime evidence and deployment work.
