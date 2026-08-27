# Everkeep Phase 2 — Succession and Digital Legacy

Everkeep Succession defines evidence-gated digital-legacy policy and activation eligibility for protected GoreeCloud resources. It is designed to preserve owner intent without allowing a missing signal, inactive policy, unverified successor, or security/privacy uncertainty to become transfer or destruction authority.

## Succession policy

A policy identifies the owner through a GoreeCloud Identity subject reference and contains explicit resource rules. A rule can request one of these dispositions:

- `transfer`
- `archive`
- `delete`
- `retain`
- `no-action`

Transfer rules reference successor identities, not raw contact information or reusable credentials. A transfer rule requires at least one successor reference.

Policies move through `draft`, `active`, `suspended`, and `revoked` states. Only an active policy can ever become activation-eligible.

## Activation signals

The policy may require owner-status confirmation, a trusted-contact quorum, legal authority, or an authorized manual emergency signal. Everkeep also imposes mandatory gates that a policy cannot weaken:

- Privacy Shield authorization;
- Wardveil Security clearance;
- verified successor evidence for any transfer disposition;
- explicit destruction authorization for any delete disposition;
- trusted-contact-quorum evidence when the policy configures a non-zero quorum.

GoreeCloud Identity remains authoritative for owner identity, successor verification, trusted contacts, authentication, and quorum claims. Privacy Shield remains authoritative for transfer, retention, disclosure, and deletion authority. Wardveil Security remains authoritative for security blocks and suspicious activation conditions.

## Waiting period

Activation evaluation requires an attributable activation event and applies the configured waiting period before eligibility can be reached. If the waiting period has not elapsed, the decision is blocked even when all external signals pass.

A missing activation event produces an inactive decision rather than assuming that an owner-status condition occurred.

## Fail-closed states

- A failed signal produces `blocked`.
- Missing or malformed required signal evidence produces `unknown`.
- Draft or suspended policy state produces `inactive`.
- Revocation produces `revoked`.
- Only all required passing signals after the waiting period produce `eligible`.

## Eligibility is not execution

The succession decision contract explicitly records `executionAuthorized: false`. Everkeep's evaluator determines only whether the policy is currently eligible to advance to a separately authorized execution workflow. It does not execute a transfer, archive operation, or deletion.

A later execution layer must re-check current Identity, Privacy Shield, Wardveil, resource-integrity, successor, retention, legal-hold, and destructive-action evidence at execution time. Eligibility evidence must not become indefinite authority.

## Evidence boundary

This phase defines policy structure and deterministic activation eligibility. It does not claim that mortality/inactivity detection, legal verification, trusted-contact workflows, successor onboarding, transfer delivery, or authorized destruction are deployed until their authoritative systems produce runtime evidence.
