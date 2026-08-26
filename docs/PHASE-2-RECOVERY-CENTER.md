# Everkeep Phase 2 — Recovery Center Core

Phase 2 turns Everkeep's Phase 1 evidence contracts into an operational Recovery Center model. The Recovery Center is not a decorative dashboard: every displayed state and action must be derived from current protection, verification, retention, authorization, dependency, key-readiness, and recovery evidence.

## Initial Phase 2 Scope

- Fleet-level protection and recovery-readiness summary.
- Protected vs. unprotected resource counts.
- Recovery Ready, At Risk, Recovery Blocked, and Unknown counts.
- Deterministic blocker aggregation and severity ordering.
- Evidence-authorized recommended actions.
- Fail-closed recovery-action exposure.
- Stable ordering so identical inputs produce identical projections.

## Recovery Action Rule

The Recovery Center may suggest verification, restore testing, policy inspection, key-readiness inspection, dependency inspection, or protection enrollment when the corresponding evidence supports that recommendation.

`restore-resource` is stricter. It may only be exposed when the resource is explicitly `Recovery Ready` and current evidence says `recoveryEligible: true`. The Recovery Center must not infer restore eligibility from backup existence alone.

## Blocker Priority

Blockers are sorted first by severity (`critical`, `high`, `medium`, `low`), then by affected-resource count, then by stable blocker code. This makes Recovery Center prioritization deterministic and auditable.

## Glaze UI Boundary

Glaze UI may render Recovery Center summaries, blocker groups, readiness states, and actions from these projections. UI code must not manufacture stronger states than the underlying Everkeep evidence permits.

## Phase 2 Next Slices

1. Per-resource protection details and evidence timeline.
2. Recovery-point browsing and version navigation.
3. Recovery-plan creation and dry-run validation.
4. Isolated Recovery Sandbox orchestration.
5. Restore-test scheduling and results.
6. Application-specific Recovery Center adapters.
7. Recovery readiness trend/history projections.

## Evidence Boundary

This Phase 2 slice implements deterministic projections and contracts. It does not claim that a live Recovery Center UI, restore infrastructure, isolated sandbox, or production recovery execution environment is deployed until separate runtime evidence exists.
