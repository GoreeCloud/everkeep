# Everkeep

Everkeep is GoreeCloud's platform-wide identity for resilience, recovery, preservation, portability, succession, and digital legacy.

It defines how GoreeCloud communicates and evaluates whether protected information can survive failures, migrations, application replacement, infrastructure changes, and long-term technology change without turning Everkeep into a backup engine or storage product.

## Core boundary

Everkeep is an identity, governance, evidence, and presentation layer.

It does **not** replace:

- **GoreeCloud Backup**, which performs backup and restore operations.
- Storage systems such as TrueNAS or ZFS.
- Application-native export, migration, or recovery mechanisms.
- Replication and synchronization systems.
- Disaster-recovery infrastructure.
- Future succession or digital-legacy applications.

Everkeep may summarize evidence from those systems, but the authoritative system remains responsible for producing and enforcing its own state.

## Platform identity model

- **Glaze UI** — design and user experience.
- **Wardveil Security** — security and protection.
- **Privacy Shield** — privacy protections and controls.
- **Everkeep** — resilience, recovery, preservation, portability, succession, and digital legacy.
- **GoreeCloud Suite** — the unified collection of GoreeCloud applications and services.

## Everkeep principles

Everkeep is built around the idea that the information GoreeCloud protects matters more than any particular application, server, vendor, or technology.

A continuity claim must therefore be evidence-based. Missing, stale, unverified, incomplete, or unavailable recovery evidence must not be presented as healthy or recoverable.

Everkeep favors:

- verified restore capability over the existence of a backup,
- portable data over application lock-in,
- documented recovery over assumptions,
- multiple independent recovery layers over a single mechanism,
- clear ownership and succession paths over undocumented dependency on one administrator,
- preservation of meaning, context, metadata, and history—not merely raw bytes.

## Repository contracts

- `CONTINUITY.md` — Everkeep identity, scope, terminology, and continuity evidence model.
- `STATUS.md` — normalized continuity state semantics and aggregation rules.
- `ADOPTION.md` — minimum requirements for GoreeCloud applications and services that integrate Everkeep.
- `SECURITY.md` — security, privacy, and sensitive-information boundaries.
- `ICON.md` — Everkeep visual-identity concept, canonical-asset path, and approval gate.
- `contracts/continuity.identity.json` — machine-readable Everkeep identity and governance contract.
- `contracts/continuity.status.schema.json` — machine-readable continuity status-record schema.
- `contracts/continuity.adoption.schema.json` — machine-readable Everkeep adoption-manifest schema.
- `examples/goreecloud-backup.adoption.json` — reference producer manifest for GoreeCloud Backup.
- `examples/goreecloud-manager.adoption.json` — reference consumer manifest for GoreeCloud Manager.
- `scripts/validate_continuity.py` — deterministic Everkeep repository validator.
- `.github/workflows/validate.yml` — CI validation.

## Adoption model

Everkeep distinguishes **producers**, **consumers**, and future **producer-consumers** through a versioned adoption manifest. An adoption manifest declares the continuity dimensions a project represents, its authoritative-source boundary, read-only behavior, fail-closed requirement, and the shared status schema it consumes or emits.

The included Backup and Manager manifests are reference contracts, not claims that either application has completed runtime Everkeep acceptance. Actual adoption remains evidence-gated and must satisfy `ADOPTION.md` at an exact source revision.

## Visual identity

The Everkeep visual identity is **approved and canonical**. Its authoritative source is `assets/everkeep.svg`, and all derived assets must trace back to that source.

## Status

**Foundation 0.4.** The Everkeep rename is authoritative across the identity contract, documentation, validation workflow, reference adoption model, and canonical visual identity. The normalized continuity status model, machine-readable status and adoption schemas, reference Backup and Manager adoption manifests, fail-closed governance, and validator foundation remain intact. Runtime adoption remains evidence-gated.
