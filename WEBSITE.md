# Everkeep website

The public Everkeep website is built from this repository for `https://everkeep.goreecloud.com/`.

Cloudflare Pages configuration:

- Production branch: `main`
- Framework preset: `None`
- Build command: `python scripts/build_public_site.py`
- Build output directory: `dist`
- Root directory: blank

The site is intentionally origin-local. The canonical Everkeep identity is copied from `assets/everkeep.svg` into the isolated public artifact during the build. Public resilience and recovery claims must remain evidence-gated and consistent with the Everkeep contracts and accepted runtime state.
