#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_repository_baseline.py"
SPEC = importlib.util.spec_from_file_location("validate_repository_baseline", MODULE_PATH)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


class RepositoryBaselineTests(unittest.TestCase):
    def populate(self, root: Path) -> None:
        for relative in (*validator.REQUIRED_ROOT_FILES, *validator.REQUIRED_REPOSITORY_CONTROLS):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if relative == "goreecloud.platform.yaml":
                content = "component:\n  repository: GoreeCloud/everkeep\n"
            elif relative == validator.ROADMAP:
                content = "**Canonical repository:** GoreeCloud/everkeep\nmeaningful roadmap control\n"
            elif relative == validator.VALIDATION_WORKFLOW:
                content = (
                    "persist-credentials: false\n"
                    "Verify exact source revision\n"
                    'run: test "$(git rev-parse HEAD)" = "$EXPECTED_SHA"\n'
                    "Validate repository documentation baseline\n"
                    "Test repository documentation baseline\n"
                )
            else:
                content = f"meaningful repository control for {relative}\n"
            path.write_text(content, encoding="utf-8")

    def test_governed_root_baseline_is_complete(self) -> None:
        self.assertEqual(len(validator.REQUIRED_ROOT_FILES), 15)
        self.assertIn("PRIVACY POLICY.md", validator.REQUIRED_ROOT_FILES)
        self.assertIn("NOTES.md", validator.REQUIRED_ROOT_FILES)
        self.assertIn("CAPABILITIES.md", validator.REQUIRED_ROOT_FILES)

    def test_complete_baseline_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            self.assertEqual(len(validator.validate_repository_baseline(root)), 17)

    def test_missing_required_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            (root / "FEATURES.md").unlink()
            with self.assertRaises(SystemExit):
                validator.validate_repository_baseline(root)

    def test_placeholder_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            (root / "BENEFITS.md").write_text("TBD\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                validator.validate_repository_baseline(root)

    def test_stale_platform_repository_identity_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            (root / "goreecloud.platform.yaml").write_text(
                "component:\n  repository: GoreeCloud/goreecloud-everkeep\n", encoding="utf-8"
            )
            with self.assertRaises(SystemExit):
                validator.validate_repository_baseline(root)

    def test_stale_roadmap_repository_identity_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            (root / validator.ROADMAP).write_text(
                "**Canonical repository:** GoreeCloud/goreecloud-everkeep\nmeaningful roadmap control\n",
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit):
                validator.validate_repository_baseline(root)


if __name__ == "__main__":
    unittest.main()
