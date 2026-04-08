#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_manifest(root: Path) -> dict:
    manifest_path = root / "skills-manifest.json"
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def copy_skill(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, symlinks=True)


def link_skill(src: Path, dst: Path) -> None:
    os.symlink(src, dst, target_is_directory=True)


def sync_skill(src: Path, dst: Path, overwrite: bool, mode: str, dry_run: bool) -> str:
    if dst.exists() or dst.is_symlink():
        if not overwrite:
            return f"skip   {dst} (exists)"
        if not dry_run:
            remove_path(dst)

    if dry_run:
        return f"{mode:6} {src} -> {dst}"

    if mode == "link":
        link_skill(src, dst)
    else:
        copy_skill(src, dst)
    return f"{mode:6} {src} -> {dst}"


def maybe_git_pull(root: Path, enabled: bool) -> None:
    if not enabled:
        return
    subprocess.run(
        ["git", "-C", str(root), "pull", "--ff-only"],
        check=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync repository-managed Codex skills into ~/.codex/skills")
    parser.add_argument("--target", default="~/.codex/skills", help="Install target for Codex skills")
    parser.add_argument("--mode", choices=["link", "copy"], default="link", help="Install via symlink or copy")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing target skills")
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing")
    parser.add_argument("--git-pull", action="store_true", help="Run git pull --ff-only before syncing")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    root = repo_root()
    manifest = load_manifest(root)
    target_root = Path(args.target).expanduser()

    maybe_git_pull(root, args.git_pull)

    if not args.dry_run:
        target_root.mkdir(parents=True, exist_ok=True)

    results: list[str] = []
    for skill in manifest.get("skills", []):
        name = skill["name"]
        src = root / skill["path"]
        dst = target_root / name
        if not src.exists():
            results.append(f"error  missing source {src}")
            continue
        results.append(sync_skill(src, dst, args.overwrite, args.mode, args.dry_run))

    for line in results:
        print(line)

    errors = [line for line in results if line.startswith("error")]
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
