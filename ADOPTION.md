# Everkeep Adoption

A GoreeCloud application or service must not claim Everkeep integration based on branding alone.

## Minimum adoption requirements

An integration must define:

1. The continuity dimensions it represents.
2. The authoritative producer for each represented value.
3. The scope of each record.
4. How freshness and staleness are determined.
5. How unknown or unavailable evidence is handled.
6. Which evidence is required before `ready` may be asserted.
7. How sensitive information is excluded from shared evidence.
8. How the integration behaves when the producer is unreachable or returns invalid data.
9. How continuity status is presented accessibly through Glaze UI.
10. How the integration is tested and validated at an exact source revision.

## Required behavioral tests

At minimum, an adopting project should test:

- current verified evidence producing the intended state,
- stale evidence becoming `unknown` or a stricter non-ready state,
- missing required evidence blocking `ready`,
- malformed evidence failing closed,
- an unavailable producer not becoming a passing state,
- a failed restore or recovery validation producing a non-ready state,
- sensitive fields being rejected or excluded,
- summary state never being more favorable than its required child evidence.

## Backup integrations

A backup integration should distinguish at least:

- backup configured,
- backup execution succeeded,
- backup artifact exists,
- artifact integrity verified,
- restore tested,
- last restore-test time,
- restore target or test environment,
- known recovery limitations.

The presence of a backup is not equivalent to a verified restore.

## Application portability integrations

An application that reports portability should distinguish among:

- export capability exists,
- export completed,
- exported data validated,
- import capability exists,
- clean-target re-import succeeded,
- metadata/provenance preservation validated,
- unsupported or lossy fields documented.

## Succession integrations

Succession or digital-legacy readiness should be reported only when the represented scope has explicit custody and recovery documentation appropriate to that information. Reusable credentials, recovery codes, private keys, or secret values must not be embedded in Everkeep evidence.

## Acceptance

A project may describe itself as **Everkeep-integrated** only after its declared integration requirements and fail-closed tests pass. A project may describe a specific scope as **Everkeep ready** only when the current required continuity evidence for that scope supports the `ready` state.
