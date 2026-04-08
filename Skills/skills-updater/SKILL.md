---
name: skills-updater
description: Bootstraps or updates the shared Folloze skills repository on a teammate machine, then syncs changed skills into ~/.codex/skills.
---

# Skills Updater

Use this skill when a teammate wants to install or refresh the shared Folloze skills repository from inside Codex instead of driving the process manually from the shell.

## Workflow

1. Confirm the local repository path, defaulting to `~/Projects/Folloze-Skills`
2. If the repository does not exist, clone it
3. If it exists, run `git pull --ff-only`
4. Run `python3 scripts/sync_codex_skills.py --overwrite`
5. Tell the teammate to restart Codex so updated skills are reloaded

## Guardrails

- Do not modify `~/.codex/skills` by hand
- Treat this repository as the source of truth
- Keep local machine auth, caches, and logs out of git
