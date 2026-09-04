#!/usr/bin/env python3
"""Fail closed on Continuity Center responsive/accessibility regressions."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "website" / "site-polish.css"


def main() -> int:
    errors: list[str] = []
    css = CSS.read_text(encoding="utf-8")

    required = {
        "public header remains in normal document flow": ".site-header{position:relative;inset-block-start:auto}",
        "tablet navigation deliberately recomposes": ".nav nav{grid-column:1/-1;grid-row:2;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));width:100%;gap:8px}",
        "navigation targets retain the 48px floor": ".nav nav a{width:100%;min-height:48px}",
        "phone navigation becomes one column": "@media(max-width:390px){body{min-inline-size:0}.nav nav{grid-template-columns:1fr}",
        "tablet cards recompose": ".card-grid.four{grid-template-columns:repeat(2,minmax(0,1fr))}",
        "phone cards collapse to one column": ".card-grid.six,.card-grid.four{grid-template-columns:1fr}",
        "recovery equation collapses to one column": ".equation{grid-template-columns:1fr}",
        "narrow actions become full width": ".actions .action{width:100%;justify-content:center}",
        "public anchors do not reserve sticky-header space": "html{scroll-padding-top:24px}",
        "reduced motion is supported": "@media(prefers-reduced-motion:reduce)",
        "reduced transparency is supported": "@media(prefers-reduced-transparency:reduce)",
        "increased contrast is supported": "@media(prefers-contrast:more)",
        "forced colors are supported": "@media(forced-colors:active)",
        "print fallback is supported": "@media print",
    }
    for label, marker in required.items():
        if marker not in css:
            errors.append(f"Missing responsive/accessibility contract: {label}")

    forbidden = {
        "horizontally scrolling navigation": "overflow-x:auto",
        "scroll-snap navigation": "scroll-snap-type",
        "sticky public header": ".site-header{position:sticky",
        "fixed public header": ".site-header{position:fixed",
    }
    for label, marker in forbidden.items():
        if marker in css:
            errors.append(f"Responsive layout regressed to {label}")

    if errors:
        print("Continuity Center responsive validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Continuity Center responsive layout validation passed: normal-flow header, deliberate two-column/one-column navigation, 48px targets, mobile card/equation recomposition, no horizontal nav scroll, and accessibility fallbacks are protected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
