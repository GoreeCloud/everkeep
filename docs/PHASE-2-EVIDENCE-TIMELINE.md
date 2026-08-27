# Everkeep Phase 2 — Resource Evidence Timeline

The Resource Evidence Timeline gives Recovery Center and application integrations a deterministic history of protection, integrity, restore-test, policy, recovery, retention, dependency, key-material, preservation, portability, and succession evidence for one protected resource.

## Current evidence vs. historical evidence

Historical evidence is never rewritten merely because a newer observation exists. The timeline preserves earlier pass, fail, unknown, and informational observations while separately projecting the latest current evidence for each category.

A previous successful restore test therefore remains visible as history but cannot override a newer failed or stale restore-test observation.

## Normalization

Each timeline item includes an evidence identifier, category, observation time, normalized state, current/historical marker, human-readable summary, and non-secret evidence reference. Optional producer, recovery-point, and freshness metadata may also be projected.

Unknown categories are normalized to `other`. Unsupported producer states become `unknown`; they are never treated as success.

Records without a stable evidence identifier, evidence reference, summary, or observation time fail closed rather than entering the timeline as unattributed proof.

## Ordering

Items are ordered newest first using the evidence observation time, with stable evidence identifiers as a deterministic tie-breaker. Identical inputs therefore produce identical timeline ordering.

## Glaze UI boundary

Glaze UI may render timeline events, category filters, historical/current markers, summaries, and evidence details. State must remain understandable without relying on color alone. The UI may not infer a current pass from an older historical pass when the current category state is failed, unknown, or absent.

## Evidence boundary

The timeline is a projection over evidence; it is not an authority source. Producers remain responsible for the underlying facts, timestamps, freshness boundaries, and references. Malformed or incomplete observations fail closed and may not strengthen recovery readiness.
