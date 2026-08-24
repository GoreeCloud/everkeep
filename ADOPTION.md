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

## Compact and wearable continuity presentation

Everkeep may present continuity status on compact, glanceable, wearable, notification, tile, complication, or similarly constrained Glaze UI surfaces, but the smaller surface must not turn incomplete recovery evidence into reassurance.

A constrained Everkeep surface must:

- preserve the normalized continuity state and never convert `unknown`, unavailable, stale, incomplete, or failed evidence into `ready`;
- distinguish a configured backup from verified restore readiness when that distinction is relevant to the represented scope;
- preserve freshness meaning, including the age of restore, export, integrity, or recovery validation when freshness affects the state;
- retain enough scope and authoritative-source context to identify what data, application, repository, or recovery path is represented, directly or through an accessible focused detail path;
- avoid exposing backup contents, recovery codes, private keys, credentials, personal records, detailed storage paths, or other sensitive recovery material on a glanceable surface;
- use a focused deep link to the authoritative recovery, backup, export, or continuity workflow when detailed action is required;
- follow the current Stable Glaze UI contract for the target form factor before the consuming application claims production conformance.

A compact Everkeep card is a presentation of existing continuity evidence. It is not proof that a restore will succeed, does not replace the authoritative backup or recovery system, and does not create continuity evidence of its own.

## Acceptance

A project may describe itself as **Everkeep-integrated** only after its declared integration requirements and fail-closed tests pass. A project may describe a specific scope as **Everkeep ready** only when the current required continuity evidence for that scope supports the `ready` state.

A project that adds a compact or wearable Everkeep surface must additionally validate state truthfulness, freshness visibility, scope/authority discoverability, sensitive-evidence exclusion, and non-ready fail-closed rendering at the exact intended source revision.
