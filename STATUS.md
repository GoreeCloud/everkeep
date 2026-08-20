# Everkeep Status Contract

## Purpose

This document defines the normalized continuity states used across Everkeep integrations. The contract exists so applications, dashboards, reports, APIs, and future clients present continuity evidence consistently without weakening the authority of the source system.

## States

### `ready`

All required continuity evidence for the represented scope is current, verified, and satisfies the applicable acceptance requirements.

A `ready` state must never be inferred from the mere presence of backups, replicas, exports, or documentation. Required evidence must prove the represented capability.

### `attention`

Continuity capability exists and required critical evidence remains valid, but one or more non-critical conditions require planned action.

Examples may include an approaching freshness deadline, a non-critical documentation gap, or a recommended additional recovery layer that is not required for the represented scope.

### `degraded`

A required continuity capability is materially impaired, incomplete, failed, or outside its accepted operating boundary.

Examples may include a failed restore test, unavailable recovery destination, broken export path, or loss of a required independent recovery layer.

### `unknown`

Required evidence is missing, stale, unavailable, incomplete, conflicting, or unverified.

`unknown` is not a passing state. Required `unknown` evidence blocks `ready`.

### `not_applicable`

The represented continuity dimension does not apply to the explicit scope. This state must be justified by scope, not used to hide missing evidence.

## Aggregation rule

An Everkeep summary must never be more favorable than the weakest required evidence in its represented scope.

For required evidence, the conservative ordering is:

`degraded` → `unknown` → `attention` → `ready`

`not_applicable` is excluded from aggregation only when non-applicability is explicitly valid for that dimension.

## Required record fields

A machine-readable continuity status record should identify:

- a stable record identifier,
- the authoritative producer,
- the represented scope,
- the continuity dimension,
- the normalized state,
- the observation or verification time,
- the freshness deadline or freshness policy,
- whether the evidence is required,
- the verification method,
- an evidence reference that does not contain secrets,
- any known limitation or reason for a non-ready state.

## Freshness

A status record must become non-ready when required evidence exceeds its defined freshness boundary. A stale required record resolves to `unknown` unless the authoritative source can prove a more specific non-passing state.

## Security and privacy

Everkeep status records must not contain reusable credentials, private keys, tokens, recovery codes, encryption secrets, unrestricted backup contents, personal data that is unnecessary for the continuity decision, or raw diagnostic material that creates avoidable exposure.

## Accessibility and Glaze UI

Everkeep state must be understandable without relying on color alone. Glaze UI integrations should pair state with text, accessible naming, and consistent iconography. Machine-readable state must remain the source for automation and aggregation.
