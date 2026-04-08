# Salesforce-Update

Manual Codex skill for reconciling open Salesforce opportunities from Gmail, Google Calendar, and Granola evidence, then writing validated updates through Salesforce CLI-backed auth.

## What it does

- starts from open opportunities in Salesforce
- enriches each deal with recent email, calendar, and Granola evidence
- updates stage, amount, summary, next step, red flags, contact roles, and selected MEDDPICC fields
- keeps opportunity creation gated as a manual follow-up decision
- writes local run logs for every batch

## Dependencies

- Codex skill support
- Salesforce CLI authenticated to the target org
- Gmail connector
- Google Calendar connector
- Granola connector
- Python 3

## Install

Clone or copy this repository into your Codex skills directory as `Salesforce-Update`.
The repository root is the skill root, so agents can install directly from the repo URL.

Example:

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/0xTrey/salesforce-update-skill.git ~/.codex/skills/Salesforce-Update
```

## Configure

Copy `references/config.example.json` to:

```bash
~/.config/salesforce-update/config.json
```

Then fill in:

- your Salesforce org alias
- your rep email
- your initials
- your failure-alert email
- optionally, `rep.owner_emails` or `rep.owner_names` when a run should cover multiple owners

See `references/config.md` for field notes.

## Use

From inside the installed skill directory:

```bash
python3 scripts/salesforce_update.py check-deps --json
python3 scripts/salesforce_update.py init-run --json
python3 scripts/salesforce_update.py validate-plan --run-dir <run_dir> --json
python3 scripts/salesforce_update.py apply-plan --run-dir <run_dir> --json
```

For the full operating rules and field behavior, read `SKILL.md`.

## Notes

- Standard Salesforce `NextStep` writes are intentionally disabled.
- The helper saves regular opportunity-detail fields separately from MEDDPICC/custom fields.
- Moving into `Validation` or `Contract` requires `Customer_Executive_Sponsor__c`.
- The helper walks stage changes forward in order when Salesforce requires sequential stage advancement.
- Salesforce CLI subprocesses default `SF_DISABLE_LOG_FILE=true` and `SF_DISABLE_TELEMETRY=true` to avoid local log and telemetry prompts from blocking non-interactive runs.
