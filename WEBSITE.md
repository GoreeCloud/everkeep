# Everkeep website

The public Everkeep website is built from this repository for `https://everkeep.goreecloud.com/`.

Cloudflare Pages configuration:

- Production branch: `main`
- Framework preset: `None`
- Build command: `python scripts/build_public_site.py`
- Build output directory: `dist`
- Root directory: blank

The site is intentionally origin-local. The canonical Everkeep identity is copied from `assets/everkeep.svg` into the isolated public artifact during the build. Public resilience and recovery claims must remain evidence-gated and consistent with the Everkeep contracts and accepted runtime state.

The active Continuity Center source remains on the historical **Glaze UI 2.1.0** baseline, promotion reference `c49113eb8b93c267613fdf1bbca1f814495acad7`; **Glaze UI 1.6.0** is the current shared Stable consumer target and migration remains pending. The public build allowlist publishes `website/glaze-ui-2.1.0.css` and does not publish the retained historical 1.5/2.0 stylesheet sources. Durable recovery, assurance, policy, and status content stays solid; controlled glaze is reserved for interaction and navigation.

Source/build alignment does not establish rendered production acceptance. The exact candidate must still satisfy repository validation and Cloudflare deployment acceptance before the live Continuity Center is used as proof of current Glaze UI 1.6.0 conformance.
