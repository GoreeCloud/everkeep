# Everkeep Phase 2 — Scheduled Restore Testing

Restore testing is the practical proof that protected data can be recovered. Phase 2 makes restore-test scheduling policy-derived and evidence-gated rather than treating successful backup jobs as sufficient assurance.

## Policy-derived schedule

The schedule derives from `verification.restoreTestIntervalSeconds` in the effective Everkeep Protection Policy. The last successful restore-test timestamp is the preferred scheduling anchor; when no successful test exists, the protected resource creation time is used when available.

The deterministic temporal states are:

- `scheduled` — the next policy deadline is still in the future.
- `due` — the policy deadline has arrived.
- `overdue` — an additional full policy interval has elapsed beyond the deadline without successful current evidence.
- `unknown` — no valid scheduling anchor exists.

Unknown is not treated as current assurance.

## Dispatch gates

A due or overdue schedule is not automatically executable. Dispatch requires explicit current evidence for:

- GoreeCloud Identity authorization;
- Privacy Shield authorization;
- Wardveil Security clearance;
- an eligible recovery point;
- Recovery Sandbox availability when the effective policy requires a sandbox.

A failed required gate produces `blocked`. Missing or malformed gate evidence produces `unknown`. Only a due/overdue schedule with `dispatchState: ready` becomes dispatchable.

## Recovery Sandbox and source preservation

Restore tests are non-destructive by design. The schedule contract records `sourceMutationAllowed: false`. When a policy requires the Recovery Sandbox, restore-test dispatch remains unavailable until sandbox availability is explicitly proven.

The runtime test should restore into an isolated target, verify integrity and application behavior, apply Wardveil malware/tamper checks as required, and capture attributable evidence for the tested recovery point and deployed revision. It must not overwrite source data merely to prove recoverability.

## Evidence production

A completed test should emit new restore-verification evidence with start/end times, recovery-point identity, environment, isolation state, integrity result, restored-state verification result, and measured RTO where applicable. Failed tests remain evidence and must reduce readiness until corrected by newer valid evidence.

## Evidence boundary

This phase implements deterministic scheduling and dispatch eligibility. It does not claim that a scheduler worker, Recovery Sandbox, restore adapter, or test environment is deployed until runtime evidence proves those capabilities.
