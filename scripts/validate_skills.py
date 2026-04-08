#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_manifest(root: Path) -> dict:
    return json.loads((root / "skills-manifest.json").read_text(encoding="utf-8"))


def validate_skill(root: Path, skill: dict) -> list[str]:
    errors: list[str] = []
    skill_root = root / skill["path"]
    name = skill["name"]

    if not skill_root.exists():
        errors.append(f"{name}: missing directory {skill_root}")
        return errors

    skill_md = skill_root / "SKILL.md"
    if not skill_md.exists():
        errors.append(f"{name}: missing SKILL.md")
    else:
        text = skill_md.read_text(encoding="utf-8")
        if f"name: {name}" not in text and f'name: "{name}"' not in text:
            errors.append(f"{name}: SKILL.md front matter should declare the skill name")

    for forbidden in [".codex-home", ".tmp-home", ".automation-home", ".sf", ".sfdx", "Library/Caches"]:
        matches = list(skill_root.glob(f"**/{forbidden}"))
        if matches:
            errors.append(f"{name}: forbidden machine-local path present: {matches[0]}")

    return errors


def main() -> int:
    root = repo_root()
    manifest = load_manifest(root)
    errors: list[str] = []

    skills = manifest.get("skills", [])
    if not skills:
        errors.append("manifest: no skills defined")

    for skill in skills:
        if "name" not in skill or "path" not in skill:
            errors.append(f"manifest: invalid entry {skill}")
            continue
        errors.extend(validate_skill(root, skill))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"OK: validated {len(skills)} skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())
