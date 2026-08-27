# Everkeep Phase 2 — Recovery Orchestration

The Recovery Orchestrator turns recovery intent into a deterministic, dependency-aware plan and evaluates whether an execution is currently authorized. It does not equate planning with permission to restore.

## Planning model

A recovery plan expands each requested target into its known recovery dependencies, orders dependencies before dependents, and emits explicit validation, staging, restore, and verification steps.

Supported plan modes:

- `dry-run` — validates ordering and gates without a recovery target.
- `sandbox` — targets an isolated Recovery Sandbox and requires explicit promotion before restored state can become production state.
- `restore` — plans a production-target recovery, while still preserving source data by default.

Every plan records `sourceMutationAllowed: false`. Recovery is additive and isolated by default; overwriting or deleting the source is not an implicit recovery step.

## Fail-closed execution gates

Every authorization boundary must fail closed. An execution is authorized only when every required gate explicitly passes:

- GoreeCloud Identity authorization;
- Privacy Shield authorization;
- Wardveil Security clearance;
- current recovery evidence;
- eligible recovery-point evidence;
- dependency readiness;
- key-material readiness.

Missing, failed, malformed, or unknown gate evidence blocks execution. A backup existing somewhere is not sufficient.

## Recovery Sandbox

Sandbox mode is the preferred path for high-value recovery and recovery testing. The sandbox should isolate restored state from production, support malware and integrity inspection, verify application behavior, and capture new recovery evidence. Successful sandbox recovery does not automatically promote data to production.

## Promotion boundary

Promotion is a separate authorized action. Before promotion, Everkeep must re-evaluate relevant identity, privacy, security, recovery-point, dependency, key-material, and restored-state evidence. A previously authorized sandbox execution cannot be treated as indefinite authority to promote later.

## Dependency ordering

Dependencies are restored and verified before dependents. The reference planner rejects dependency cycles and missing resource metadata rather than inventing an order. Application adapters may add more precise recovery ordering, but they may not weaken canonical Everkeep gates.

## Execution states

The execution contract supports:

`pending` → `authorized` → `running` → `verifying` → `completed`

and non-passing terminal or interrupted states:

`blocked`, `failed`, `cancelled`.

The reference code in this phase evaluates authorization and start eligibility only. It does not perform runtime restoration.

## Evidence boundary

This phase adds planning, authorization, dependency ordering, and execution-state contracts. It does not claim that Recovery Sandbox infrastructure, production restoration, promotion, storage providers, or application-specific restore adapters are deployed until authoritative runtime evidence proves those capabilities.
