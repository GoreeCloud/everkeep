# GoreeCloud Continuity Security

GoreeCloud Continuity is an evidence and presentation boundary, not a credential store or unrestricted diagnostics channel.

## Sensitive-information rules

Continuity records, contracts, examples, fixtures, logs, screenshots, CI artifacts, and documentation must not contain reusable secrets or unnecessary personal information.

Do not include:

- passwords,
- API keys,
- access tokens,
- private keys,
- recovery codes,
- encryption keys,
- session material,
- setup keys,
- unrestricted backup credentials,
- raw secret-bearing environment files,
- unnecessary personal or family data.

Evidence should use identifiers, timestamps, normalized status, non-secret checksums, bounded metadata, and references to authoritative systems rather than copying sensitive source material.

## Trust boundary

A Continuity consumer must not treat producer-provided text as trusted executable content. Inputs should be schema-validated, bounded, and escaped for the target presentation environment.

A producer failure, timeout, malformed response, or authentication failure must not become `ready`.

## Remediation boundary

Continuity integrations are read-only by default. A status presentation must not silently acquire permission to restore backups, delete recovery points, alter retention, rotate credentials, modify storage, or change application data.

Any future write or remediation action must remain owned, authorized, and audited by the authoritative technical system.

## Reporting vulnerabilities

Do not disclose exploitable GoreeCloud infrastructure details, credentials, private endpoints, private user data, or active secret material in public issues or repository content. Use an approved private security-reporting path for sensitive findings.
