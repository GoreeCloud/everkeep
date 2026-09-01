#!/usr/bin/env python3
"""Fail closed on Continuity Center responsive/public-document layout regressions."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "website" / "site-polish.css"


def main() -> int:
    errors: list[str] = []
    css = CSS.read_text(encoding="utf-8")

    required = {
        "public header remains in normal document flow": ".site-header{position:relative;inset-block-start:auto}",
        "tablet navigation becomes three columns": "@media(max-width:850px){.nav{align-items:flex-start;flex-direction:column;gap:12px;padding:14px 0}.nav nav{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))",
        "phone navigation becomes two columns": "@media(max-width:580px){.wrap{width:min(calc(100% - 1.5rem),1180px)}.nav nav{grid-template-columns:repeat(2,minmax(0,1fr))",
        "exact-width phone canvas can fit inside the usable viewport": "@media(max-width:380px){body.glaze-canvas{min-inline-size:0}",
        "narrow navigation becomes one column": ".nav nav{grid-template-columns:1fr}",
        "phone content cards collapse to one column": ".card-grid.six,.card-grid.four,.card-grid.three{grid-template-columns:1fr}",
        "recovery equation collapses to one column": ".equation{grid-template-columns:1fr}",
        "narrow action buttons become full width": ".actions .button{width:100%}",
        "public anchors do not reserve sticky-header space": "html{scroll-padding-top:24px}",
    }
    for label, marker in required.items():
        if marker not in css:
            errors.append(f"Missing responsive contract: {label}")

    sticky = css.rfind(".site-header{position:sticky")
    normal_flow = css.rfind(".site-header{position:relative;inset-block-start:auto}")
    if sticky >= 0 and normal_flow <= sticky:
        errors.append("Final Continuity Center cascade does not keep public navigation in normal document flow")

    if errors:
        print("Continuity Center responsive validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Continuity Center responsive layout validation passed: normal-flow navigation, 3/2/1-column nav, exact-width 320px fit, single-column phone cards/equation, and full-width narrow actions are protected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
