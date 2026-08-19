# GoreeCloud Continuity

GoreeCloud Continuity is GoreeCloud's platform-wide identity for resilience, recovery, preservation, portability, succession, and digital legacy.

It defines how GoreeCloud communicates and evaluates whether protected information can survive failures, migrations, application replacement, infrastructure changes, and long-term technology change without turning Continuity into a backup engine or storage product.

## Core boundary

Continuity is an identity, governance, evidence, and presentation layer.

It does **not** replace:

- **GoreeCloud Backup**, which performs backup and restore operations.
- Storage systems such as TrueNAS or ZFS.
- Application-native export, migration, or recovery mechanisms.
- Replication and synchronization systems.
- Disaster-recovery infrastructure.
- Future succession or digital-legacy applications.

Continuity may summarize evidence from those systems, but the authoritative system remains responsible for producing and enforcing its own state.

## Platform identity model

- **Glaze UI** — design and user experience.
- **Wardveil Security** — security and protection.
- **Privacy Shield** — privacy protections and controls.
- **GoreeCloud Continuity** — resilience, recovery, preservation, portability, succession, and digital legacy.
- **GoreeCloud Suite** — the unified collection of GoreeCloud applications and services.

## Continuity principles

GoreeCloud Continuity is built around the idea that the information GoreeCloud protects matters more than any particular application, server, vendor, or technology.

A Continuity claim must therefore be evidence-based. Missing, stale, unverified, incomplete, or unavailable recovery evidence must not be presented as healthy or recoverable.

Continuity favors:

- verified restore capability over the existence of a backup,
- portable data over application lock-in,
- documented recovery over assumptions,
- multiple independent recovery layers over a single mechanism,
- clear ownership and succession paths over undocumented dependency on one administrator,
- preservation of meaning, context, metadata, and history—not merely raw bytes.

## Repository contracts

- `CONTINUITY.md` — identity, scope, terminology, and evidence model.
- `STATUS.md` — normalized Continuity state semantics and aggregation rules.
- `ADOPTION.md` — minimum requirements for GoreeCloud applications and services that integrate Continuity.
- `SECURITY.md` — security, privacy, and sensitive-information boundaries.
- `ICON.md` — visual-identity concept, canonical-asset path, and approval gate.
- `contracts/continuity.identity.json` — machine-readable identity and governance contract.
- `contracts/continuity.status.schema.json` — machine-readable status-record schema.
- `contracts/continuity.adoption.schema.json` — machine-readable adoption-manifest schema.
- `examples/goreecloud-backup.adoption.json` — reference producer manifest for GoreeCloud Backup.
- `examples/goreecloud-manager.adoption.json` — reference consumer manifest for GoreeCloud Manager.
- `scripts/validate_continuity.py` — deterministic repository validator.
- `.github/workflows/validate.yml` — CI validation.

## Adoption model

Continuity now distinguishes **producers**, **consumers**, and future **producer-consumers** through a versioned adoption manifest. An adoption manifest declares the dimensions a project represents, its authoritative-source boundary, read-only behavior, fail-closed requirement, and the shared status schema it consumes or emits.

The included Backup and Manager manifests are reference contracts, not claims that either application has completed runtime Continuity acceptance. Actual adoption remains evidence-gated and must satisfy `ADOPTION.md` at an exact source revision.

## Visual identity

The Continuity visual identity is currently **pending**. The canonical source asset is reserved as `assets/continuity.svg`, but no provisional artwork is treated as approved. The acceptance boundary is defined in `ICON.md`.

## Status

**Foundation 0.3.** The identity contract, normalized status model, machine-readable status and adoption schemas, reference Backup and Manager adoption manifests, fail-closed governance, validator foundation, and visual-identity approval gate are established. Runtime adoption and canonical icon approval remain evidence-gated implementation steps.
