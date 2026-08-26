# Everkeep Phase 1 — Core Architecture

Phase 1 establishes the minimum implementable Everkeep platform core. It does not claim deployed backup, immutable storage, multi-provider resilience, or tested recoverability until runtime evidence exists.

## Core services

1. **Resource Registry** — identifies protectable resources, ownership, source application, preservation tier, relationships, policy references, and lifecycle metadata.
2. **Protection Policy Engine** — evaluates backup, redundancy, placement, retention, verification, authorization, and recovery objectives.
3. **Recovery Point Service** — registers versions, snapshots, backups, database PITR points, archive points, copy placement, integrity state, retention, and recovery eligibility.
4. **Evidence Service** — produces normalized protection, verification, policy-compliance, RPO/RTO, restore-test, dependency, and key-readiness evidence.
5. **Retention Engine** — evaluates retention, expiration, delayed deletion, privacy deletion, immutable retention windows, and policy conflicts.
6. **Verification Service** — performs checksum validation, copy validation, stale-evidence detection, and scheduled restore testing.
7. **Recovery Orchestrator** — plans and executes authorized recovery while preserving source data by default and supporting isolated recovery targets.
8. **Mesh Adapter** — exposes Everkeep operations and emits normalized lifecycle events to GoreeCloud Mesh.
9. **Recovery Center API** — supplies UI-ready protection inventory, recovery readiness, evidence, policy state, and recovery actions.

## Canonical core entities

- Protected Resource
- Protection Policy
- Recovery Point
- Protected Copy
- Integrity Verification
- Restore Test
- Protection Evidence
- Retention Decision
- Recovery Plan
- Recovery Execution
- Preservation Archive
- Preservation Capsule
- Succession Policy

The first four machine-readable contracts are defined in `contracts/everkeep.*.schema.json`.

## Core state rules

Everkeep must fail closed for recovery claims. A completed backup operation alone must never produce `Recovery Ready`.

A resource may be considered recovery-ready only when required policy evidence is current and confirms, as applicable:

- an eligible recovery point exists;
- integrity verification passed;
- required protected-copy count and failure-domain diversity are satisfied;
- required immutable, isolated, or off-site copies exist;
- retention state permits recovery;
- Privacy Shield permits the operation;
- Wardveil does not block the recovery point or session;
- Identity authorization requirements are satisfied;
- required key material and dependencies are recoverable;
- required restore-test evidence is current and successful.

Missing or stale evidence must degrade readiness rather than be interpreted as success.

## Initial Mesh operation surface

- `everkeep.protectResource`
- `everkeep.createRecoveryPoint`
- `everkeep.listRecoveryPoints`
- `everkeep.verifyIntegrity`
- `everkeep.queryProtectionStatus`
- `everkeep.queryRecoveryEligibility`
- `everkeep.requestRecoveryEvidence`
- `everkeep.restoreResource`
- `everkeep.performRecoveryTest`
- `everkeep.applyRetentionPolicy`
- `everkeep.changePreservationTier`

## Initial Mesh events

- `everkeep.protection.completed`
- `everkeep.protection.failed`
- `everkeep.recovery-point.created`
- `everkeep.recovery-point.expired`
- `everkeep.verification.completed`
- `everkeep.integrity.warning`
- `everkeep.restore-test.completed`
- `everkeep.recovery.started`
- `everkeep.recovery.completed`
- `everkeep.recovery.failed`
- `everkeep.policy.violation`
- `everkeep.readiness.changed`

## Recovery Center Phase 1 surfaces

The first UI/API implementation should expose:

- protected and unprotected resources;
- latest recovery point;
- last successful verification;
- last successful restore test;
- recovery eligibility;
- policy-compliance state;
- RPO status;
- available copy count and failure domains;
- immutable/isolated-copy requirement state;
- retention expiration;
- dependency and key-material blockers;
- evidence-backed readiness score with underlying factors;
- available recovery and verification actions.

## Security and privacy gates

Everkeep is not authoritative for identity, privacy, or security policy. It consumes their decisions and must retain attributable evidence references.

- Privacy Shield governs backup, retention, archival, replication, export, succession, restoration, and deletion authority.
- Wardveil Security governs trust, malicious-content detection, tamper state, recovery-session protection, destructive-action controls, and ransomware response.
- GoreeCloud Identity governs authentication, reauthentication, role/permission checks, trusted contacts, successor verification, MFA, and quorum authorization.
- GoreeCloud Mesh coordinates requests, events, policy context, and platform evidence.

## Phase 1 completion criteria

Phase 1 is complete only when:

- all core schemas validate;
- a resource can be registered and assigned a policy;
- a recovery point can be recorded with protected-copy and integrity metadata;
- evidence can be generated deterministically from current state;
- stale and missing evidence fail closed;
- retention conflicts are surfaced;
- Mesh request/event contracts are versioned;
- Recovery Center can read the normalized state;
- automated contract tests cover valid and invalid examples;
- no UI claims exceed available runtime evidence.
