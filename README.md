# Folloze Skills

Central source of truth for Folloze Codex skills.

This repo is meant to be the team-managed distribution point. Skills live here, updates are reviewed here, and each teammate syncs this repo into `~/.codex/skills` from one local clone.

## Recommended Team Setup

Use this repo as the only place where skill code and instructions are edited. Do not hand-edit skills separately in each person's `~/.codex/skills` directory.

The recommended rollout model is:

1. Each teammate clones this repo to a stable local path such as `~/Projects/Folloze-Skills`
2. They run `python3 scripts/sync_codex_skills.py --overwrite`
3. The sync script links or copies each repo skill into `~/.codex/skills`
4. An optional macOS `launchd` job runs `git pull --ff-only` plus the same sync command on a schedule
5. Teammates restart Codex after skill updates so the app reloads the changed skill files

This is the practical replacement for Codex's built-in GitHub installer, which is install-oriented and not a live team update channel.

If you want the update flow to be callable from inside Codex instead of shell-first, use the `skills-updater` skill in this repo. That skill wraps the repo pull + changed-skill sync process behind one command.

## What "Automatic Update" Means Here

GitHub push alone will not update a teammate's installed skills.

To make updates propagate automatically, you need two layers:

- This repo as the source of truth
- A local sync mechanism on each machine that pulls the repo and refreshes `~/.codex/skills`

The repo now includes both:

- `skills-manifest.json`
- `scripts/sync_codex_skills.py`
- `scripts/validate_skills.py`
- `ops/launchd/com.folloze.codex-skills-sync.plist.template`

## Initial Rollout

From a teammate machine:

```bash
git clone git@github.com:0xTrey/Folloze-Skills.git ~/Projects/Folloze-Skills
cd ~/Projects/Folloze-Skills
python3 scripts/sync_codex_skills.py --overwrite
```

For ongoing automatic sync on macOS:

1. Copy the launchd template in `ops/launchd/`
2. Replace `__REPO_ROOT__` with that teammate's local clone path
3. Load it with `launchctl`

The scheduled command will:

- `git pull --ff-only`
- refresh the linked skills under `~/.codex/skills`

## Governance

Use normal software delivery rules here:

- Protect `main`
- Require PR review for skill changes
- Run validation on every PR
- Avoid machine-specific absolute paths in skills
- Keep secrets and personal tokens out of the repo

If these skills include internal sales process, GTM workflow, or customer-specific implementation details, this repo should be private before full team rollout.

## Structure

- `Skills/`
- `scripts/`
- `ops/`
- `.github/workflows/`

Each skill lives in its own subdirectory so it can carry its own `SKILL.md`, scripts, references, and agent config.

## Included Skills

### `account-org-chart`
Builds a company org chart workbook across Marketing, Sales, IT, Digital, AI, Strategy, and Product Marketing, then uploads the result into the correct company folder in Google Drive as a native Google Sheet.

### `folloze-sales-doc`
Builds branded Folloze sales and customer lifecycle documents such as discovery prep docs, stakeholder maps, onboarding plans, QBRs, renewal prep docs, and account summaries using the shared Folloze design system.

### `Salesforce-Update`
Manually reconciles Salesforce open opportunities from Gmail, Google Calendar, and Granola evidence, then writes validated updates through the local Salesforce helper flow.

### `skills-updater`
Bootstraps or updates the shared Folloze skills repo on a teammate machine, then syncs changed skills into `~/.codex/skills`.

## Conventions

- Put each skill in `Skills/<skill-name>/`
- Keep the runnable instructions in `SKILL.md`
- Put helper scripts in `scripts/` when the skill needs automation
- Put reference docs and examples in `references/`
- Keep skills machine-independent and avoid user-specific absolute paths
- Avoid generated artifacts and local caches in git
