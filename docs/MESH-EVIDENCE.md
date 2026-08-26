# Everkeep — GoreeCloud Mesh Evidence Boundary

Everkeep can publish bounded resilience, recovery, preservation, and continuity evidence through GoreeCloud Mesh using the GoreeCloud Evidence Envelope v1.

The source profile is `contracts/everkeep.mesh-evidence-profile.json`.

## Authority separation

Everkeep remains authoritative for recoverability, integrity verification, recovery readiness, preservation integrity, continuity readiness, portability, and succession evidence. Mesh may coordinate, persist, correlate, and transport those records, but it must not reinterpret them into stronger recovery claims.

In particular, Mesh must never convert:

`backup exists`

into:

`verified + policy compliant + recovery tested + recoverable`.

Only Everkeep producer contracts and evidence can establish those meanings.

## Restore verification

Resource-scoped restore-verification evidence is a primary integration target for the envelope. A Mesh transport record should carry only the bounded derived result, resource identity/scope, producer contract, exact source revision, observation/validity timestamps, opaque evidence reference, and optional digest.

Restored file bodies, database contents, snapshot payloads, archive content, encryption keys, or other recovery material must not be placed in the envelope.

## Wardveil coordination

Wardveil may consume Everkeep restore or recovery evidence when performing compromise containment, recovery safety checks, or post-restore security verification. Wardveil remains authoritative for the security result; Everkeep remains authoritative for the recovery/restore result.

The two evidence streams may be correlated by Mesh, but correlation does not merge their authority.

## Privacy Shield coordination

Privacy Shield remains authoritative for privacy constraints that affect Everkeep operations, including retention authority, deletion obligations, export restrictions, succession permissions, and transfer constraints.

Everkeep may use those obligations to decide whether a recovery, preservation, archive, portability, or succession operation is permitted. It must not weaken them merely because recovery data exists.

## Freshness and readiness

Everkeep is responsible for declaring the validity window appropriate to each evidence family. Restore verification, RPO/RTO readiness, retention compliance, copy assurance, and continuity exercises may have different freshness semantics.

Mesh must preserve the producer-declared validity window and fail closed when an envelope is expired or future-dated.

## Acceptance boundary

This profile is a source-level interoperability contract. It does not itself establish deployment acceptance, service health, recovery readiness, Phase 1 completion, or production approval for any Everkeep runtime.
