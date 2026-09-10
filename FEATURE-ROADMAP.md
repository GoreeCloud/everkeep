# Everkeep Feature Roadmap

**Status:** Active roadmap control  
**As of:** September 10, 2026  
**Authoritative project record:** `Project Specification — Everkeep`  
**Repository:** `GoreeCloud/goreecloud-everkeep`  
**Drive mirror:** `GoreeCloud/Feature Roadmap/Everkeep/FEATURE-ROADMAP.docx`

## Purpose

This file is the repository-side feature roadmap control required by GoreeCloud planned-feature governance. It tracks current Everkeep feature obligations without replacing the authoritative project specification, verified implementation evidence, GoreeCloud Tasks Management, or release/production gates.

Everkeep must never convert backup existence, source implementation, contract validity, or simulation results into verified recoverability. Missing, stale, malformed, unavailable, mismatched, or unverified evidence fails closed.

## Roadmap

| ID | Feature / obligation | Priority | Current state |
| --- | --- | --- | --- |
| FR-001 | Reconcile every current planned or recommended Everkeep feature from the authoritative project record and verified repository state into both roadmap copies. | High | Ongoing control |
| FR-002 | Move actionable feature obligations into GoreeCloud Tasks Management when required, preserving priority, dependencies, and lifecycle disposition. | High | Ongoing control |
| FR-003 | Do not mark features implemented, complete, cancelled, superseded, production-ready, or Stable without authoritative evidence and synchronized repository/Drive roadmap updates. | High | Ongoing control |
| FR-004 | Validate real restore operations in isolated environments and bind acceptance to the exact protected resource, deployed target revision, Everkeep source revision, recovery point, environment, evidence freshness, and verified restored state. | Critical | Development — source evidence gate exists; exact-revision hardening in PR #57; production restore evidence pending |
| FR-005 | Complete live GoreeCloud Identity, Privacy Shield, and Wardveil authority-provider integrations without Everkeep minting or substituting their authority. | Critical | Planned / integration evidence pending |
| FR-006 | Establish accepted production GoreeCloud Monitoring ingestion and GoreeCloud Notify delivery evidence for minimized continuity signals. | High | Planned / production acceptance pending |
| FR-007 | Advance controlled production recovery, failover, and rollback only with execution-time revalidation of approval, target, dependency, key-material, privacy, security, rollback, and operator gates. | Critical | Planned — current controlled execution remains simulation/non-production |
| FR-008 | Migrate Continuity Center to the current GLAZE UI V1.3 / `1.3.0` Stable consumer target and prove exact-revision rendered, accessibility, resilience, rollback, and production acceptance without altering recovery truth. | High | Development / migration required |
| FR-009 | Expand Continuity Center around evidence-backed Recovery Ready, At Risk, Recovery Blocked, Unknown, topology, assurance, drill, and rollback state without implying unsupported readiness. | High | Development foundation exists; production evidence pending |
| FR-010 | Maintain portability, preservation, and succession/digital-legacy as first-class continuity domains with independent evidence and privacy gates. | Medium | Source foundations implemented; runtime/production acceptance incomplete |
| FR-011 | Require application-specific Everkeep continuity acceptance for each protected GoreeCloud workload, including recovery objectives, restore tests, retention/privacy obligations, dependency/key-material needs, and exact production evidence. | High | Planned / per-workload acceptance incomplete |
| FR-012 | Keep recovery evidence freshness, provenance, exact-revision identity, target identity, and non-transfer of external authority machine-verifiable at every consumer boundary. | Critical | Development — ongoing hardening |

## Maintenance and synchronization

This roadmap and the Drive-side `FEATURE-ROADMAP.docx` must remain materially synchronized with one another and with the authoritative project record. Update both copies whenever feature scope, priority, dependency, implementation status, cancellation, supersession, recommendation, or verification state materially changes.

No feature may be represented as complete or Stable solely because it appears here. At each material feature change, reconcile this roadmap against the authoritative Everkeep specification, current repository implementation, applicable Integral Platform System requirements, and GoreeCloud Tasks Management.
