#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import shutil
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "website"
DIST = ROOT / "dist"
LOCK = SITE / "glaze.lock.json"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


lock = json.loads(LOCK.read_text(encoding="utf-8"))
if lock.get("version") != "1.1.0" or lock.get("entrypoint") != "css/glaze-v1.1.0.css":
    raise SystemExit("Continuity Center must target GLAZE UI V1.1 / 1.1.0 Stable")
release_commit = lock.get("release_commit", "")
if len(release_commit) != 40:
    raise SystemExit("Continuity Center Glaze lock requires an immutable release commit")

files = {
    SITE / "index.html": DIST / "index.html",
    SITE / "style.css": DIST / "style.css",
    SITE / "site-polish.css": DIST / "site-polish.css",
    SITE / "site.js": DIST / "site.js",
    SITE / "_headers": DIST / "_headers",
    SITE / "robots.txt": DIST / "robots.txt",
    SITE / "sitemap.xml": DIST / "sitemap.xml",
    ROOT / "assets" / "everkeep.svg": DIST / "assets" / "everkeep.svg",
}

if DIST.exists():
    shutil.rmtree(DIST)
for src, dst in files.items():
    if not src.is_file():
        raise SystemExit(f"missing public source: {src.relative_to(ROOT)}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

(DIST / "assets" / "glaze").mkdir(parents=True, exist_ok=True)
for upstream_path, expected_blob in lock["files"].items():
    url = "https://raw.githubusercontent.com/GoreeCloud/goreecloud-glaze-ui/" + release_commit + "/" + upstream_path
    request = Request(url, headers={"User-Agent": "GoreeCloud-Continuity-Center-Build/1"})
    with urlopen(request, timeout=20) as response:
        data = response.read()
    actual_blob = git_blob_sha(data)
    if actual_blob != expected_blob:
        raise SystemExit(f"Glaze source identity mismatch for {upstream_path}: expected {expected_blob}, got {actual_blob}")
    (DIST / "assets" / "glaze" / Path(upstream_path).name).write_bytes(data)

print(f"Built Everkeep public site with immutable GLAZE UI V1.1 / 1.1.0 Stable -> dist/")
