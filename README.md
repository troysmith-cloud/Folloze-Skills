# Folloze Skills

Central source of truth for Folloze Codex skills.

This repository is the team-managed distribution point for shared skills. Skills live here, updates are reviewed here, and each teammate syncs this repository into `~/.codex/skills` from one stable local clone.

## Recommended Team Setup

Use this repository as the only place where skill code and instructions are edited. Do not hand-edit skills separately inside each person's `~/.codex/skills` directory.

Recommended rollout:

1. Clone this repository to a stable local path such as `~/Projects/Folloze-Skills`
2. Run `python3 scripts/sync_codex_skills.py --overwrite`
3. The sync script links or copies each repository skill into `~/.codex/skills`
4. Optionally install the macOS `launchd` job in `ops/launchd/` to run `git pull --ff-only` plus the same sync command on a schedule
5. Restart Codex after skill updates so the app reloads the changed skill files

This setup is the practical replacement for Codex's built-in GitHub installer, which is install-oriented and not a live team update channel.

If you want the update flow to be callable from inside Codex instead of shell-first, use the `skills-updater` skill in this repository. That skill wraps the repository pull plus changed-skill sync process behind one command.

## What "Automatic Update" Means Here

GitHub push alone will not update a teammate's installed skills.

To make updates propagate automatically, you need two layers:

1. This repository as the source of truth
2. A local sync mechanism on each machine that pulls the repository and refreshes `~/.codex/skills`

This repository includes both:

- `skills-manifest.json`
- `scripts/sync_codex_skills.py`
- `scripts/validate_skills.py`
- `ops/launchd/com.folloze.codex-skills-sync.plist.template`

## Initial Rollout

```bash
git clone git@github.com:troysmith-cloud/Folloze-Skills.git ~/Projects/Folloze-Skills
cd ~/Projects/Folloze-Skills
python3 scripts/sync_codex_skills.py --overwrite
```

For ongoing automatic sync on macOS:

1. Copy the template in `ops/launchd/`
2. Replace `__REPO_ROOT__` with the teammate's local clone path
3. Load it with `launchctl`

The scheduled command will:

- run `git pull --ff-only`
- refresh the linked or copied skills under `~/.codex/skills`

## Governance

Use normal software delivery rules here:

- Protect `main`
- Require PR review for skill changes
- Run validation on every PR
- Avoid machine-specific absolute paths in skills
- Keep secrets and personal tokens out of the repository

If these skills include internal sales process, GTM workflow, or customer-specific implementation details, keep this repository private before full team rollout.

## Structure

- `Skills/`
- `scripts/`
- `ops/`
- `.github/workflows/`

Each skill lives in its own subdirectory so it can carry its own `SKILL.md`, scripts, references, and agent config.

## Included Skills

- `account-org-chart`
- `daily-email-summary-delivery`
- `doc`
- `folloze-sales-doc`
- `Folloze-Customer-Watchlist`
- `linkedin-operator-content`
- `pdf`
- `playwright`
- `Salesforce-Update`
- `skills-updater`
- `sora`
- `spreadsheet`

## Conventions

- Put each skill in `Skills/<skill-name>/`
- Keep runnable instructions in `SKILL.md`
- Put helper scripts in `scripts/` when the skill needs automation
- Put reference docs and examples in `references/`
- Keep skills machine-independent and avoid user-specific absolute paths
- Avoid generated artifacts and local caches in git

## Common Commands

```bash
python3 scripts/validate_skills.py
python3 scripts/sync_codex_skills.py --overwrite
python3 scripts/sync_codex_skills.py --dry-run
```
