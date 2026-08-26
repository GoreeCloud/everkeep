# Everkeep Live Acceptance

Live acceptance is the final evidence gate before an Everkeep environment may be described as operational. Configuration, successful CI, or reachable health endpoints are not sufficient by themselves.

## Required authoritative checks

1. **Everkeep readiness** — the deployed Everkeep revision reports ready and matches the revision being accepted.
2. **PostgreSQL migrations** — the target database is reachable and all required Everkeep migrations are applied.
3. **GoreeCloud Identity authenticated flow** — a real authenticated request succeeds with the expected permission context, and an unauthorized request is rejected.
4. **Privacy Shield deliberate denial** — a controlled operation that Privacy Shield denies must be rejected by Everkeep with no prohibited mutation committed.
5. **Wardveil Security deliberate denial** — a controlled recovery/security denial must block the operation and leave auditable evidence.
6. **GoreeCloud Mesh delivery and retry** — an event is delivered successfully; a forced transient failure remains pending/retryable and is not falsely acknowledged.
7. **Adapter cursor restart** — an adapter persists its cursor, restarts, resumes from the durable cursor, and does not silently duplicate or skip accepted resources.
8. **Durable runtime restart** — the service restarts while preserving durable resources, policy versions, recovery-point state, audit ordering, idempotency records, and pending outbox work.

Every required check must be both `status=pass` and `authoritative=true`. Missing, unknown, synthetic-only, or non-authoritative evidence causes `accepted=false`.

## Evidence handling

Run acceptance from the target environment or another explicitly authorized verifier with access to the deployed service and authoritative platform dependencies. Capture the deployed source revision, timestamps, request/result identifiers, migration state, event IDs, restart evidence, and relevant audit sequences. Never store passwords, tokens, private keys, database credentials, or raw secrets in acceptance evidence.

## Failure injection

Privacy Shield and Wardveil tests must use controlled test resources and policies. The goal is to prove Everkeep fails closed when the governing subsystem denies an action, not to weaken or bypass those systems.

Mesh retry testing must force a safe transient delivery failure and demonstrate that the outbox preserves the event until successful delivery. Adapter restart tests must verify cursor continuity across process replacement. Runtime restart tests must verify durable state rather than relying on process memory.

## Operational claim

An environment may only be marked accepted when the generated live-acceptance evidence has `accepted=true`. Staging acceptance does not imply production acceptance. Production requires its own independent evidence against the production environment.
