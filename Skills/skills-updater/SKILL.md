---
name: skills-updater
description: Update the shared Folloze Codex skills from the central GitHub repository into the local ~/.codex/skills installation. Use when someone says "update my skills", "sync the Folloze skills", "pull the latest shared skills", "refresh our Codex skills", or asks Codex to install newly added repo skills on their machine.
---

# Skills Updater

Use this skill to refresh the locally installed Folloze skills from the central GitHub repo.

This skill is the user-facing entrypoint for the shared-skill distribution flow:

- it ensures the team repo exists locally
- it fast-forwards the repo from GitHub
- it detects which `Skills/<name>/` folders changed
- it syncs those changes into `${CODEX_HOME:-$HOME/.codex}/skills`

By default it assumes the local clone lives at `~/Projects/Folloze-Skills`. Override that with `FOLLOZE_SKILLS_REPO_ROOT` if needed.

## When To Use

Use this skill when the user wants any of the following:

- update shared Folloze skills
- sync newly added skills from the repo
- pull the latest skill changes from GitHub
- refresh the local Codex skill installation after another teammate updated a skill

## One-Time Assumptions

- Each teammate should have one clean local clone of the shared repo
- That clone should be used for syncing, not for ad hoc edits
- If the repo is private, the machine must already have GitHub access configured

## Default Command

Run the helper script shipped with this skill:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/skills-updater/scripts/update_folloze_skills.py"
```

The helper will:

- clone `Folloze-Skills` into `~/Projects/Folloze-Skills` if it does not exist
- fetch and fast-forward `main`
- sync only changed skills when possible
- fall back to a full sync when the manifest changes or on first install

## Useful Variants

Dry run:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/skills-updater/scripts/update_folloze_skills.py" --dry-run
```

Force a full refresh:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/skills-updater/scripts/update_folloze_skills.py" --all
```

Refresh only specific skills:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/skills-updater/scripts/update_folloze_skills.py" \
  --skill account-org-chart \
  --skill Salesforce-Update
```

## Guardrails

- If the local repo clone has uncommitted changes, stop and tell the user to use a clean clone for updates
- Do not edit `~/.codex/skills` by hand as part of normal updates; use the helper script
- After a successful update, tell the user whether Codex should be restarted

## Expected Response

Return a short summary:

- repo updated or already current
- which skills were refreshed
- whether a Codex restart is needed
