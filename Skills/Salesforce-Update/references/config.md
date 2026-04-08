Use the config file at `~/.config/salesforce-update/config.json` unless `SALESFORCE_UPDATE_CONFIG` points elsewhere.

Copy the example from `references/config.example.json`.

## Required fields

- `salesforce.org_alias`
- `rep.initials`
- `notifications.failure_alert_to`
- at least one owner scope:
  - `rep.email`
  - `rep.owner_emails`
  - `rep.owner_names`

## Recommended fields

- `defaults.lookback_hours`
- `matching.internal_domains`
- `matching.ignored_domains`
- `matching.ignored_company_keywords`

## Notes

- `matching.internal_domains` should include `folloze.com`.
- `rep.email` remains the default single-owner scope and is also used as the fallback primary rep identity for summary metadata.
- `rep.owner_emails` lets the helper review all open opportunities for multiple Salesforce owners by email.
- `rep.owner_names` is a safer fallback when you know the owner names but do not want to guess their email addresses.
- If both owner emails and names are present, the helper matches either and de-duplicates results.
- `notifications.failure_alert_to` is the address the Gmail connector should use for failure alerts.
- `ignored_domains` and `ignored_company_keywords` support the unmatched-activity pass so partner or consultant meetings do not look like create candidates by default.
