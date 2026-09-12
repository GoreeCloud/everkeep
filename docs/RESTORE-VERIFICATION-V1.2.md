# Everkeep Restore Verification v1.2 — Exact Isolated Restore Evidence

**Roadmap:** FR-004  
**Lifecycle:** Development source candidate

## Recovery truth boundary

**Backup Exists is not Recoverable.** Version 1.2 is an additive restore-verification contract for evidence that a specific recovery point was actually restored into a specific isolated environment and that the restored workload was checked successfully. It requires evidence from a **real isolated restore**, not a simulation or presentation-only exercise.

The older v1.0 and v1.1 contracts remain available for pinned consumers. V1.2 does not silently reinterpret their evidence.

## Exact identity binding

A passing v1.2 record binds:

- the exact verification-attempt identifier expected by the consumer;
- the exact isolated environment identifier;
- the exact recovery point identifier;
- the exact recovery point artifact digest;
- the exact Everkeep source revision and tree;
- the exact protected resource identifier;
- the exact deployed target revision;
- the recovery point production time;
- restore start, completion, capture, and freshness times;
- integrity verification and restored-state verification; and
- one or more workload-specific checks with bounded evidence references.

The verification-attempt binding prevents evidence from another otherwise-compatible restore verification from being replayed as the requested verification. The execution mode is fixed to `real_isolated_restore`. A simulation cannot satisfy this contract. Source mutation and production promotion are both fixed to false.

## Fail-closed consumption

A consumer must reject v1.2 evidence when the verification attempt, environment, protected resource, target revision, Everkeep revision/tree, recovery-point identity, artifact digest, workload checks, timestamps, freshness, integrity, restored-state verification, or authority-transfer boundary does not match the expected scope. Missing or failed workload checks remain non-recoverable.

Consumers may shorten evidence freshness, but they must not extend Everkeep's evidence validity.

## Authority boundary

Everkeep remains the recovery and restore-verification authority. This evidence records what was observed during a bounded restore exercise; it does not grant Privacy Shield, Wardveil, Identity, Manager, Mesh, or the restored workload any additional authority.

A passing source contract or validation run does not prove that any real production workload has been restored. A real record must be generated from an actual isolated restore and separately accepted for the exact verification attempt, workload, recovery point, artifact, and environment.

This contract does not authorize production failover, production promotion, traffic switching, destructive recovery actions, release approval, or Stable qualification.
