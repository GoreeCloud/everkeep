# Everkeep Phase 1 — Execution Layer

This boundary turns Phase 1 contracts into deterministic platform behavior without claiming deployment of storage or recovery infrastructure that is not evidenced.

## Resource Registry

The Resource Registry accepts explicit registrations, rejects duplicate resource identifiers, records application, class, owner, preservation tier, parent relationship, and optional explicit protection policy.

## Policy Resolution

Policy resolution is deterministic. Precedence is:

1. Explicit resource policy.
2. Inherited parent effective policy when available and enabled.
3. Matching resource-ID scope.
4. Matching resource-class scope.
5. Matching application scope.
6. Matching preservation-tier scope.
7. Enabled default policy.

Ties are resolved by stable policy identifier ordering. Missing applicable policy fails closed instead of silently treating the resource as protected.

## Retention Decisions

Retention evaluation produces an explicit decision and authority. Privacy Shield deletion requirements can override ordinary Everkeep retention when the policy permits it. Active legal or operational holds are represented separately. Conflicts between deletion and holds are surfaced as `conflict`; Everkeep does not hide them inside backup retention.

## Recovery-Point Ingestion

Recovery points are accepted as immutable logical records keyed by recovery-point ID. Duplicate IDs fail rather than silently overwriting evidence.

## Recovery Center Projection

The first executable projection combines registered resources, effective policies, recovery points, and Recovery Readiness results into query-ready resource summaries. A resource is not marked protected merely because it is registered; it requires both an effective policy and at least one recovery point.

## Current Boundary

This code provides deterministic models and validation. It does not claim that backups, immutable storage, isolation, restore tests, or recovery execution are deployed. Runtime services must supply evidence before public or UI claims exceed this boundary.
