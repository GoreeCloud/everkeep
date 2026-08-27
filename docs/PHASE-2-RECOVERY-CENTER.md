# Everkeep Phase 2 — Recovery Center Core

Phase 2 turns Everkeep's Phase 1 evidence contracts into an operational Recovery Center model. The Recovery Center is not a decorative dashboard: every displayed state and action must be derived from current protection, verification, retention, authorization, dependency, key-readiness, preservation, portability, and recovery evidence.

## Scope in this slice

- Fleet-level protection and recovery-readiness summary.
- Protected vs. unprotected resource counts.
- Recovery Ready, At Risk, Recovery Blocked, and Unknown counts.
- Assurance coverage for integrity verification, restore testing, and policy compliance.
- Deterministic blocker aggregation and severity ordering.
- Evidence-authorized recommended actions.
- Fail-closed recovery-action exposure.
- Recovery-plan and isolated-sandbox entry points when current evidence permits them.
- Preservation-capsule and portability-export entry points when their own authority evidence permits them.
- Stable ordering so identical inputs produce identical projections.

## Recovery action rule

The Recovery Center may suggest verification, restore testing, policy inspection, key-readiness inspection, dependency inspection, protection enrollment, recovery planning, preservation, or export only when the corresponding evidence supports that recommendation.

`restore-resource` is stricter. It may only be exposed when the resource is explicitly `Recovery Ready` and current evidence says `recoveryEligible: true`. The Recovery Center must not infer restore eligibility from backup existence alone.

Recovery planning and sandbox rehearsal are non-destructive entry points. They do not weaken the later authorization boundary: an execution must still pass the Recovery Orchestrator's identity, privacy, security, dependency, key-material, recovery-point, and evidence gates before any real restoration can begin.

## Assurance coverage

The summary separately counts explicit pass, fail, and unknown states for:

- current integrity verification;
- current restore-test evidence;
- current policy compliance.

Unknown is deliberately visible. Missing evidence is not converted into failure or success, and it never contributes to a stronger readiness claim.

## Blocker priority

Blockers are sorted first by severity (`critical`, `high`, `medium`, `low`), then by affected-resource count, then by stable blocker code. This makes Recovery Center prioritization deterministic and auditable.

## Glaze UI boundary

Glaze UI may render Recovery Center summaries, blocker groups, assurance coverage, readiness states, and actions from these projections. UI code must not manufacture stronger states than the underlying Everkeep evidence permits, and state must remain understandable without relying on color alone.

## Connected Phase 2 slices

1. Per-resource protection details and evidence timeline.
2. Recovery-point browsing and version navigation.
3. Recovery-plan creation and dry-run validation.
4. Isolated Recovery Sandbox orchestration.
5. Restore-test scheduling and results.
6. Application-specific Recovery Center adapters.
7. Recovery readiness trend/history projections.
8. Preservation Capsules with provenance and integrity manifests.
9. Portable export manifests with independent verification metadata.

The recovery-plan, execution-gating, preservation, and portability foundations are defined in the adjacent Phase 2 documents and contracts in this branch.

## Evidence boundary

This Phase 2 slice implements deterministic projections and contracts. It does not claim that a live Recovery Center UI, restore infrastructure, isolated sandbox, preservation archive, export pipeline, or production recovery execution environment is deployed until separate runtime evidence exists.
