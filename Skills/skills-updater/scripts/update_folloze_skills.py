#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


DEFAULT_REPO_URL = os.environ.get(
    "FOLLOZE_SKILLS_REPO_URL",
    "https://github.com/0xTrey/Folloze-Skills.git",
)
DEFAULT_REPO_ROOT = Path(
    os.environ.get(
        "FOLLOZE_SKILLS_REPO_ROOT",
        str(Path.home() / "Projects" / "Folloze-Skills"),
    )
)
DEFAULT_BRANCH = os.environ.get("FOLLOZE_SKILLS_REPO_BRANCH", "main")
DEFAULT_CODEX_HOME = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
DEFAULT_DEST = DEFAULT_CODEX_HOME / "skills"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap, pull, and sync shared Folloze Codex skills.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(DEFAULT_REPO_ROOT),
        help="Local clone path for the Folloze-Skills repository.",
    )
    parser.add_argument(
        "--repo-url",
        default=DEFAULT_REPO_URL,
        help="GitHub repo URL used when cloning for the first time.",
    )
    parser.add_argument(
        "--branch",
        default=DEFAULT_BRANCH,
        help="Branch to track. Defaults to main.",
    )
    parser.add_argument(
        "--dest",
        default=str(DEFAULT_DEST),
        help="Destination skills directory. Defaults to $CODEX_HOME/skills or ~/.codex/skills.",
    )
    parser.add_argument(
        "--mode",
        choices=("symlink", "copy"),
        default="symlink",
        help="Install mode passed through to sync_codex_skills.py.",
    )
    parser.add_argument(
        "--skill",
        action="append",
        default=[],
        help="Refresh only the named skill. May be passed multiple times.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Refresh all enabled skills even if only some changed.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without making changes.",
    )
    return parser.parse_args()


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    dry_run: bool = False,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str] | None:
    print(f"$ {' '.join(cmd)}")
    if dry_run:
        return None
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        capture_output=capture_output,
    )


