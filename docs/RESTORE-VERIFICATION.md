# Everkeep Restore Verification Evidence

Everkeep owns GoreeCloud recovery and restore-verification authority. This contract provides a resource-scoped evidence record that other GoreeCloud systems may consume when they need proof that a real recovery exercise completed successfully.

## Purpose

A recovery capability, backup, snapshot, PITR bookmark, healthy storage backend, or successful deployment is not restore verification. Restore verification requires an actual bounded exercise against an identified recovery point and target revision, followed by integrity and restored-state verification.

The canonical machine-readable contract is `contracts/everkeep.restore-verification.schema.json`.

## Required target binding

Every record identifies the target system, component, resource, and exact deployed revision. A consumer must reject evidence for a different target or revision. A later deployment requires new restore-verification evidence rather than inheriting an earlier result.

## Passing evidence

A consumer may treat a restore verification as passed only when all of the following are true:

- `environment` matches the environment being accepted;
- `status` is `pass`;
- `authoritative` is `true`;
- the target exactly matches the resource and deployed revision under review;
- `isolatedVerification` is `true`;
- `integrityVerified` is `true`;
- `restoredStateVerified` is `true`;
- at least one evidence reference is present; and
- timestamps describe a completed exercise rather than a future or incomplete operation.

A restore verification should normally run in an isolated recovery/test target. `promotionToProductionPerformed` records whether the exercise promoted restored state into production; a passing verification does not require production promotion.

## Wardveil Security integration

Wardveil Security may consume an authoritative Everkeep restore-verification record to satisfy a bounded recovery acceptance requirement for the exact Wardveil runtime revision named in the target. This does not make Wardveil a recovery authority and does not allow Everkeep to manufacture Wardveil trust, authorization, malware-cleanliness, incident state, protection execution, or `Protected by Wardveil` claims.

For the Wardveil Cloudflare persistence runtime, the intended target values are:

- system: `Wardveil Security`
- component: `Cloudflare persistence runtime`
- resourceId: `goreecloud-wardveil-persistence`
- deployedRevision: the exact 40-character Wardveil production revision being accepted.

## Fail-closed behavior

Missing, malformed, non-authoritative, unknown, failed, stale-target, revision-mismatched, integrity-unverified, or restored-state-unverified evidence must not satisfy a restore-verification requirement. PITR availability remains recovery-capability evidence only until this separate restore exercise succeeds.

## Authority boundary

Everkeep remains the resilience, backup, restore, and recovery-verification authority. Consumers may validate and use Everkeep evidence within an explicit integration contract, but they may not rewrite, upgrade, or fabricate the recovery result. The record includes `securityStateAuthorityTransferred=false` to make clear that recovery evidence does not transfer Wardveil Security authority to Everkeep.
