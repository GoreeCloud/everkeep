#!/usr/bin/env python3
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'
FILES={
    ROOT/'website'/'index.html': DIST/'index.html',
    ROOT/'website'/'style.css': DIST/'style.css',
    ROOT/'website'/'glaze-ui-2.1.0.css': DIST/'glaze-ui-2.1.0.css',
    ROOT/'website'/'site-polish.css': DIST/'site-polish.css',
    ROOT/'website'/'_headers': DIST/'_headers',
    ROOT/'website'/'robots.txt': DIST/'robots.txt',
    ROOT/'website'/'sitemap.xml': DIST/'sitemap.xml',
    ROOT/'assets'/'everkeep.svg': DIST/'assets'/'everkeep.svg',
}

if DIST.exists(): shutil.rmtree(DIST)
for src,dst in FILES.items():
    if not src.is_file(): raise SystemExit(f'missing public source: {src.relative_to(ROOT)}')
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst)
print(f'Built Everkeep public site: {len(FILES)} files -> dist/')