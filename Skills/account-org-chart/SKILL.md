---
name: account-org-chart
description: Builds a company org chart workbook across Marketing, Sales, IT, Digital, AI, Strategy, and Product Marketing, then uploads the result into the correct company folder in Google Drive as a native Google Sheet.
---

# Account Org Chart

Use this skill when a teammate needs an org-chart workbook for a target account and the final artifact should land in the correct Google Drive folder as a native Google Sheet.

## Status

Starter scaffold only. Expand this skill with the exact workflow, Drive folder conventions, workbook schema, and any helper scripts before team rollout.

## Expected Shape

- Put automation helpers in `scripts/`
- Put example schemas and mapping docs in `references/`
- Keep any account-specific data out of git

## Minimum Workflow To Define

1. Identify the target company and the destination Drive folder
2. Gather people across Marketing, Sales, IT, Digital, AI, Strategy, and Product Marketing
3. Build the workbook with role, level, function, reporting line, and notes
4. Upload or convert the result into Google Sheets
