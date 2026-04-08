The helper expects a `plan.json` file inside the run directory.

It is created automatically by `init-run`.

## Top-level shape

```json
{
  "run_id": "20260327T213000Z-abc123",
  "notes": "optional run notes",
  "updates": [],
  "create_candidates": []
}
```

## Update object

```json
{
  "opportunity_id": "006xxxxxxxxxxxx",
  "summary_reason": "Moved to Discovery after first call showed named initiative and follow-up meeting.",
  "set_fields": {
    "StageName": "Discovery",
    "Next_step__c": "demo with larger team",
    "Amount": 40000,
    "Competition__c": "Other",
    "Next_Call_Date__c": "2026-03-30",
    "What_s_New_Changed__c": "Second-call demo scheduled with analytics deep dive."
  },
  "merge_fields": {
    "Summary__c": {
      "mode": "prepend",
      "value": "3/27/26 - TH - Call + email update. Named project, broader team coming next call, and $40k price point discussed. Granola: https://granola.app/example"
    },
    "Redflag_s__c": {
      "mode": "prepend",
      "value": "3/27/26 - Prospect no-showed and did not respond before meeting."
    },
    "Metrics__c": {
      "mode": "append",
      "value": "JP Morgan uses Neo4j in 16 of 800 technology products."
    },
    "Decision_Criteria__c": {
      "mode": "append",
      "value": "Needs supported enterprise AI workflow, not local open-source tooling."
    }
  },
  "contact_lookup_updates": {
    "Customer_Executive_Sponsor__c": "vp@acme.com",
    "Champion__c": "melissa.bradbury@zilliant.com",
    "Decision_Maker__c": "jane@acme.com"
  },
  "contacts_to_ensure": [
    {
      "email": "jane@acme.com",
      "display_name": "Jane Doe"
    }
  ],
  "contact_roles_to_ensure": [
    {
      "email": "jane@acme.com",
      "is_primary": false,
      "role": ""
    }
  ]
}
```

## Validation rules

- `StageName` must be forward-only and must stay within the active pipeline supported by the helper.
- `Summary__c` may be written either through `merge_fields` for prepend/append behavior or through `set_fields` when you need to replace an inaccurate existing summary block instead of duplicating it.
- Standard `NextStep` writes are disabled. If a plan still includes `NextStep`, the helper will ignore it and remap the value to `Next_step__c` when possible.
- `Next_Call_Date__c` must be supplied as an ISO date string like `2026-03-30`.
- `Competition__c` must match an actual Salesforce picklist value; otherwise use `Other`.
- `contact_lookup_updates` accepts emails, not contact ids. The helper resolves or creates contacts before writing the lookup field.
- Moving an opportunity from below `Validation` into `Validation` or `Contract` requires either an existing `Customer_Executive_Sponsor__c` or `contact_lookup_updates.Customer_Executive_Sponsor__c` in the same update.
- `merge_fields` only supports:
  - `prepend`
  - `append`
- `contacts_to_ensure` and `contact_roles_to_ensure` must be external contacts only.
- `create_candidates` is advisory only. The helper does not create opportunities from that section.
- The helper writes regular/detail fields and MEDDPICC/custom fields in separate Salesforce save calls.
- `Customer_Executive_Sponsor__c` is treated as a regular/detail save-group field even though it is a custom lookup.
- When a valid forward stage target skips intermediate stages, the helper advances the opportunity through the missing stages automatically during apply.

## Apply flow

1. Edit `plan.json`
2. Validate with `validate-plan`
3. Apply with `apply-plan`
4. Read `apply-result.json` in the run directory for the final local log
