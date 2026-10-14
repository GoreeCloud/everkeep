# Wardveil Cloudflare persistence — isolated Everkeep restore preflight

**Status:** Non-executing readiness plan. **Not a restore exercise, backup, or accepted recovery record.**

## Exact scope

- Wardveil resource: `goreecloud-wardveil-persistence`.
- Frozen Wardveil Seal source: `cc493530c02925a4404c54d2767c15d9fbfa0835`.
- Target environment: `production`, but **recovery execution target must be an entirely separate, nonproduction isolated instance**.
- Everkeep output when independently verified in the future: producer-owned `everkeep.restore-verification.v1.1` accepted by the current Wardveil consumer.
- Everkeep implementation boundary: `scripts/recovery_orchestrator.py` plans and gates; it does not execute restores or create recovery evidence.

## Current blockers (2026-10-14)

The deployed Wardveil Worker has real private-RPC evidence and a separately verified Cloudflare stored-log marker, but **no authoritative Everkeep isolated-restore record exists**. Read-only checks of the connected GoreeCloud VPS and laptop did not find an Everkeep-named service/container or a local PostgreSQL listener. That does not rule out a remote deployment.

Cloudflare SQLite Durable Object PITR offers `getCurrentBookmark()` and `onNextSessionRestoreBookmark()` on the **same Durable Object instance**. Calling the latter on the production Wardveil object would mutate authoritative storage, so it **must not** be used for a recovery acceptance test against live production. A bookmark proves PITR capability, not that the contents were restored into a separate target. See [Cloudflare SQLite Durable Object PITR](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/#pitr-point-in-time-recovery-api).

## Non-executing preflight

Run:

```bash
python3 scripts/wardveil_cloudflare_restore_preflight.py
python3 scripts/test_wardveil_cloudflare_restore_preflight.py
```

Optional JSON input to `--manifest path.json` may declare `deployedRevision`, a separate `isolatedTargetId`, and `gates` with only `state` and nonsecret `evidenceRef`. Do not include credentials, source contents, private data or backup payloads. The script only returns blocker codes and a four-step *proposed* sandbox plan. It never invokes Cloudflare or Everkeep runtime APIs, does not write source or target storage, and never marks any recovery exercise performed. A caller claiming that all gates pass still gets only `requires_independent_authoritative_review` and **not execution authorization**.

Required gates include existing Everkeep Identity/Privacy/Wardveil/recovery-point/dependency/key-material gates plus independently verified Everkeep runtime, exact source revision, durable recovery point/export, target isolation, source write fence, **actual cross-object restore method**, and an integrity witness.

## Path to an actual accepted exercise

1. Identify the real Everkeep runtime, deployment revision and independent authorization provider. Confirm a source-bound recovery point and a **supported way to restore it into a new isolated target**. Stop if only an in-place PITR operation is available.
2. Verify an isolated disposable target cannot address or mutate the production namespace, with a deliberate source readback before/after the exercise and a bounded cleanup plan.
3. Perform an actual restore of protected *synthetic* records/checkpoints/digests through the approved recovery engine into that separate target. Verify state, digest, omitted/altered records and recovery-point identity on the target; validate that the production source remained unchanged.
4. Only the deployed, authoritative Everkeep provider may issue a fresh `schemaVersion=1.1` record with `status=pass`, `authoritative=true`, `isolatedVerification=true`, `integrityVerified=true`, `restoredStateVerified=true`, nonempty immutable evidence references, exact production target/revision, timezone-qualified timestamps and producer-owned `freshUntil`. `securityStateAuthorityTransferred=false` and `promotionToProductionPerformed=false` are required.
5. Wardveil independently validates the exact revision and freshness via its own `contracts/wardveil.everkeep.restore-verification.json` and consumer validator. The result can satisfy **only** `restore_verification_exercise`; it does not confer Anchor, runtime acceptance, or `Protected by Wardveil`.

Tracking: [Everkeep #79](https://github.com/GoreeCloud/everkeep/issues/79). Production/private-RPC and independent log evidence: [Wardveil #214](https://github.com/GoreeCloud/wardveil/issues/214).

## Fail-closed requirement

Missing source/export isolation, unknown restore implementation, source mutation capability, unavailable runtime, out-of-scope identity or stale evidence: **stop, leave `restorePerformed=false`, and do not release/publish a passing restore record**.
