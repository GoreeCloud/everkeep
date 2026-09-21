#!/usr/bin/env python3
"""Validate the mandatory Everkeep repository documentation baseline."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATION_WORKFLOW = ".github/workflows/validate.yml"

REQUIRED_ROOT_FILES = (
    "README.md",
    "SPECIFICATIONS.md",
    "FEATURES.md",
    "FEATURE-ROADMAP.md",
    "BENEFITS.md",
    "COMPETITIVE-OBJECTIVES.md",
    "BRANDING.md",
    "USER-MANUAL.md",
    "PRIVACY POLICY.md",
    "NOTES.md",
    "SECURITY.md",
    ".gitignore",
    ".editorconfig",
    "goreecloud.platform.yaml",
)
REQUIRED_REPOSITORY_CONTROLS = (
    ".github/PULL_REQUEST_TEMPLATE.md",
    VALIDATION_WORKFLOW,
)
MINIMUM_MEANINGFUL_CHARACTERS = 20


def validate_repository_baseline(root: Path = ROOT) -> list[str]:
    validated: list[str] = []
    problems: list[str] = []

    for relative in (*REQUIRED_ROOT_FILES, *REQUIRED_REPOSITORY_CONTROLS):
        path = root / relative
        if not path.is_file():
            problems.append(f"missing required repository control: {relative}")
            continue
        try:
            text = path.read_text(encoding="utf-8").strip()
        except UnicodeDecodeError:
            problems.append(f"required repository control is not UTF-8 text: {relative}")
            continue
        if len(text) < MINIMUM_MEANINGFUL_CHARACTERS:
            problems.append(f"required repository control is empty/placeholder-sized: {relative}")
            continue
        if text.lower() in {"todo", "tbd", "placeholder", "coming soon"}:
            problems.append(f"required repository control is a placeholder: {relative}")
            continue
        validated.append(relative)

    platform = root / "goreecloud.platform.yaml"
    if platform.is_file():
        platform_text = platform.read_text(encoding="utf-8")
        if "repository: GoreeCloud/everkeep" not in platform_text:
            problems.append("platform contract does not identify canonical repository GoreeCloud/everkeep")

    workflow = root / VALIDATION_WORKFLOW
    if workflow.is_file():
        workflow_text = workflow.read_text(encoding="utf-8")
        for token in (
            "persist-credentials: false",
            "Verify exact source revision",
            'run: test "$(git rev-parse HEAD)" = "$EXPECTED_SHA"',
            "Validate repository documentation baseline",
            "Test repository documentation baseline",
        ):
            if token not in workflow_text:
                problems.append(f"validation workflow missing stabilization control: {token}")

    if problems:
        raise SystemExit("Everkeep repository baseline validation failed: " + "; ".join(problems))
    return validated


def main() -> None:
    validated = validate_repository_baseline()
    print(
        "Everkeep repository baseline passed: "
        f"mandatory_root={len(REQUIRED_ROOT_FILES)}, "
        f"conditional_controls={len(REQUIRED_REPOSITORY_CONTROLS)}, "
        f"validated={len(validated)}."
    )


if __name__ == "__main__":
    main()
