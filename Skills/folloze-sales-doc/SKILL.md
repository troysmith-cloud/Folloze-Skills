---
name: folloze-sales-doc
description: "Use this skill to create branded Folloze sales preparation and customer lifecycle documents. Trigger whenever a Folloze team member asks for a call prep doc, discovery prep, follow-up summary, QBR doc, onboarding plan, renewal prep, champion brief, stakeholder map, or any structured document for a prospect or customer touchpoint — pre-sale through post-sale. Also trigger when someone says 'prep me for a call', 'build me a doc for this account', 'summarize the account', 'put together a brief', or 'create a [lifecycle stage] doc for [company]'. Always use this skill for any Folloze account documentation regardless of lifecycle stage."
---

# Folloze Sales & Customer Lifecycle Doc Skill

This skill produces branded, professional Word (.docx) documents for every stage of the Folloze customer lifecycle — from pre-sale discovery prep through post-sale QBRs and renewals. All docs share the same visual design system (navy/teal brand colors, structured tables, callout boxes) established in the Tailscale discovery prep doc.

## Quick Reference

| Lifecycle Stage | Doc Type | Key Sections |
|---|---|---|
| Pre-Sale | Discovery Prep | Company snapshot, contacts, pain mapping, pitch angles, discovery Qs |
| Pre-Sale | Champion Brief | Champion profile, org map, internal politics, talking points |
| Active Deal | Stakeholder Map | Buyer roles, influence, objections per person |
| Active Deal | Proposal Summary | Value prop mapped to pain, ROI framing, next steps |
| Post-Sale | Onboarding Plan | Goals, milestones, team contacts, success metrics |
| Post-Sale | QBR / Business Review | Usage stats, wins, gaps, roadmap alignment |
| Post-Sale | Renewal Prep | Health score, risks, expansion opportunities, renewal narrative |
| Any Stage | Account Summary | Snapshot of where the account stands right now |

---

## Step 1 — Identify the Doc Type and Gather Inputs

Ask the user (or infer from context) the following:

1. **Lifecycle stage** — pre-sale, active deal, or post-sale?
2. **Doc type** — which of the above types fits best?
3. **Account info** — company name, contact names/titles, any call notes or CRM data provided
4. **What do they know?** — any intel already in the conversation (call notes, prior emails, research)

If the user provides call notes or raw information, extract structured content from them. If they provide a company name but no research, use web search to gather company snapshot data before building the doc.

---

## Step 2 — Research (if needed)

For pre-sale docs, always research:
- Company size, funding, stage, revenue signals
- Marketing team structure and key contacts (LinkedIn, Crunchbase, job postings)
- Current martech stack (job descriptions are a goldmine)
- Recent company news or growth signals
- ABM maturity signals (are they hiring ABM? what tools do they mention?)

For post-sale docs, pull from:
- Call notes and CRM data provided by the user
- Any product usage stats shared
- Prior correspondence in the conversation

---

## Step 3 — Build the Document

Use the `docx` npm library. Always follow the **Folloze Design System** defined in `references/design-system.md`.

### Document Structure by Type

#### Discovery / Call Prep Doc
1. Header block (company name, doc type, date, "Selling: Folloze")
2. Company Snapshot (two-col table)
3. Growth Signals / Why Now (dark callout box)
4. Marketing Team & Key Contacts (person cards)
5. Their Situation Today (callout box with current pain/stack)
6. Folloze Pitch Angles (numbered, mapped to their specific pain)
7. Discovery Questions (grouped by theme)
8. Likely Objections & Responses (two-col table)
9. Call Strategy & Goals
10. Quick Reference Cheat Sheet (two-col table)

#### Champion Brief
1. Header block
2. Champion Profile (person card with background, tenure, priorities)
3. Their Internal Goals & KPIs
4. Organizational Map (who they report to, who influences them)
5. Internal Dynamics (allies, skeptics, budget holders)
6. How to Arm Them (talking points, materials to share)
7. Risk Factors
8. Recommended Next Actions

#### Stakeholder Map
1. Header block
2. Account Overview
3. Stakeholder Cards (one per key contact — role, influence level, stance on Folloze, key concern)
4. Decision-Making Process
5. Engagement Strategy per Stakeholder
6. Risk & Mitigation

#### Onboarding Plan
1. Header block
2. Account Goals (what success looks like for them)
3. Folloze Team Contacts
4. Customer Team Contacts
5. Onboarding Milestones (30/60/90 day table)
6. Success Metrics
7. Known Risks & Mitigation
8. Next Scheduled Touchpoints

#### QBR / Business Review
1. Header block
2. Executive Summary
3. Usage & Engagement Highlights (key stats in callout box)
4. Wins Since Last Review
5. Gaps / Areas to Improve
6. Roadmap Alignment (what's coming that matters to them)
7. Mutual Action Plan
8. Next Steps

#### Renewal Prep
1. Header block
2. Account Health Snapshot (two-col table: green/amber/red signals)
3. Usage Trends
4. Relationship Map (champion strength, exec access)
5. Risks & Mitigation
6. Expansion Opportunities
7. Renewal Narrative (the story to tell)
8. Competitive Threats
9. Recommended Actions & Timeline

---

## Step 4 — Code Pattern

Always install and use the `docx` npm package. Save output to `/mnt/user-data/outputs/`.

```javascript
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
        LevelFormat } = require('docx');
const fs = require('fs');
```

Read `references/design-system.md` for the full set of reusable component functions (header block, callout box, person card, two-col table, h1, h2, bullet, etc.) — copy them into the script verbatim. Do not reinvent the design components.

File naming convention:
```
[Company]_[DocType]_Folloze.docx
e.g. Tailscale_DiscoveryPrep_Folloze.docx
     Okta_RenewalPrep_Folloze.docx
     Salesforce_QBR_Folloze.docx
```

---

## Step 5 — Validate and Present

After generating:
1. Run the file and confirm it writes successfully
2. Use `present_files` to share the `.docx` with the user
3. Give a 2-3 sentence summary of what's inside and what to customize before the call/meeting

---

## Critical Rules

- **Always use the design system** from `references/design-system.md` — never invent new color schemes or layouts
- **Never make up contacts** — if you can't find a person's name, use a placeholder like `[ABM Manager — confirm name]`
- **Flag assumptions** — if you assumed something (e.g. their stack, their team size), note it in the doc with `[Verify: ...]`
- **Tailor pitch angles to their actual pain** — generic Folloze value props are not enough; map each angle to something specific from research or call notes
- **Keep cheat sheets truly concise** — the quick reference table at the end should be scannable in 30 seconds
