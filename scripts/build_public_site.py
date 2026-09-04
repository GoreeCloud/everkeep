#!/usr/bin/env python3
import hashlib
import json
import posixpath
import re
from pathlib import Path
import shutil
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "website"
DIST = ROOT / "dist"
LOCK = SITE / "glaze.lock.json"
IMPORT_RE = re.compile(r"@import\s+([^;]+);", re.IGNORECASE)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def parse_import(statement: str, source_path: str) -> str:
    spec = statement.strip()
    match = re.match(r"""url\(\s*(['"])(.*?)\1\s*\)""", spec, re.IGNORECASE)
    if match is None:
        match = re.match(r"""(['"])(.*?)\1""", spec)
    if match is None:
        raise SystemExit(f"unsupported CSS @import syntax in {source_path}: {statement!r}")
    target = match.group(2).strip()
    if not target:
        raise SystemExit(f"empty CSS @import target in {source_path}")
    if "://" in target or target.startswith("//"):
        raise SystemExit(f"remote CSS @import is forbidden in {source_path}: {target}")
    if target.startswith("/"):
        raise SystemExit(f"root-absolute CSS @import is forbidden in {source_path}: {target}")
    if "?" in target or "#" in target:
        raise SystemExit(f"query/fragment CSS @import is forbidden in {source_path}: {target}")
    return target


def validate_import_closure(entrypoint: str, fetched: dict[str, bytes]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(source_path: str) -> None:
        if source_path in visiting:
            raise SystemExit(f"cyclic CSS @import detected at {source_path}")
        if source_path in visited:
            return
        data = fetched.get(source_path)
        if data is None:
            raise SystemExit(f"missing CSS import target in immutable Glaze graph: {source_path}")
        try:
            css = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SystemExit(f"non-UTF-8 CSS in immutable Glaze graph: {source_path}") from exc

        visiting.add(source_path)
        for statement in IMPORT_RE.findall(css):
            target = parse_import(statement, source_path)
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(source_path), target))
            if resolved.startswith("../") or resolved == ".." or not resolved.startswith("css/"):
                raise SystemExit(f"CSS @import escapes the locked css/ graph in {source_path}: {target}")
            visit(resolved)
        visiting.remove(source_path)
        visited.add(source_path)

    visit(entrypoint)


lock = json.loads(LOCK.read_text(encoding="utf-8"))
if lock.get("version") != "1.1.0" or lock.get("entrypoint") != "css/glaze-v1.1.0.css":
    raise SystemExit("Continuity Center must target the current GLAZE UI V1.1 / 1.1.0 Stable contract")
release_commit = lock.get("release_commit", "")
if not re.fullmatch(r"[0-9a-f]{40}", release_commit):
    raise SystemExit("Continuity Center Glaze lock requires an immutable lowercase release commit")
locked_files = lock.get("files")
if not isinstance(locked_files, dict) or len(locked_files) != 13:
    raise SystemExit("Continuity Center Glaze lock must contain the complete 13-file Stable web graph")

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

fetched: dict[str, bytes] = {}
for upstream_path, expected_blob in locked_files.items():
    if not isinstance(upstream_path, str) or not upstream_path.startswith("css/"):
        raise SystemExit(f"invalid locked Glaze path: {upstream_path!r}")
    if not isinstance(expected_blob, str) or not re.fullmatch(r"[0-9a-f]{40}", expected_blob):
        raise SystemExit(f"invalid locked Git blob identity for {upstream_path}")
    url = (
        "https://raw.githubusercontent.com/GoreeCloud/goreecloud-glaze-ui/"
        + release_commit
        + "/"
        + upstream_path
    )
    request = Request(url, headers={"User-Agent": "GoreeCloud-Continuity-Center-Build/1"})
    with urlopen(request, timeout=20) as response:
        data = response.read()
    actual_blob = git_blob_sha(data)
    if actual_blob != expected_blob:
        raise SystemExit(
            f"Glaze source identity mismatch for {upstream_path}: "
            f"expected {expected_blob}, got {actual_blob}"
        )
    fetched[upstream_path] = data

# Fail closed before publishing anything if the immutable dependency graph is incomplete.
# This intentionally detects the known 1.1.0 stale import until a corrected immutable
# Stable release is published and this consumer is explicitly re-pinned.
validate_import_closure(lock["entrypoint"], fetched)

if DIST.exists():
    shutil.rmtree(DIST)
for src, dst in files.items():
    if not src.is_file():
        raise SystemExit(f"missing public source: {src.relative_to(ROOT)}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

(DIST / "assets" / "glaze").mkdir(parents=True, exist_ok=True)
for upstream_path, data in fetched.items():
    (DIST / "assets" / "glaze" / Path(upstream_path).name).write_bytes(data)

print("Built Everkeep public site with import-closed immutable GLAZE UI V1.1 / 1.1.0 Stable -> dist/")
