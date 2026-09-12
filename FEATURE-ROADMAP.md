# Everkeep — Feature Roadmap

**Status:** Active roadmap control  
**As of:** 2026-09-11  
**Authoritative project record:** Project Specification — Everkeep  
**Canonical repository:** GoreeCloud/goreecloud-everkeep  
**Drive control:** `GoreeCloud/Feature Roadmap/Everkeep/FEATURE-ROADMAP.docx`

## Purpose

This file is the repository-side feature roadmap control for Everkeep. It records current planned and recommended feature work without replacing the authoritative project record, implementation evidence, release gates, or GoreeCloud Tasks Management.

## Roadmap

| ID | Feature / obligation | Priority | Current state |
| --- | --- | --- | --- |
| FR-001 | Reconcile and maintain every current planned or recommended Everkeep feature from the authoritative project record and verified repository evidence in this roadmap. | High | Ongoing control |
| FR-002 | Move actionable feature obligations into GoreeCloud Tasks Management when required, preserving priority, dependency, and lifecycle disposition. | High | Ongoing control |
| FR-003 | Do not mark features implemented, complete, cancelled, or superseded without authoritative evidence and synchronized repository/Drive roadmap updates. | High | Ongoing control |
| FR-004 | Complete live GoreeCloud Identity, Privacy Shield, and Wardveil authority-provider integrations for recovery operations while preserving each system's independent authority and preventing authentication, privacy state, or security state from being manufactured by Everkeep. | P0 | Partially Source Implemented. Everkeep already carries source contracts and acceptance boundaries for these authorities, but live provider connectivity and target-environment production acceptance remain pending. |
| FR-005 | Establish accepted production GoreeCloud Monitoring ingestion and GoreeCloud Notify delivery for minimized continuity signals, including evidence provenance, retry/delivery behavior, privacy minimization, and exact-environment acceptance. | P1 | Planned / production evidence pending. Source-side Monitoring/Notify adapters and minimized delivery concepts exist, but verified production ingestion/delivery is not established. |
| FR-006 | Execute and verify real restore operations in isolated environments, binding each result to exact protected resource, environment, source revision, protection policy, recovery point, integrity state, and authoritative restore evidence. | P0 | In Development. Everkeep has restore-verification contracts, Recovery Sandbox/dry-run foundations, scheduled restore-test decisions, and resource-scoped evidence; real workload restore evidence remains required before Recovery Ready claims. |
| FR-007 | Advance controlled recovery execution only when approval, exact plan/revision, target readiness, dependency state, key material, Identity authority, Privacy Shield constraints, Wardveil security acceptance, rollback assurance, and operator gates can be revalidated at execution time. | P0 | Simulation/controlled-drill foundation implemented; production-effect authority pending. Current Phase 3/3.5 evidence deliberately separates simulations and drills from live production failover or rollback authority. |
| FR-008 | Migrate and accept Continuity Center on the current Stable Glaze UI target while preserving evidence-backed Recovery Ready, At Risk, Recovery Blocked, Unknown, topology, assurance, drill, rollback, and degraded/error states without implying unsupported recoverability. | P1 | Migration required. The accepted deployed Continuity Center presentation is historical Glaze UI 2.1.0 evidence; current Platform Contract reconciliation in Draft PR #58 requires Glaze UI 1.3.0 and fresh rendered/accessibility/resilience/rollback/production acceptance before current conformance may be claimed. |
| FR-009 | Maintain portability, preservation, and succession/digital-legacy as first-class continuity domains, including preservation capsules, portability manifests, retention/deletion constraints, succession eligibility, long-term verification, and privacy-governed transfer/export behavior. | P1 | Substantial source foundations implemented; application/runtime adoption and production acceptance remain incremental and evidence-gated. |
| FR-010 | Require every applicable GoreeCloud application/service to define and validate its Everkeep protection contract, recovery objectives, required evidence, restore test, retention/privacy obligations, dependency/key-material requirements, and production acceptance boundary. | P1 | Ongoing adoption obligation. Existing source contracts do not establish application-specific production acceptance for the full GoreeCloud portfolio. |
| FR-011 | Produce exact-workload production evidence that backup, integrity verification, restore, topology, failure-domain coverage, continuity objectives, failover, rollback, and recovery-assurance paths work for each protected workload and environment. | P0 | Production evidence gate — Pending/incomplete. A successful backup, source tests, fake-client CI, contract validity, or Mesh transport alone cannot satisfy this requirement. |
| FR-012 | Complete target-environment recovery automation and provider-specific execution only where approved, including alternate-target deployment/traffic changes, rollback, corruption handling, portability, failure isolation, observability, and explicit production approval. | P0 | Planned/controlled expansion. No general live production failover, production traffic switching, or provider-specific production recovery authority is established by current source candidates. |

## Recovery-claim boundary

Everkeep must continue to distinguish **Backup Exists** from **Backup Exists + Integrity Verified + Policy Compliant + Recovery Tested + Recoverable**. Missing, stale, malformed, unavailable, or unverified evidence fails closed. Source implementation, simulation, drill execution, presentation state, or a successful backup must never be relabeled as verified recoverability without the required exact-resource and exact-environment evidence.

## Maintenance and synchronization

This roadmap and the corresponding Drive `FEATURE-ROADMAP.docx` must remain materially synchronized with one another and with the authoritative project or service record. Update both copies whenever feature scope, priority, dependency, implementation status, cancellation, supersession, recommendation, or verification state materially changes.

No feature may be represented as complete or Stable solely because it appears in this roadmap. Completion and lifecycle claims require the applicable authoritative implementation, validation, review, release, and production evidence.

## Reconciliation rule

At each material feature change, reconcile this roadmap against the current authoritative project record, repository implementation state, applicable platform-system requirements, and GoreeCloud Tasks Management. Missing obligations, stale status, duplicated work, roadmap drift, or undocumented disposition changes are defects to correct.
