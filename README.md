# Everkeep

Everkeep is GoreeCloud's platform-wide resilience, preservation, backup, recovery, portability, continuity, succession, and digital-legacy subsystem.

It is a foundational technical system, not merely the name of GoreeCloud Backup, a visual identity, or a presentation layer. Everkeep provides shared infrastructure, contracts, evidence, policies, recovery planning, preservation manifests, and continuity services that GoreeCloud applications and infrastructure can use without independently implementing complete resilience systems.

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

Phase 1 established the first implementable Everkeep core:

- Resource Registry
- Protection Policy Engine
- Recovery Point Service
- Evidence Service
- Retention Engine
- Verification Service
- Recovery Orchestrator boundary
- GoreeCloud Mesh adapter
- Recovery Center API foundation
- PostgreSQL persistence and durable outbox semantics
- deployment, staging-verification, live-acceptance, and restore-verification evidence boundaries

See `docs/PHASE-1-CORE.md`.

## Phase 2 control plane

Phase 2 expands Everkeep from core protection records into an evidence-driven resilience control plane.

### Recovery Center

- Fleet-level Recovery Ready / At Risk / Recovery Blocked / Unknown projections.
- Protected vs. unprotected resource coverage.
- Explicit assurance coverage for integrity verification, restore testing, and policy compliance.
- Deterministic blocker prioritization.
- Evidence-authorized recommended actions.
- Fail-closed restore-action exposure.

See `docs/PHASE-2-RECOVERY-CENTER.md`.

### Recovery orchestration

- Dependency-aware recovery plans.
- Dry-run, isolated Recovery Sandbox, and production-target plan modes.
- Explicit Identity, Privacy Shield, Wardveil, evidence, recovery-point, dependency, and key-material gates.
- Source-preserving execution contracts with `sourceMutationAllowed: false`.
- Separate sandbox promotion boundary.

See `docs/PHASE-2-RECOVERY-ORCHESTRATION.md`.

### Preservation and portability

- Preservation Capsules with stable resource identities, content digests, provenance, relationships, policy references, and evidence references.
- Deterministic capsule-manifest digests.
- Aggregate integrity state that remains unknown when evidence is incomplete.
- Portable export manifests that require both export authority and verified capsule integrity.

See `docs/PHASE-2-PRESERVATION-PORTABILITY.md`.

## Machine-readable contracts

The repository includes contracts for continuity state, adoption, acceptance, resource identity, protection policy, recovery points, evidence, readiness, Mesh integration, runtime acceptance, and restore verification.

Phase 2 adds:

- `contracts/everkeep.recovery-action.schema.json`
- `contracts/everkeep.recovery-center.summary.schema.json`
- `contracts/everkeep.recovery-plan.schema.json`
- `contracts/everkeep.recovery-execution.schema.json`
- `contracts/everkeep.preservation-capsule.schema.json`
- `contracts/everkeep.portability-manifest.schema.json`

## Recovery standard

Everkeep distinguishes:

**Backup Exists**

from:

**Backup Exists + Integrity Verified + Policy Compliant + Recovery Tested + Recoverable**

A backup job completing successfully is never sufficient by itself to produce a recovery-ready state.

## Protection and preservation principles

Everkeep favors verified restore capability over backup existence, portable and documented data over lock-in, explicit retention over accidental permanence, independent failure domains over a single recovery mechanism, dependency-aware restoration over isolated component recovery, and preservation of meaning, metadata, provenance, and relationships rather than raw bytes alone.

High-value policies may require immutable or isolated copies, off-site protection, multi-party authorization for destructive changes, malware checks before restoration, and a Recovery Sandbox before promotion to production. These are policy capabilities and must not be represented as deployed unless runtime evidence proves them.

## Status

**Phase 2 resilience control-plane architecture in development.** Phase 1 identity, continuity/adoption contracts, runtime boundaries, persistence, canonical visual identity, and evidence-gated integration model remain intact. Recovery Center projections, dependency-aware recovery planning, execution authorization gates, Preservation Capsules, and portability manifests now define the next implementable service boundaries. Runtime deployment and application adoption remain evidence-gated.
