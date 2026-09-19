# Everkeep — Feature Roadmap

**Status:** Active roadmap control  
**As of:** 2026-09-19  
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
| FR-004 | Validate real restore operations in isolated environments and bind acceptance to the exact protected resource, deployed target revision, Everkeep source revision, recovery point, environment, evidence freshness, and verified restored state. | Critical | Development — restore-verification v1.2 source is integrated on authoritative main through PR #65 / `ba2f8cd478187a137edeea0a9826dacdc8e0e154`. Exact candidate `a39d4b56c037351d9ed6c38a03163af9fab444b0` passed Validate Everkeep run `35456548056` and isolated-restore v1.2 run `35456547944`; merged main passed post-merge runs `35456627139` and `35456627096`. Real exact-workload production restore evidence remains pending. |
| FR-005 | Complete live GoreeCloud Identity, Privacy Shield, and Wardveil authority-provider integrations without Everkeep minting or substituting their authority. | Critical | Planned / integration evidence pending. |
| FR-006 | Establish accepted production GoreeCloud Monitoring ingestion and GoreeCloud Notify delivery evidence for minimized continuity signals. | High | Planned / production acceptance pending. |
| FR-007 | Advance controlled production recovery, failover, and rollback only with execution-time revalidation of approval, target, dependency, key-material, privacy, security, rollback, and operator gates. | Critical | Planned — current controlled execution remains simulation/non-production. |
| FR-008 | Migrate Continuity Center to the current Stable Glaze UI 1.5.1 consumer target and prove exact-revision rendered, accessibility, resilience, rollback, and production acceptance without altering recovery truth. | High | Authoritative main now declares Platform Contract 0.4 and Stable Glaze UI 1.5.1 while remaining `applicable-migration-required`. The Continuity Center's historical repository-specific 2.1.0 presentation evidence is implementation history only; current 1.5.1 rendered/application/production acceptance remains pending. |
| FR-009 | Expand Continuity Center around evidence-backed Recovery Ready, At Risk, Recovery Blocked, Unknown, topology, assurance, drill, and rollback state without implying unsupported readiness. | High | Development foundation exists; production evidence pending. |
| FR-010 | Maintain portability, preservation, and succession/digital-legacy as first-class continuity domains with independent evidence and privacy gates. | Medium | Source foundations implemented; runtime/production acceptance incomplete. |
| FR-011 | Require application-specific Everkeep continuity acceptance for each protected GoreeCloud workload, including recovery objectives, restore tests, retention/privacy obligations, dependency/key-material needs, and exact production evidence. | High | Planned / per-workload acceptance incomplete. |
| FR-012 | Keep recovery evidence freshness, provenance, exact-revision identity, target identity, and non-transfer of external authority machine-verifiable at every consumer boundary. | Critical | Development — live-acceptance evidence v1.1 is integrated on authoritative main through PR #67 / `d55d6317e084de8732681721eaad073c6bb6e725`. Exact candidate `516cde3ce54d3d419514c699d7d37b48385233b9` passed Validate Everkeep run `35458567380`; merged main passed post-merge run `35458609637`. The gate binds required checks to provider, environment, exact revisions, unique evidence IDs, freshness, and check-specific proof while rejecting unsupported environments and extra checks. No real staging/production provider acceptance is established. |

## Current platform checkpoint

The live-acceptance implementation baseline is `d55d6317e084de8732681721eaad073c6bb6e725`. The recovery-verification implementation baseline remains `ba2f8cd478187a137edeea0a9826dacdc8e0e154`, whose post-merge Validate Everkeep run `35456627139` and isolated-restore v1.2 run `35456627096` succeeded. Live-acceptance evidence v1.1 was integrated through PR #67; exact candidate `516cde3ce54d3d419514c699d7d37b48385233b9` passed Validate Everkeep run `35458567380`, and that implementation-bearing merged revision passed post-merge run `35458609637`. The repository continues to use Platform Contract `0.4`, evaluates exactly nine Integral Platform Systems, treats GoreeCloud Sync as separately governed, requires Stable Glaze UI `1.5.1`, and keeps application-specific production acceptance blocked where real evidence is not established. This checkpoint is Development/source evidence only.

## Recovery-claim boundary

Everkeep must continue to distinguish **Backup Exists** from **Backup Exists + Integrity Verified + Policy Compliant + Recovery Tested + Recoverable**. Missing, stale, malformed, unavailable, or unverified evidence fails closed. Source implementation, simulation, drill execution, presentation state, or a successful backup must never be relabeled as verified recoverability without the required exact-resource and exact-environment evidence.

## Maintenance and synchronization

This roadmap and the corresponding Drive `FEATURE-ROADMAP.docx` must remain materially synchronized with one another and with the authoritative project or service record. Update both copies whenever feature scope, priority, dependency, implementation status, cancellation, supersession, recommendation, or verification state materially changes.

No feature may be represented as complete or Stable solely because it appears in this roadmap. Completion and lifecycle claims require the applicable authoritative implementation, validation, review, release, and production evidence.

## Reconciliation rule

At each material feature change, reconcile this roadmap against the current authoritative project record, repository implementation state, applicable platform-system requirements, and GoreeCloud Tasks Management. Missing obligations, stale status, duplicated work, roadmap drift, or undocumented disposition changes are defects to correct.
