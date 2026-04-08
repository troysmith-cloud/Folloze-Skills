Use the config file at `~/.config/salesforce-update/config.json` unless `SALESFORCE_UPDATE_CONFIG` points elsewhere.

Copy the example from `/Users/treyharnden/.codex/skills/Salesforce-Update/references/config.example.json`.

## Required fields

- `salesforce.org_alias`
- `rep.email`
- `rep.initials`
- `notifications.failure_alert_to`

## Recommended fields

- `defaults.lookback_hours`
- `matching.internal_domains`
- `matching.ignored_domains`
- `matching.ignored_company_keywords`

## Notes

- `matching.internal_domains` should include `folloze.com`.
- `rep.email` is used to scope default opportunity candidate selection to the rep's open opportunities.
- `notifications.failure_alert_to` is the address the Gmail connector should use for failure alerts.
- `ignored_domains` and `ignored_company_keywords` support the unmatched-activity pass so partner or consultant meetings do not look like create candidates by default.
