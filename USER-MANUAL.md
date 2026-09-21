# Everkeep — User Manual

## Current audience

Everkeep is currently in Development. This manual describes the current repository and evidence model for developers and administrators. It is not a claim that production recovery automation is available for every GoreeCloud workload.

## Understanding Everkeep status

Everkeep uses evidence-backed continuity states:

- **ready** — all required evidence for the represented scope is current and verified;
- **attention** — continuity exists but a non-critical condition needs action;
- **degraded** — a required capability is impaired or failed;
- **unknown** — required evidence is missing, stale, unavailable, conflicting, incomplete, or unverified;
- **not_applicable** — the dimension genuinely does not apply to the explicit scope.

A successful backup alone does not mean a resource is recoverable.

## Recovery workflows

Current source supports planning, dry-run and isolated recovery concepts, restore-test scheduling, recovery topology, failover governance, simulation-only controlled drills, and rollback assurance. Production-effect recovery remains separately authorization- and evidence-gated.

Before relying on a recovery result, verify the protected resource, recovery point, exact revision, target environment, integrity checks, service checks, Privacy Shield and Wardveil requirements, dependencies, key material, and freshness evidence applicable to that scope.

## Safety

Do not place reusable passwords, tokens, private keys, recovery codes, or secret values in ordinary Everkeep evidence. Do not treat approval records or simulation artifacts as bearer execution credentials.

## More information

See `README.md`, `CONTINUITY.md`, `STATUS.md`, `ADOPTION.md`, `SECURITY.md`, and `FEATURE-ROADMAP.md` for the current Development contracts and boundaries.
