# Everkeep Identity and Evidence Model

## Purpose

Everkeep defines the platform-wide identity and common language for resilience, recovery, preservation, portability, succession, and digital legacy across GoreeCloud.

Its purpose is to answer a higher-level question than whether a service is currently online: **Can the information and capability represented by this system survive failure, change, migration, replacement, or long-term transition?**

## Scope

Everkeep may represent evidence about:

- backup coverage,
- restoration capability,
- recovery-point freshness,
- recovery-time readiness,
- data exportability,
- migration portability,
- dependency recoverability,
- storage redundancy,
- independent recovery layers,
- documentation completeness,
- ownership and custody,
- succession readiness,
- long-term preservation,
- metadata and provenance preservation,
- digital-legacy transfer readiness.

## Authority boundary

Everkeep does not perform or own the underlying technical operation merely because it presents its state.

Examples:

- GoreeCloud Backup remains authoritative for its own backup and restore operations.
- An application remains authoritative for its native export and import behavior.
- TrueNAS/ZFS remains authoritative for storage-pool state and filesystem integrity.
- Proxmox remains authoritative for VM snapshots and VM backup state.
- A recovery procedure remains authoritative only when its defined validation evidence exists.

Everkeep integrations should be read-only by default. Any future remediation workflow must preserve the authority and audit boundary of the technical system being changed.

## Normalized states

Everkeep uses conservative continuity states:

- `ready` — required continuity evidence for the represented scope is current and verified.
- `attention` — continuity capability exists, but one or more non-critical requirements require action.
- `degraded` — required continuity capability is materially impaired.
- `unknown` — required evidence is missing, stale, unavailable, incomplete, or unverified.
- `not_applicable` — the continuity dimension does not apply to the represented scope.

An Everkeep summary must never be more favorable than the weakest required evidence in its represented scope. Required `unknown` evidence blocks `ready`.

## Evidence requirements

An Everkeep continuity record should preserve, where applicable:

- authoritative source,
- explicit scope,
- observation or verification time,
- freshness limit,
- validation method,
- last successful restore or recovery test,
- recovery target or destination,
- portability or export proof,
- known limitations,
- evidence reference that does not expose secrets.

The existence of backup files alone is not proof of recoverability.

## Relationship to GoreeCloud Backup

GoreeCloud Backup is a product. Everkeep is a platform identity and cross-product continuity model.

Backup can be one producer of Everkeep evidence, but Everkeep also includes recovery testing, portability, migration, preservation, succession, dependency recovery, documentation, and long-term information survivability.

## Relationship to Wardveil Security and Privacy Shield

Everkeep is separate from security and privacy.

Wardveil Security may report whether recovery systems are securely configured or whether an Everkeep-related control has a security problem. Privacy Shield may protect privacy within its own scope. Everkeep reports whether information and capability can survive disruption or transition.

No identity should silently absorb the technical responsibilities of another.

## Relationship to Glaze UI

Everkeep-facing interfaces use Glaze UI. Continuity status must not depend on color alone and must remain understandable through text, iconography, accessible naming, and machine-readable state.

## Digital legacy and succession

Everkeep includes the long-term requirement that protected information remain understandable, recoverable, portable, and transferable to its rightful owner or an approved future custodian.

Succession readiness must not be inferred merely because backups exist. It requires explicit documentation, access-recovery planning, ownership information, and a controlled transfer path appropriate to the represented data.

## Fail-closed principle

Everkeep never turns absence of evidence into reassurance.

If a required restore test has never been performed, if the last known evidence is stale, if a repository cannot be reached, or if export integrity has not been verified, the corresponding state is not `ready`.
