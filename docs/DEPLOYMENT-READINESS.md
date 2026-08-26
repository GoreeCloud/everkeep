# Everkeep Phase 1 — Deployment Readiness

This boundary makes Everkeep deployable to a controlled staging environment without claiming production deployment.

## Runtime

- `runtime/everkeep_host.py` provides the initial HTTP process boundary and health/readiness probes.
- `runtime/deployment_runtime.py` loads fail-closed runtime configuration, reads service credentials from files rather than embedding secrets, provides HTTP client boundaries for GoreeCloud Identity, Privacy Shield, Wardveil Security, and GoreeCloud Mesh, and defines an outbox worker plus basic runtime metrics.
- `Dockerfile` runs Everkeep as a non-root user with a container health check.
- `deploy/staging.compose.yaml` provides a hardened staging composition with read-only filesystem, tmpfs, no-new-privileges, explicit required platform endpoints, and a file-mounted service secret.

## Readiness Contract

The service must report `not_ready` when any required platform endpoint or database configuration is absent. Configuration presence alone is not evidence that a provider is healthy. Sensitive Everkeep operations remain fail-closed unless authoritative Identity, Privacy Shield, and Wardveil decisions succeed.

## Mesh Delivery

Mesh publication uses the durable outbox boundary. A worker claims durable events, publishes them to GoreeCloud Mesh, and acknowledges only successful publication. Failed delivery leaves the event eligible for retry. Production deployments should add bounded exponential backoff, dead-letter handling, delivery metrics, and alerting.

## PostgreSQL

The existing PostgreSQL repository and schema contracts remain the production persistence direction. Staging deployment must apply migrations before readiness is granted and must verify row-locking and `SKIP LOCKED` behavior under concurrent outbox workers.

## Secrets

No service token, database password, or provider credential belongs in repository configuration. Runtime configuration stores endpoints and references secret files or an external secret manager. Secret rotation must not require rebuilding the application image.

## Staging Verification Gate

A staging environment is only considered verified after evidence demonstrates: container startup; database migration success; database connectivity; Identity authentication/authorization response; Privacy Shield decision response; Wardveil decision response; Mesh event publication and acknowledgement; adapter discovery against at least one first-party application; health/readiness behavior; restart recovery; and retained audit/outbox evidence.

## Evidence Boundary

This repository now contains deployment-ready reference artifacts. It does **not** establish that GoreeCloud Identity, Privacy Shield, Wardveil Security, GoreeCloud Mesh, PostgreSQL, Cloudflare, application adapters, immutable backup media, or recovery infrastructure are currently deployed or reachable. Those claims require runtime evidence from the target environment.
