# Everkeep

Everkeep is GoreeCloud's platform-wide resilience, preservation, backup, recovery, portability, continuity, succession, and digital-legacy subsystem.

It is a foundational technical system, not merely the name of GoreeCloud Backup, a visual identity, or a presentation layer. Everkeep provides shared infrastructure, contracts, evidence, policies, and recovery services that GoreeCloud applications and infrastructure can use without independently implementing complete resilience systems.

## Platform boundary

- **GoreeCloud Backup** is the user-facing backup and restore application powered by Everkeep.
- **Everkeep** defines and coordinates shared protection, recovery, preservation, portability, retention, continuity, succession, and assurance capabilities.
- Storage systems, databases, snapshot engines, replication systems, archive providers, and infrastructure platforms remain implementation components beneath Everkeep and must produce evidence for claims Everkeep surfaces.

Everkeep must never convert an unsupported capability into a public protection claim. Missing, stale, malformed, unverified, or unavailable recovery evidence fails closed.

## Foundational systems

- **Privacy Shield** — control, consent, minimization, retention authority, transfer authority, and deletion governance.
- **Wardveil Security** — protection, trust, threat detection, tamper resistance, and security response.
- **Everkeep** — survival, recoverability, integrity, preservation, continuity, portability, and authorized succession.
- **GoreeCloud Mesh** — coordination and governance plane connecting applications, services, devices, identities, permissions, events, and shared platform capabilities.
- **Glaze UI** — interaction, accessibility, responsive behavior, and evidence-backed state presentation.

## Core domains

1. **Resilience** — backups, snapshots, versions, replicas, recovery points, rollback, and restoration.
2. **Preservation** — archives, integrity, provenance, format longevity, preservation metadata, and long-term verification.
3. **Continuity** — disaster recovery, service recovery, failover, dependency-aware restoration, and recovery exercises.
4. **Portability** — exports, imports, migration packages, documented formats, manifests, and independent verification.
5. **Succession** — digital legacy, trusted contacts, successor policies, emergency recovery, selective transfer, and authorized destruction.
6. **Assurance** — recovery evidence, restore testing, policy compliance, measurable RPO/RTO objectives, and readiness evaluation.

## Phase 1 core

Phase 1 establishes the implementable Everkeep core:

- Resource Registry
- Protection Policy Engine
- Recovery Point Service
- Evidence Service
- Retention Engine
- Verification Service
- Recovery Orchestrator
- GoreeCloud Mesh adapter
- Recovery Center API foundation

See `docs/PHASE-1-CORE.md`.

## Machine-readable contracts

Existing continuity/adoption contracts remain part of the repository. Phase 1 adds platform-core contracts:

- `contracts/everkeep.resource.schema.json` — protected resource identity, ownership, source, tier, relationships, and governing policy references.
- `contracts/everkeep.protection-policy.schema.json` — RPO/RTO, redundancy, immutability/isolation, retention, verification, placement, and authorization requirements.
- `contracts/everkeep.recovery-point.schema.json` — recovery-point type, integrity, protected copies, failure domains, retention, clean-state classification, and recovery eligibility.
- `contracts/everkeep.evidence.schema.json` — normalized protection, verification, recovery, policy, RPO/RTO, copy assurance, dependency, key-material, and readiness evidence.

The prior contracts remain available for continuity state, adoption, acceptance, identity, semantic color, and Mesh integration.

## Recovery standard

Everkeep distinguishes:

**Backup Exists**

from:

**Backup Exists + Integrity Verified + Policy Compliant + Recovery Tested + Recoverable**

A backup job completing successfully is never sufficient by itself to produce a recovery-ready state.

## Protection principles

Everkeep favors verified restore capability over backup existence, portable and documented data over lock-in, explicit retention over accidental permanence, independent failure domains over a single recovery mechanism, dependency-aware restoration over isolated component recovery, and preservation of meaning, metadata, provenance, and relationships rather than raw bytes alone.

High-value policies may require immutable or isolated copies, off-site protection, multi-party authorization for destructive changes, malware checks before restoration, and a Recovery Sandbox before promotion to production. These are policy capabilities and must not be represented as deployed unless runtime evidence proves them.

## Status

**Phase 1 core architecture in development.** The foundational identity, continuity/adoption contracts, canonical visual identity, and evidence-gated integration model remain intact. Protected-resource, protection-policy, recovery-point, and evidence contracts now establish the first implementable Everkeep service boundary. Runtime deployment and application adoption remain evidence-gated.
