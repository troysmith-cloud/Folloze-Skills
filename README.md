# Folloze Skills

Public home for reusable Folloze-oriented Codex skills.

## Structure

- `Skills/`
  - `account-org-chart/`
  - `Salesforce-Update/`

Each skill lives in its own subdirectory so it can carry its own `SKILL.md`, scripts, references, and agent config.

## Included Skills

### `account-org-chart`
Builds a company org chart workbook across Marketing, Sales, IT, Digital, AI, Strategy, and Product Marketing, then uploads the result into the correct company folder in Google Drive as a native Google Sheet.

### `Salesforce-Update`
Manually reconciles Salesforce open opportunities from Gmail, Google Calendar, and Granola evidence, then writes validated updates through the local Salesforce helper flow.

## Conventions

- Put each skill in `Skills/<skill-name>/`
- Keep the runnable instructions in `SKILL.md`
- Put helper scripts in `scripts/` when the skill needs automation
- Put reference docs and examples in `references/`
- Avoid generated artifacts and local caches in git
