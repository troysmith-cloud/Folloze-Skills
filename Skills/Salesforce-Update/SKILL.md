---
name: Salesforce-Update
description: Manually reconcile Salesforce open opportunities from Gmail, Google Calendar, and Granola evidence, then write validated updates through Salesforce CLI-backed auth with local logging. Use when a rep wants to update stage, next steps, amount, summary, red flags, contact roles, and MEDDPICC fields over the last 72 hours, last week, or all open deals.
---

# Salesforce Update

This skill is manual-only.
Use Gmail, Google Calendar, and Granola connectors for read-side evidence and the local helper at `scripts/salesforce_update.py` for Salesforce candidate export, plan validation, and writes.

Do not silently create new opportunities.
If unmatched activity looks like a new deal, present it as a create candidate and ask the rep before any new opportunity is created.

## Prerequisites

1. Confirm local config and Salesforce auth
- Run: `python3 scripts/salesforce_update.py check-deps --json`
- Config path defaults to `~/.config/salesforce-update/config.json`
- Read `references/config.md` before creating or editing config.

2. Confirm connectors are available for this session
- Gmail connector
- Google Calendar connector
- Granola connector

## Workflow

1. Initialize a run
- Default 72h run: `python3 scripts/salesforce_update.py init-run --json`
- Last week: `python3 scripts/salesforce_update.py init-run --lookback-hours 168 --json`
- All open: `python3 scripts/salesforce_update.py init-run --all-open --json`

2. Read the generated run files
- `context.json` contains:
  - candidate opportunities for the chosen lookback
  - a lightweight all-open index for unmatched-activity matching
  - current contact roles
  - relevant field metadata including stage and competition picklist values
- `plan.json` is the file to fill before applying updates.

3. Review candidate opportunities first
- Start from candidate opps, not from raw inbox/calendar activity.
- Use the all-open index only for the unmatched hybrid pass.

4. Gather evidence with connectors
- Gmail:
  - Search inbox and sent mail for matching contacts, domains, and account names.
  - Include same-day outbound email context in the summary block.
- Google Calendar:
  - Read matching events and attendees.
  - External attendees are eligible for contact creation and opportunity contact-role association.
- Granola:
  - Read meeting notes and summaries for the same opportunity.
  - Granola is a dependency for this skill; retry once on transient connector failures before falling back to email/calendar-only reasoning.

5. Apply stage and field rules
- Stage flow is forward-only.
- Default start stage is `Meeting Booked`.
- First external call completed: move to `S0`.
- `S0 -> Identify` when there is a continuation signal.
- `Identify -> Discovery` when meaningful buying motion exists, especially if two or more are true:
  - named project or named program
  - identified budget or pricing discussion
  - competitor or incumbent mentioned
  - multiple external attendees
  - clear follow-up meeting scheduled
  - manager or broader team expected on the next call
- `Discovery -> Solution Development` only after the second call has actually happened.
- `Solution Development -> Proposal` when pricing/proposal/order-form documentation is shared or actively being prepared.
- `Proposal -> Validation` when procurement, legal, privacy, security, or process review is underway before final contract agreement.
  - before moving into `Validation` or later, confirm `Customer_Executive_Sponsor__c` is identified and populated on the opportunity
- `Validation -> Contract` when the final contract is agreed and sent for signature.
- Do not move stages backward.
- Do not auto-create `Closed Won`, `Closed Lost`, or new opportunities in this skill.

6. Apply write rules
- Do not write standard `NextStep`.
- Write the custom MEDDPICC next-step field `Next_step__c` only.
- `Amount`:
  - early-stage call-note numbers are allowed
  - email-shared numbers trump call-note numbers
  - ambiguous numbers should be left unchanged
- `Summary__c`:
  - prepend newest dated block at the top
  - preserve older blocks below
  - include date, rep initials, and whether the update came from call, email, or both
  - same-day updates may exceed three sentences if meaningful movement happened
- `Redflag_s__c`:
  - store red flags here
  - do not duplicate red-flag text into the summary unless useful for human readability
- MEDDPICC text fields:
  - append instead of overwrite when new evidence exists
- `Metrics__c` can be updated when the call surfaces concrete scale or volume numbers.
- `Next_Call_Date__c` should be set when a clear follow-up meeting is already booked.
- MEDDPICC contact lookup fields:
  - must point to external contacts only
  - `Internal_Executive_Sponsor__c` is intentionally out of scope for v1
- `Customer_Executive_Sponsor__c`:
  - is a customer-side external contact lookup
  - must be set before the skill moves an opportunity from below `Validation` into `Validation` or `Contract`
- `Competition__c`:
  - use the exact picklist value when matched
  - otherwise set `Other`
- Save regular opportunity/detail fields separately from MEDDPICC/custom fields.
- If Salesforce requires in-order stage advancement, the helper will walk forward through the intermediate stages automatically before applying the rest of the detail save group.
- Treat `StageName`, `Amount`, `Summary__c`, and `Customer_Executive_Sponsor__c` as the regular/detail save group.
- Treat `Next_step__c`, `Next_Call_Date__c`, MEDDPICC text fields, MEDDPICC lookup fields, `Competition__c`, `Redflag_s__c`, and `What_s_New_Changed__c` fields as the MEDDPICC/custom save group.
- Contacts and contact roles:
  - exclude internal `@folloze.com` attendees
  - when an external attendee is missing in Salesforce, create a `Contact` on the opportunity account
  - set new contact `OwnerId` to the opportunity owner
  - attach the external contact to the opportunity with an `OpportunityContactRole`
  - skip duplicate opportunity-contact-role creation

7. Handle unmatched external activity
- After matched-opportunity updates are planned, review unmatched email/calendar/Granola activity.
- Classify unmatched activity into:
  - ignore
  - review only
  - create candidate
- Never auto-create an opportunity.
- Present create candidates to the rep and ask whether a new opportunity should be created.

8. Validate the plan before writing
- Read `references/plan-schema.md`
- Fill `plan.json`
- Validate: `python3 scripts/salesforce_update.py validate-plan --run-dir <run_dir> --json`

9. Apply the plan
- Apply: `python3 scripts/salesforce_update.py apply-plan --run-dir <run_dir> --json`
- The helper writes local logs into the run directory and returns a concise summary payload.

10. On failure
- Use the Gmail connector to email the configured failure recipient from the authenticated Gmail account.
- Include:
  - run id
  - failing step
  - error summary
  - log path

11. End-of-run response
- Always return a short summary of which opportunities were updated and why.
- Format should stay brief:
  - `Asana -> moved to Contract, updated signer context, prepended summary`
  - `Zilliant -> no stage movement, prepended red flag and summary`

## Guardrails

- Prefer candidate opportunities over inbox-first scanning.
- Treat the all-open index as a matching aid, not as permission to update everything.
- Do not overwrite append-style MEDDPICC text fields.
- Do not assign internal contacts to external MEDDPICC lookup fields.
- Do not create contacts for internal Folloze attendees.
- Do not proceed with plan application if validation errors exist.
