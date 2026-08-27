# Everkeep Phase 2 — Preservation and Portability

Everkeep preservation must retain more than raw bytes. A durable preservation object needs enough integrity, provenance, relationship, policy, and format information to prove what was preserved and to make future verification and migration possible.

## Preservation Capsule

A Preservation Capsule is a manifest-backed preservation unit. The Phase 2 contract records:

- stable resource identity;
- source-provided content digest;
- media type and size when known;
- provenance references;
- relationship references;
- integrity-evidence references;
- applicable preservation policy references;
- deterministic capsule digest;
- aggregate integrity state.

The reference builder never invents a content digest. If a resource does not have a digest from the authoritative storage or application layer, capsule construction must fail closed.

## Integrity state

Capsule integrity is:

- `verified` only when every included entry explicitly has successful integrity evidence;
- `failed` when any included entry explicitly fails integrity verification;
- `unknown` when required integrity evidence is incomplete or unavailable.

The capsule digest protects the canonical manifest representation. It is not a substitute for per-object content verification.

## Portability manifest

A portability manifest is derived from a Preservation Capsule and records the resource identifiers and content digests that a receiving system can independently verify.

An export is marked `portable: true` only when:

1. Privacy Shield or another authoritative policy source explicitly permits the export; and
2. the source Preservation Capsule is currently integrity-verified.

Missing authority or unknown integrity therefore blocks a positive portability claim.

## Privacy and security boundaries

Privacy Shield remains authoritative for export, transfer, retention, deletion, and succession authority. Wardveil Security may add malware, tamper, or destination-safety requirements. GoreeCloud Identity governs who may request or approve export operations. Everkeep records and evaluates their evidence; it does not replace those systems.

## Long-term direction

Later preservation slices can add:

- format-risk detection and migration planning;
- fixity re-verification schedules;
- redundant archive placement and repair;
- WARC or application-specific preservation packages;
- cryptographic provenance chains;
- cold-storage and offline-media evidence;
- independent import validation;
- selective succession packages;
- legal-hold and deletion-conflict handling.

## Evidence boundary

These contracts create deterministic preservation and portability manifests. They do not claim that archival storage, format migration, external export delivery, offline copies, or long-term media refresh are deployed until runtime evidence proves those capabilities.
