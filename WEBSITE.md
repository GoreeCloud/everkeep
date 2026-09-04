# Everkeep website

The public Everkeep Continuity Center is built from this repository for `https://everkeep.goreecloud.com/`.

## Cloudflare Pages configuration

- Production branch: `main`
- Framework preset: `None`
- Build command: `python scripts/build_public_site.py`
- Build output directory: `dist`
- Root directory: blank

`dist/` is generated publication output, not a separate product, continuity, branding, or design authority.

## Current presentation contract

The current platform presentation baseline is **GLAZE UI V1.1 / 1.1.0**. The Continuity Center source candidate activates `data-glaze-version="1.1"`, loads the official `css/glaze-v1.1.0.css` entrypoint from a built local artifact, and supports the V1.1 Light, Dark, and Deep Dark appearance contract.

`website/glaze.lock.json` pins the immutable `v1.1.0` release commit `15cc76d2bcd4065552dc31c77145b63f34d9e7b2`, release tree, entrypoint, and all 13 Git blob identities in that published web source graph. The build retrieves only those exact files, verifies each Git blob identity, validates the complete transitive local CSS import closure, and only then publishes them under `dist/assets/glaze/`. The browser artifact has no runtime dependency on GitHub or another UI CDN.

### Current upstream blocker

The immutable `v1.1.0` graph is currently known to contain a stale import from `css/glaze-v1.components.css` to nonexistent `./glaze-v1.candidate.css`. The required inherited foundation already exists as `css/glaze-v1.foundation.css`, so Everkeep must not recreate or locally patch a competing Candidate foundation.

The canonical Glaze UI repository has a validated **1.1.1 Release Candidate preparation** that removes the stale import and adds fail-closed import-closure validation, but 1.1.1 has not yet been promoted and published as an immutable Stable release. Everkeep therefore remains blocked from claiming current Glaze acceptance. The Continuity Center build deliberately fails closed on the broken 1.1.0 closure until a corrected immutable Stable release exists, this consumer is explicitly re-pinned, and applicable exact-revision validation is repeated.

Durable continuity, recovery, assurance, policy, evidence, and state content remains on solid surfaces. Soft Glaze is bounded to navigation chrome. Glaze UI is presentation authority only and cannot create a backup, verify integrity, prove a restore, authorize failover, or upgrade Everkeep continuity state.

## Visual identity

The approved Everkeep identity is **Keystone 04**. The authoritative branding source is `GoreeCloud/goreecloud-branding-assets` at `systems/everkeep/everkeep.svg`. This repository's `assets/everkeep.svg` is a synchronized derivative and is the only Everkeep identity input copied into the public artifact.

The public site must not redraw, reinterpret, or replace Keystone 04 locally. Branding approval is separate from continuity or recovery acceptance.

## Content and evidence boundary

Public continuity and recovery claims must remain evidence-gated and consistent with Everkeep contracts and accepted runtime evidence. A backup, snapshot, replica, export, documented plan, successful source validation, website build, or deployment is not equivalent to proven recoverability.

Fast-changing implementation and production-acceptance details belong in authoritative Everkeep status, evidence, deployment, and acceptance records. Static public copy should describe durable product capabilities and authority boundaries conservatively rather than embed claims that may become stale.

## Responsive and accessibility requirements

The Continuity Center intentionally recomposes for desktop, tablet, and phone layouts. Mobile navigation must not rely on horizontal scrolling. Navigation targets preserve the 48 px Glaze floor, with the V1.1 56 px Touch Assistance contract available where enabled.

The site preserves visible focus, text reflow, reduced motion, reduced transparency, increased contrast, forced colors, safe narrow-width behavior, and print fallbacks. Responsive source checks and browser geometry checks remain release gates.

## Validation

The repository validation workflow:

- checks out and verifies the exact candidate revision;
- validates Everkeep continuity and identity contracts;
- validates responsive/accessibility rules;
- fetches the immutable Glaze source graph and verifies all locked Git blob identities;
- recursively validates CSS import closure before publishing any built artifact;
- verifies local publication files and canonical Keystone 04 bytes;
- rejects superseded active Glaze 2.1 publication inputs; and
- exercises the built page in Chrome at desktop, tablet, and phone widths only after the dependency graph is valid.

## Acceptance boundary

Source validation, a successful build, a preview, or a pull request does not establish rendered production acceptance, deployed-byte verification, recovery readiness, production failover authorization, clean-environment recovery, live integration acceptance, or overall Everkeep Stable eligibility.

At the current checkpoint, the upstream Glaze import-closure defect intentionally blocks the Continuity Center publication gate. A corrected immutable Stable Glaze release must be published and Everkeep must be re-pinned and revalidated before the website can advance beyond this blocked Development candidate. The live `everkeep.goreecloud.com` deployment must also be independently verified before website publication acceptance is claimed.
