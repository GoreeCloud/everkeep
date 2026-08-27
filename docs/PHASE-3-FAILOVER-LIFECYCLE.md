# Everkeep Phase 3 — Failover Lifecycle Detail

## Purpose

This increment adds a separate lifecycle detail projection for Everkeep's existing Phase 3.5 simulation-only failover executor. It complements, rather than replaces, the Recovery Center 1.5 summary and the existing failover-operations projection.

The projection keeps three concepts separate:

- executor lifecycle state;
- rollback assurance;
- failover acceptance.

A transport or lifecycle state does not become a recovery-readiness verdict, and historical or missing evidence is not upgraded into current assurance.

## Lifecycle detail

`contracts/everkeep.recovery-center.failover-lifecycle.schema.json` and `scripts/recovery_center_lifecycle.py` expose one read-only record per known execution identifier. Executor state may be active, terminal, or `unknown`.

An unrecognized or missing executor state for an existing execution identifier becomes `unknown`; it is not rewritten as blocked, failed, completed, or successful. Unknown lifecycle evidence sets `refreshRequired: true`.

Completed executions separately expose rollback assurance and failover acceptance as `pass`, `fail`, or `unknown`. Those states remain independent: passing rollback assurance does not create failover acceptance, and passing acceptance does not create rollback assurance.

## Recovery Center actions

The detail projection reuses existing evidence-bounded Recovery Center actions:

- `inspect-failover-drill` for active, cancelled, or unknown lifecycle evidence;
- `inspect-failover-drill-blocker` for blocked or failed executor evidence;
- `review-rollback-assurance` when a completed drill lacks passing rollback assurance;
- `evaluate-failover-acceptance` when a completed drill lacks passing environment- and revision-bound acceptance evidence.

It defines no `execute-failover` action.

## Safety boundary

Every lifecycle detail record states `simulationOnly: true` and `externalEffectsAuthorized: false`. The projection cannot switch traffic, mutate source data, provision alternate infrastructure, embed credentials, mint execution authority, or turn a drill record into production failover permission.

This change does not alter Recovery Center 1.5, the Phase 3.5 failover-operations 1.0 contract, or the simulation-only executor implementation. Any future production-effect executor remains a separate implementation, authority, validation, and deployment boundary.
