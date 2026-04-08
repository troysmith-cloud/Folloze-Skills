#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


FORBIDDEN_TEXT_PATTERNS = (
    "/Users/treyharnden",
    "/Users/",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest(root: Path, manifest: dict, errors: list[str]) -> list[dict]:
    seen: set[str] = set()
    skills = manifest.get("skills", [])
    if not isinstance(skills, list) or not skills:
        errors.append("skills-manifest.json must contain a non-empty 'skills' list.")
        return []

    for skill in skills:
        name = skill.get("name")
        rel_path = skill.get("path")
        if not name or not rel_path:
            errors.append(f"Invalid manifest entry: {skill!r}")
            continue
        if name in seen:
            errors.append(f"Duplicate manifest skill name: {name}")
            continue
        seen.add(name)

        skill_dir = root / rel_path
        if not skill_dir.exists():
            errors.append(f"Manifest path does not exist for {name}: {skill_dir}")
            continue

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            errors.append(f"Missing SKILL.md for {name}: {skill_md}")
        else:
            text = skill_md.read_text(encoding="utf-8")
            if f"name: {name}" not in text and f'name: "{name}"' not in text:
                errors.append(f"{name}: SKILL.md front matter should declare the skill name")

        for forbidden in [".codex-home", ".tmp-home", ".automation-home", ".sf", ".sfdx", "Library/Caches"]:
            matches = list(skill_dir.glob(f"**/{forbidden}"))
            if matches:
                errors.append(f"{name}: forbidden machine-local path present: {matches[0]}")

    return skills


def scan_for_forbidden_paths(root: Path, errors: list[str]) -> None:
    for path in root.rglob("*"):
        if path.is_dir() or ".git" in path.parts:
            continue
        if path == Path(__file__).resolve():
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".xlsx"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in FORBIDDEN_TEXT_PATTERNS:
            if pattern in text:
                errors.append(f"Forbidden machine-specific path '{pattern}' found in {path}")


def compile_python(root: Path, errors: list[str]) -> None:
    python_files = sorted(root.rglob("*.py"))
    if not python_files:
        return
    cmd = [sys.executable, "-m", "py_compile", *[str(path) for path in python_files]]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        errors.append(result.stderr.strip() or "Python compilation failed.")


def main() -> int:
    root = repo_root()
    manifest_path = root / "skills-manifest.json"
    errors: list[str] = []

    if not manifest_path.exists():
        errors.append(f"Missing manifest: {manifest_path}")
    else:
        manifest = load_manifest(manifest_path)
        skills = validate_manifest(root, manifest, errors)

    scan_for_forbidden_paths(root, errors)
    compile_python(root, errors)

    if errors:
        print("Skill validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Skill validation passed for {len(skills)} skills.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
