# Everkeep Staging Verification

This runbook defines the evidence required before an Everkeep staging environment may be described as operational.

## Required runtime evidence

Everkeep staging is operational only when all required checks are authoritative and passing:

- Everkeep `/ready` responds successfully over HTTPS.
- PostgreSQL is reachable and the Everkeep migration table is readable.
- GoreeCloud Identity is configured and its health endpoint responds successfully.
- Privacy Shield is configured and its health endpoint responds successfully.
- Wardveil Security is configured and its health endpoint responds successfully.
- GoreeCloud Mesh is configured and its health endpoint responds successfully.
- The running source revision is captured in the resulting evidence artifact.

A missing endpoint, missing database driver, unavailable dependency, TLS failure, failed request, or unknown state prevents `operational: true`.

## Execution

Provide the staging runtime with:

- `EVERKEEP_BASE_URL`
- `EVERKEEP_POSTGRES_DSN`
- `EVERKEEP_IDENTITY_ENDPOINT`
- `EVERKEEP_PRIVACY_ENDPOINT`
- `EVERKEEP_WARDVEIL_ENDPOINT`
- `EVERKEEP_MESH_ENDPOINT`
- `EVERKEEP_SOURCE_REVISION`

Then execute:

```bash
python3 scripts/staging_verify.py > staging-evidence.json
```

Exit code `0` means every required check passed authoritatively. Exit code `2` means staging must remain non-operational.

## Evidence handling

The output must conform to `contracts/everkeep.staging-evidence.schema.json`. Evidence may be attached to a deployment record, release, CI artifact, or GoreeCloud operational record, but secrets, bearer tokens, and database credentials must never be copied into evidence.

## Additional deployment acceptance tests

Before promotion beyond staging, separately verify authenticated Everkeep requests through GoreeCloud Identity, a deliberate Privacy Shield denial, a deliberate Wardveil denial, successful and retried GoreeCloud Mesh publication, adapter cursor restart behavior, service restart with durable state preserved, recovery-point lifecycle persistence, and Recovery Center query behavior against the deployed database.

This runbook does not convert configuration into evidence. Staging remains unverified until the checks execute against the deployed environment.
