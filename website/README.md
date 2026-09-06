# Everkeep Continuity Center Public Website

> **Static website source authority:** the canonical source for the public Continuity Center is now `GoreeCloud/goreecloud-static-websites/sites/everkeep`.

This `website/` directory and the related public-site build inputs in this repository are protected transitional deployment copies while the production Pages deployment still uses the pre-consolidation source. Future authoritative public-site source changes belong in the centralized static-websites repository.

The public destination is `https://everkeep.goreecloud.com`.

## Centralized package

The central package reproduces the bounded public website source and only the site-specific inputs required to build and validate it, including the approved Everkeep mark. Everkeep runtime, continuity, recovery, preservation, evidence, governance, contracts, and service implementation remain authoritative in this repository and were not transferred to the public static-site repository.

Generated deployment output is not canonical source authority.

## Current legacy deployment boundary

While the legacy deployment remains active, this repository retains the website subtree and its public-site build/validation tooling so the currently verified deployment can continue to build and roll back safely.

The existing public build uses `scripts/build_public_site.py` to create the isolated publication artifact. The central manifest intentionally continues to record `deployment_state: legacy-source` until authenticated Cloudflare Pages configuration is changed to the centralized package and the exact resulting production deployment is verified.

Do not delete this website subtree, the approved public identity input, or required legacy build resources before that cutover and verification are complete.

## Acceptance boundary

Central source migration has reached `validated-in-central-repo`, but that state does not prove that Cloudflare Pages is using the centralized repository and does not create or upgrade Everkeep runtime, recovery, continuity, preservation, or production acceptance.

After the Pages repository/root/build cutover, the deployed custom domain must be verified against the accepted central revision before this legacy public-site copy can be retired. Everkeep's substantive platform authority remains in `GoreeCloud/goreecloud-everkeep` throughout and after the website-source migration.
