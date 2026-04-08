---
name: "daily-email-summary-delivery"
description: "Use when a recurring or test workflow should review recent Gmail inbox activity, produce a concise action-oriented summary, send it by real email, send it as a Slack DM, and finish with exactly one inbox item."
---

# Daily Email Summary Delivery

Use this skill for recurring or test email-summary runs that must both analyze inbox activity and deliver the result through tools.

## Workflow

1. Use the Gmail inbox triage workflow to inspect recent inbox activity and identify the most important threads since the last business-day run.
2. Produce a concise summary grouped into:
   - Urgent
   - Needs reply soon
   - Waiting
   - FYI
3. For each important thread include:
   - sender
   - subject
   - why it matters
   - recommended response action
4. Format the final summary so it is easy to scan in both email and Slack.
5. For manual test runs, do the same full analysis workflow as a scheduled run. Do not send a synthetic delivery-only message and do not skip the review/summarization step.

## Delivery workflow

- Send the final summary as a Slack DM to Troy Smith using Slack user ID `U08FTRBFX1R`.
- Use the Slack connector to actually send the DM. Do not merely mention that Slack delivery should happen.
- Send the final summary by real email to `Troy.smith@folloze.com`.
- Prefer the bundled script `scripts/send_daily_email_summary_email.sh` for email delivery when `gws` is available and authenticated.
- Write the email body to a temporary text file, then call:
  `scripts/send_daily_email_summary_email.sh <to_email> <subject> <body_file>`
- Use the same real delivery path for scheduled runs and manual test runs.
- Generate the summary first, then deliver the identical summary to Slack and email.

## Subject line

Use:

- `Daily Email Summary - YYYY-MM-DD` for normal runs
- `Daily Email Summary Test - YYYY-MM-DD` for explicit test runs

## Output requirements

- The assistant should still present a short final answer for the run.
- End with exactly one `::inbox-item` directive.
- The inbox title should make clear whether delivery succeeded or what blocked it.
- The final answer should briefly confirm whether Slack delivery succeeded and whether email delivery succeeded.

## Failure handling

- If Gmail inbox analysis fails, say so clearly and still end with one inbox item.
- If delivery fails after the summary is generated, report which step failed: Gmail, Slack, or both.
- Do not silently skip delivery.
