---
name: "linkedin-operator-content"
description: "Use when the user wants LinkedIn content ideas, post outlines, article drafts, or recurring content generation for a growth-oriented operator voice across martech, SaaS, startups, customer success, leadership, AI, recruiting, professional services, account management, support, net revenue retention, and upsells. Also use when the output should be delivered through Slack and/or email."
---

# LinkedIn Operator Content

Use this skill for two related workflows:

1. Generate LinkedIn ideas and outlines on a recurring or one-off basis.
2. Turn a selected idea into a polished LinkedIn article or post draft.

## Voice and positioning

Write from the perspective of a practical, commercially minded operator.

- Core domains: martech, SaaS, startups, customer success, leadership, AI, personal brand, recruiting, professional services, account management, support.
- Business lens: NRR, retention, expansion, upsells, customer value, team performance, service delivery, and revenue impact.
- Tone: specific, credible, human, operator-led, and useful.
- Avoid: generic inspiration, engagement bait, empty platitudes, and obvious AI phrasing.

## Idea generation workflow

When the user asks for ideas, default to:

- 7 LinkedIn ideas
- A working title for each
- A strong opening hook
- The core point
- Why it would resonate on LinkedIn
- The best format: story post, contrarian take, lesson learned, framework, recruiting insight, customer growth insight, or AI/operator perspective
- A short outline with 3 to 5 bullets

Always include a mix across:

- revenue growth and expansion
- customer retention and NRR
- team leadership and hiring
- service delivery, support, and account management
- AI for go-to-market and customer teams

End with the top 2 recommendations for today and one sentence on why each is likely to perform well.

## Drafting workflow

When the user picks an idea, produce:

- Title
- Strong opening hook
- Full LinkedIn article or post draft
- Clear closing takeaway
- 3 alternate hooks

Keep the structure tight, practical, and experience-driven. Tie the piece back to leadership, customers, growth, or commercial outcomes whenever it fits naturally.

## Delivery workflow

If the user asks for delivery through tools or automations:

- Send the result as a Slack DM when requested and the Slack connector is available.
- Send the result by email when requested and the email destination is known.
- Prefer the bundled script `scripts/send_linkedin_email.sh` for real email delivery when `gws` is available and authenticated.
- Write the final email body to a temporary text file, then call `scripts/send_linkedin_email.sh <to_email> <subject> <body_file>`.
- If the user asks to test the workflow, use the same real delivery path instead of only showing the output in chat.
- If an exact email address is missing, use the user-provided label if that is enough for the active connector; otherwise ask for the address.
- Format delivery outputs for easy scanning with short headings and compact sections.

## Quality bar

- Favor concrete observations over broad advice.
- Make the content sound like it came from a leader who owns outcomes.
- Prefer lessons, frameworks, and operating principles over motivational language.
- Keep hooks sharp but believable.
- Do not force every topic into AI; use it where it adds genuine insight.
