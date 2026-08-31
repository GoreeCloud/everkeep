# Everkeep Live Acceptance

Live acceptance is the final evidence gate before an Everkeep environment may be described as operational. Configuration, successful CI, reachable health endpoints, or synthetic `verified=true` markers are not sufficient by themselves.

## Required authoritative checks

1. **Everkeep readiness** — the deployed Everkeep revision reports ready and matches the revision being accepted.
2. **PostgreSQL migrations** — the target database is reachable and all required Everkeep migrations are applied.
3. **GoreeCloud Identity authenticated flow** — a real authenticated request succeeds with the expected Everkeep service identity and permission context, and an unauthorized request is rejected.
4. **Privacy Shield deliberate denial** — a controlled operation that Privacy Shield denies must be rejected by Everkeep with no prohibited mutation committed.
5. **Wardveil Security deliberate denial** — a controlled recovery/security denial must block the operation, commit no prohibited mutation, and leave auditable evidence.
6. **GoreeCloud Mesh delivery and retry** — an event is delivered successfully; a forced transient failure remains pending/retryable and is not falsely acknowledged.
7. **Adapter cursor restart** — an adapter persists its cursor, restarts, resumes from the durable cursor, and does not silently duplicate or skip accepted resources.
8. **Durable runtime restart** — the service restarts while preserving durable resources, policy versions, recovery-point state, audit ordering, idempotency records, and pending outbox work.

Every required check must be both `status=pass` and `authoritative=true`. Missing, unknown, synthetic-only, duplicate, wrong-provider, wrong-environment, wrong-revision, stale, future-skewed, replayed, or otherwise unbound evidence causes `accepted=false`.

## Evidence provenance

Every acceptance check must carry evidence bound to:

- the expected authority/provider for that check;
- the exact target environment;
- the exact Everkeep revision being accepted;
- a unique evidence identifier;
- a timezone-aware observation timestamp.

The eight required checks must use eight distinct evidence identifiers. Reusing one evidence identifier for multiple required checks is treated as replay/aliasing and fails the acceptance decision even if each check otherwise contains plausible fields.

Authoritative passing evidence must also be fresh relative to the single acceptance capture time. The current evaluator accepts observations no older than **one hour** and allows at most **60 seconds** of future clock skew. Evidence older than that window or farther in the future fails closed. These bounds are evaluator policy while the serialized evidence document remains compatible with schema 1.1.

External authority checks for GoreeCloud Identity, Privacy Shield, Wardveil Security, and GoreeCloud Mesh must also identify the provider revision that produced or governed the observed result. Provider revision is evidence provenance, not a version-comparison shortcut: each provider remains responsible for its own deployment and acceptance status.

Check-specific facts are also required. Examples include authenticated success plus unauthorized rejection for Identity, denial plus no committed mutation for Privacy Shield and Wardveil, transient failure plus preserved retry state for Mesh, and restart plus durable-state preservation for Everkeep runtime checks. Merely setting `authoritative=true` does not make arbitrary evidence authoritative.

## Evidence handling

Run acceptance from the target environment or another explicitly authorized verifier with access to the deployed service and authoritative platform dependencies. Capture deployed source revisions, timestamps, request/result identifiers, migration state, event IDs, restart evidence, relevant audit sequences, and external provider revisions. Never store passwords, tokens, private keys, database credentials, or raw secrets in acceptance evidence.

All checks in one decision should be collected closely enough in time to remain inside the freshness window. If a long-running acceptance exercise exceeds that window, recollect expired checks rather than extending their timestamps or treating old evidence as current.

## Failure injection

Privacy Shield and Wardveil tests must use controlled test resources and policies. The goal is to prove Everkeep fails closed when the governing subsystem denies an action, not to weaken or bypass those systems.

Mesh retry testing must force a safe transient delivery failure and demonstrate that the outbox preserves the event until successful delivery. Adapter restart tests must verify cursor continuity across process replacement. Runtime restart tests must verify durable state rather than relying on process memory.

## Operational claim

An environment may only be marked accepted when the generated live-acceptance evidence has `accepted=true` under the current acceptance schema and validator. Staging acceptance does not imply production acceptance. Production requires its own independent evidence against the production environment.
