#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    repo_root = default_repo_root()
    default_codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))

    parser = argparse.ArgumentParser(
        description="Sync repository-managed Folloze skills into ~/.codex/skills.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(repo_root),
        help="Path to the local Folloze-Skills clone.",
    )
    parser.add_argument(
        "--manifest",
        help="Path to the skills manifest. Defaults to <repo-root>/skills-manifest.json.",
    )
    parser.add_argument(
        "--dest",
        "--target",
        dest="dest",
        default=str(default_codex_home / "skills"),
        help="Destination skills directory. Defaults to $CODEX_HOME/skills or ~/.codex/skills.",
    )
    parser.add_argument(
        "--skill",
        action="append",
        default=[],
        help="Install only the named skill. May be passed multiple times.",
    )
    parser.add_argument(
        "--mode",
        choices=("symlink", "link", "copy"),
        default="symlink",
        help="Install mode. Symlink is the recommended default for team-managed repos.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing destination skill directory when needed.",
    )
    parser.add_argument(
        "--pull",
        "--git-pull",
        dest="pull",
        action="store_true",
        help="Run git pull --ff-only before syncing.",
    )
    parser.add_argument(
        "--remote",
        default="origin",
        help="Git remote to use with --pull. Defaults to origin.",
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Git branch to use with --pull. Defaults to main.",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Remove symlinked skills in the destination that point into this repo but are no longer in the selected manifest set.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without modifying the filesystem.",
    )
    return parser.parse_args()


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    shutil.rmtree(path)


def copy_skill(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, symlinks=True)


def link_skill(src: Path, dst: Path) -> None:
    dst.symlink_to(src, target_is_directory=True)


def ensure_git_pull(repo_root: Path, remote: str, branch: str, dry_run: bool) -> None:
    cmd = ["git", "-C", str(repo_root), "pull", "--ff-only", remote, branch]
    print(f"$ {' '.join(cmd)}")
    if dry_run:
        return
    subprocess.run(cmd, check=True)


def resolve_selected_skills(manifest: dict, requested: set[str]) -> list[dict]:
    skills = [skill for skill in manifest["skills"] if skill.get("enabled", True)]
    if not requested:
        return skills

    selected = [skill for skill in skills if skill["name"] in requested]
    missing = sorted(requested - {skill["name"] for skill in selected})
    if missing:
        raise SystemExit(f"Unknown skills in selection: {', '.join(missing)}")
    return selected


def install_skill(src: Path, dst: Path, mode: str, overwrite: bool, dry_run: bool) -> None:
    normalized_mode = "symlink" if mode == "link" else mode
    action = "link" if normalized_mode == "symlink" else "copy"
    print(f"{action}: {src} -> {dst}")

    if dry_run:
        return

    if dst.exists() or dst.is_symlink():
        same_symlink = normalized_mode == "symlink" and dst.is_symlink() and dst.resolve() == src.resolve()
        if same_symlink:
            return
        if not overwrite:
            raise SystemExit(f"Destination already exists: {dst} (use --overwrite)")
        remove_path(dst)

    if normalized_mode == "symlink":
        link_skill(src, dst)
        return
    copy_skill(src, dst)


def prune_managed_symlinks(repo_root: Path, dest_root: Path, keep_names: set[str], dry_run: bool) -> None:
    if not dest_root.exists():
        return

    for child in sorted(dest_root.iterdir()):
        if child.name in keep_names or not child.is_symlink():
            continue
        try:
            target = child.resolve()
        except FileNotFoundError:
            target = None
        if target is None or repo_root not in target.parents:
            continue
        print(f"prune: {child}")
        if not dry_run:
            child.unlink()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve() if args.manifest else repo_root / "skills-manifest.json"
    dest_root = Path(args.dest).expanduser().resolve()

    if not repo_root.exists():
        raise SystemExit(f"Repo root not found: {repo_root}")
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")

    if args.pull:
        ensure_git_pull(repo_root, args.remote, args.branch, args.dry_run)

    manifest = load_manifest(manifest_path)
    requested = set(args.skill)
    selected = resolve_selected_skills(manifest, requested)
    keep_names = {skill["name"] for skill in selected}

    print(f"repo: {repo_root}")
    print(f"dest: {dest_root}")
    print(f"mode: {args.mode}")

    if not args.dry_run:
        dest_root.mkdir(parents=True, exist_ok=True)

    for skill in selected:
        src = (repo_root / skill["path"]).resolve()
        dst = dest_root / skill["name"]
        if not src.exists():
            raise SystemExit(f"Skill source does not exist: {src}")
        install_skill(src, dst, args.mode, args.overwrite, args.dry_run)

    if args.prune:
        prune_managed_symlinks(repo_root, dest_root, keep_names, args.dry_run)

    if selected:
        names = ", ".join(sorted(keep_names))
        print(f"synced: {names}")
        print("Restart Codex after updates so the changed skills are reloaded.")
    else:
        print("No enabled skills selected.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
