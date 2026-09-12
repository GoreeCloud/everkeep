# Everkeep — Feature Roadmap

**Status:** Active roadmap control  
**As of:** 2026-09-12  
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
| FR-003 | Do not mark features implemented, complete, cancelled, superseded, production-ready, or Stable without authoritative evidence and synchronized repository/Drive roadmap updates. | High | Ongoing control |
| FR-004 | Validate real restore operations in isolated environments and bind acceptance to the exact protected resource, deployed target revision, Everkeep source revision, recovery point, environment, evidence freshness, and verified restored state. | Critical | Source Validated contract foundation — Draft PR #60 adds additive restore-verification v1.2 for exact real isolated-restore evidence while preserving v1.0/v1.1. Exact head `9522e0e1788dfbb3e5ea8448c5d159a642bec23d` passed Validate Everkeep `34675136028` and dedicated isolated-restore v1.2 validation `34675136083`. The contract binds exact environment/resource/target/source/tree/recovery-point/artifact identity, requires `real_isolated_restore`, integrity and restored-state verification plus workload-specific passed checks, forbids source mutation and production promotion, and fails closed on stale/mismatched/weaker evidence. There are zero real v1.2 restore-evidence records in this source candidate; no real exact-workload restore, production recoverability, production failover, or Stable acceptance is established. |
| FR-005 | Complete live GoreeCloud Identity, Privacy Shield, and Wardveil authority-provider integrations without Everkeep minting or substituting their authority. | Critical | Planned / integration evidence pending. |
| FR-006 | Establish accepted production GoreeCloud Monitoring ingestion and GoreeCloud Notify delivery evidence for minimized continuity signals. | High | Planned / production acceptance pending. |
| FR-007 | Advance controlled production recovery, failover, and rollback only with execution-time revalidation of approval, target, dependency, key-material, privacy, security, rollback, and operator gates. | Critical | Planned — current controlled execution remains simulation/non-production. |
| FR-008 | Migrate Continuity Center to the current GLAZE UI V1.3 / 1.3.0 Stable consumer target and prove exact-revision rendered, accessibility, resilience, rollback, and production acceptance without altering recovery truth. | High | Source compatibility reconciliation is validated in Draft PR #58 at exact head `29d3480885183b920dec74c22cccf52a26b60bb2` with Validate Everkeep run `34663715057` and Platform Contract run `34663715591` successful. The existing Continuity Center 2.1.0 presentation remains migration-required; current V1.3 rendered/application/production acceptance is pending. |
| FR-009 | Expand Continuity Center around evidence-backed Recovery Ready, At Risk, Recovery Blocked, Unknown, topology, assurance, drill, and rollback state without implying unsupported readiness. | High | Development foundation exists; production evidence pending. |
| FR-010 | Maintain portability, preservation, and succession/digital-legacy as first-class continuity domains with independent evidence and privacy gates. | Medium | Source foundations implemented; runtime/production acceptance incomplete. |
| FR-011 | Require application-specific Everkeep continuity acceptance for each protected GoreeCloud workload, including recovery objectives, restore tests, retention/privacy obligations, dependency/key-material needs, and exact production evidence. | High | Planned / per-workload acceptance incomplete. |
| FR-012 | Keep recovery evidence freshness, provenance, exact-revision identity, target identity, and non-transfer of external authority machine-verifiable at every consumer boundary. | Critical | Development — ongoing hardening. |

## Recovery-claim boundary

Everkeep must continue to distinguish **Backup Exists** from **Backup Exists + Integrity Verified + Policy Compliant + Recovery Tested + Recoverable**. Missing, stale, malformed, unavailable, or unverified evidence fails closed. Source implementation, simulation, drill execution, presentation state, or a successful backup must never be relabeled as verified recoverability without the required exact-resource and exact-environment evidence.

## Maintenance and synchronization

This roadmap and the corresponding Drive `FEATURE-ROADMAP.docx` must remain materially synchronized with one another and with the authoritative project or service record. Update both copies whenever feature scope, priority, dependency, implementation status, cancellation, supersession, recommendation, or verification state materially changes.

No feature may be represented as complete or Stable solely because it appears in this roadmap. Completion and lifecycle claims require the applicable authoritative implementation, validation, review, release, and production evidence.

## Reconciliation rule

At each material feature change, reconcile this roadmap against the current authoritative project record, repository implementation state, applicable platform-system requirements, and GoreeCloud Tasks Management. Missing obligations, stale status, duplicated work, roadmap drift, or undocumented disposition changes are defects to correct.
