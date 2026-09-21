# Everkeep — Repository Notes

## Current state

Everkeep is in Development. Authoritative source is the `GoreeCloud/everkeep` repository. Source validation, simulations, and repository documentation do not establish production recovery readiness.

## Current implementation baselines

The repository contains the integrated restore-verification v1.2 and live-acceptance v1.1 foundations documented in `FEATURE-ROADMAP.md` and the canonical GoreeCloud Tasks Management record.

## Important boundaries

- Backup existence is not recoverability.
- Simulation and controlled drills do not grant production-effect authority.
- External platform authority must remain with the owning GoreeCloud system.
- Missing or stale required evidence fails closed.
- GoreeCloud Sync is separately governed and is not a substitute for backup.
- The current shared Glaze UI consumer target is 1.6.0; repository-specific Continuity Center migration/acceptance remains open.

## Maintenance

Keep this file factual and repository-safe. Do not store passwords, tokens, private keys, recovery codes, private backup contents, or other reusable secrets here.