def git_output(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def ensure_repo(repo_root: Path, repo_url: str, branch: str, dry_run: bool) -> bool:
    if repo_root.exists():
        try:
            git_output(repo_root, "rev-parse", "--show-toplevel")
        except subprocess.CalledProcessError as exc:
            raise SystemExit(f"Existing path is not a git repo: {repo_root}") from exc
        return False

    run(
        ["git", "clone", "--branch", branch, repo_url, str(repo_root)],
        dry_run=dry_run,
    )
    return True


def ensure_clean_worktree(repo_root: Path) -> None:
    status = git_output(repo_root, "status", "--porcelain")
    if status:
        raise SystemExit(
            "Local Folloze-Skills clone has uncommitted changes. "
            "Use a clean clone for updater runs."
        )


def changed_files(repo_root: Path, old_head: str | None, new_head: str) -> list[str]:
    if old_head is None:
        return []
    output = git_output(repo_root, "diff", "--name-only", f"{old_head}..{new_head}")
    return [line for line in output.splitlines() if line]


def load_manifest(repo_root: Path) -> dict:
    return json.loads((repo_root / "skills-manifest.json").read_text())


def enabled_skills(manifest: dict) -> set[str]:
    return {skill["name"] for skill in manifest["skills"] if skill.get("enabled", True)}


def changed_skill_names(files: list[str]) -> set[str]:
    names: set[str] = set()
    for rel_path in files:
        parts = Path(rel_path).parts
        if len(parts) >= 2 and parts[0] == "Skills":
            names.add(parts[1])
    return names


def missing_installed_skills(dest: Path, enabled_names: set[str]) -> set[str]:
    missing: set[str] = set()
    for skill_name in enabled_names:
        if not (dest / skill_name).exists():
            missing.add(skill_name)
    return missing


def sync_skills(
    repo_root: Path,
    dest: Path,
    mode: str,
    skill_names: list[str] | None,
    prune: bool,
    dry_run: bool,
) -> None:
    sync_script = repo_root / "scripts" / "sync_codex_skills.py"
    cmd = [
        sys.executable,
        str(sync_script),
        "--repo-root",
        str(repo_root),
        "--dest",
        str(dest),
        "--mode",
        mode,
        "--overwrite",
    ]
    if prune:
        cmd.append("--prune")
    if dry_run:
        cmd.append("--dry-run")
    if skill_names:
        for skill_name in skill_names:
            cmd.extend(["--skill", skill_name])
    run(cmd, dry_run=False)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()
    dest = Path(args.dest).expanduser().resolve()
    requested = set(args.skill)

    cloned = ensure_repo(repo_root, args.repo_url, args.branch, args.dry_run)
    if args.dry_run and cloned and not repo_root.exists():
        print("Repo does not exist locally yet. First updater run would clone it, then perform a full sync.")
        return 0

    ensure_clean_worktree(repo_root)

    manifest_before = load_manifest(repo_root)
    enabled_before = enabled_skills(manifest_before)
    old_head = None if cloned else git_output(repo_root, "rev-parse", "HEAD")

    run(["git", "-C", str(repo_root), "fetch", "origin", args.branch], dry_run=args.dry_run)

    if args.dry_run:
        if old_head is None:
            print("Dry run: first install would perform a full sync after clone.")
            return 0
        remote_head = git_output(repo_root, "rev-parse", f"origin/{args.branch}")
        files = changed_files(repo_root, old_head, remote_head)
        skills = sorted(changed_skill_names(files))
        manifest = load_manifest(repo_root)
        missing = sorted(missing_installed_skills(dest, enabled_skills(manifest)))
        print(f"current_head: {old_head}")
        print(f"remote_head: {remote_head}")
        if files:
            print("changed_files:")
            for rel_path in files:
                print(f"- {rel_path}")
        else:
            print("No upstream changes detected.")
        if skills:
            print("changed_skills:")
            for skill_name in skills:
                print(f"- {skill_name}")
        if missing:
            print("missing_installed_skills:")
            for skill_name in missing:
                print(f"- {skill_name}")
        if args.all:
            print("Dry run: would perform a full sync.")
        elif requested:
            print(f"Dry run: would sync requested skills: {', '.join(sorted(requested))}")
        elif missing:
            print(f"Dry run: would sync missing skills: {', '.join(missing)}")
        return 0

    if old_head is None:
        new_head = git_output(repo_root, "rev-parse", "HEAD")
    else:
        run(
            ["git", "-C", str(repo_root), "pull", "--ff-only", "origin", args.branch],
            dry_run=False,
        )
        new_head = git_output(repo_root, "rev-parse", "HEAD")

    manifest_after = load_manifest(repo_root)
    enabled_after = enabled_skills(manifest_after)
    files = changed_files(repo_root, old_head, new_head)
    skill_changes = changed_skill_names(files)
    missing_skills = missing_installed_skills(dest, enabled_after)

    manifest_changed = "skills-manifest.json" in files or enabled_before != enabled_after
    sync_all = cloned or args.all or (not requested and manifest_changed)

    if requested:
        skills_to_sync = sorted(requested)
    elif sync_all:
        skills_to_sync = []
    else:
        skills_to_sync = sorted(skill_changes | missing_skills)

    print(f"old_head: {old_head or '(new clone)'}")
    print(f"new_head: {new_head}")
    if missing_skills:
        print(f"missing_installed_skills: {', '.join(sorted(missing_skills))}")

    if not cloned and old_head == new_head and not args.all and not requested and not missing_skills:
        print("Repo already up to date. No skill changes to sync.")
        return 0

    if sync_all:
        print("Performing full skill sync.")
        sync_skills(
            repo_root=repo_root,
            dest=dest,
            mode=args.mode,
            skill_names=None,
            prune=True,
            dry_run=False,
        )
        print("Restart Codex if you want the updated skills to be reloaded immediately.")
        return 0

    if not skills_to_sync:
        print("Repo updated, but no skill directory changes were detected.")
        return 0

    print(f"Syncing changed skills: {', '.join(skills_to_sync)}")
    sync_skills(
        repo_root=repo_root,
        dest=dest,
        mode=args.mode,
        skill_names=skills_to_sync,
        prune=False,
        dry_run=False,
    )
    print("Restart Codex if you want the updated skills to be reloaded immediately.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
