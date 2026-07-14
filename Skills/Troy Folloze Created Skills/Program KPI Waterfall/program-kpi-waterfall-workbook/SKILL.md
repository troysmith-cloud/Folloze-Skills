---
name: program-kpi-waterfall-workbook
description: Build Excel or Google Sheets-ready program KPI waterfall workbooks for customer program planning. Use when a user asks to create, update, or replicate a spreadsheet/form that lets customers add many program sections, enter program details, choose standard or custom benchmarks, and auto-calculate account-to-pipeline waterfall metrics, pipeline goal, and bookings.
---

# Program KPI Waterfall Workbook

## Purpose

Create a customer-facing workbook that turns program assumptions into waterfall calculations:

- quarter, program type, name, segment, channels, content, and notes
- program year dropdown values `2026`, `2027`, `2028`, and `2029`
- projected live boards and published boards by program
- actual engaged accounts, meetings, pipeline opportunities, closed deals, pipeline, and bookings
- standard benchmark chain: `100% -> 30% -> 10% -> 50% -> 30%`
- optional custom benchmark overrides per program
- calculated accounts in market, engaged accounts, sales meetings, pipeline opportunities, closed deals, pipeline goal, and bookings
- quarterly and full-year summaries for a one-year plan
- quarter summaries for projected live boards, published boards, actual meetings, actual pipeline, and actual bookings
- as many program rows/sections as needed

Current program type dropdown values:

- `1:1 ABM`
- `1:few ABM`
- `1:many ABM`
- `Executive program`
- `Event follow-up`
- `Digital deal room`
- `Renewal / QBR`
- `Customer expansion`
- `Web Engager Program`
- `Resource Center`
- `Enablement Program`
- `Newsletter`
- `Test`
- `New Product Launch`
- `Content Hub`
- `Article Hub`
- `Other`

## Default Workflow

1. Use `scripts/build_program_kpi_workbook.py` to create a local `.xlsx` whenever the user asks for an Excel file or a spreadsheet artifact.
2. If the destination is Google Sheets, create the `.xlsx` first, then import it as a native Google Sheet using the Google Drive/Sheets workflow.
3. Preserve the model structure unless the user asks to change the funnel:
   - accounts targeted
   - accounts in market
   - engaged accounts
   - sales meetings
   - pipeline opportunities
   - closed deals
   - average deal size
   - pipeline goal
   - bookings
4. Include the first replaceable example row so the form is immediately understandable.
5. Make the customer-editable fields visually distinct from calculated outputs.
6. Verify formulas by opening or inspecting the workbook after creation.

## Builder Script

Run:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/program-kpi-waterfall-workbook/scripts/build_program_kpi_workbook.py" \
  --output /absolute/path/program-kpi-waterfall.xlsx
```

Optional inputs:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/program-kpi-waterfall-workbook/scripts/build_program_kpi_workbook.py" \
  --output /absolute/path/program-kpi-waterfall.xlsx \
  --programs /absolute/path/programs.json \
  --rows 250
```

If `python3` cannot import `openpyxl`, call `codex_app.load_workspace_dependencies` to locate the current Python runtime with spreadsheet libraries and rerun the installed-skill-relative script path with that runtime.

`--programs` accepts a JSON array of objects with keys:

```json
[
  {
    "program_type": "1:1 ABM",
    "quarter": "Q1",
    "program_year": "2026",
    "program_name": "Strategic account motion",
    "segment": "Enterprise target accounts",
    "channels": "Display ads + email + sales outreach",
    "content": "Thought leadership, solution proof, case studies",
    "notes": "Planning assumption",
    "benchmark_mode": "Standard",
    "accounts_targeted": 1200,
    "avg_deal_size": 5000000,
    "projected_live_boards": 1,
    "published_boards": 0,
    "actual_engaged": 0,
    "actual_meetings": 0,
    "actual_pipeline_opps": 0,
    "actual_closed_deals": 0,
    "actual_pipeline": 0,
    "actual_bookings": 0,
    "custom_in_market": 1,
    "custom_engage": 0.3,
    "custom_meeting": 0.1,
    "custom_pipeline": 0.5,
    "custom_close": 0.3
  }
]
```

Use decimal percentages in JSON: `0.3` for `30%`.

## Workbook Shape

The builder creates:

- `Customer Program Form`: row-based form with dropdowns and formulas, designed to behave like a `+ Program Type` control by filling the next blank row.
- `Waterfall Sections`: printable/shareable section view for every prepared program row.
- `Quarter Summary`: Q1, Q2, Q3, Q4, and full-year rollups.
- `Benchmarks`: reference tab with the standard benchmark chain and metric definitions.

## Formula Rules

Use the same row-level logic as the original model:

- selected benchmark = custom value when `Benchmark Mode = Custom` and the custom cell is filled, otherwise the standard benchmark
- published board attainment = published boards / projected live boards
- accounts in market = accounts targeted x selected in-market %
- engaged accounts = accounts in market x selected engage %
- sales meetings = engaged accounts x selected meeting %
- pipeline opportunities = sales meetings x selected pipeline %
- closed deals = pipeline opportunities x selected close %
- pipeline goal = average deal size x pipeline opportunities
- bookings = average deal size x closed deals
- pipeline attainment = actual pipeline / projected pipeline goal
- bookings attainment = actual bookings / projected bookings

## Quality Checks

Before returning:

- confirm the workbook exists at the requested path
- confirm the first program row calculates to the expected sample values when using defaults: `1,200 -> 1,200 -> 360 -> 36 -> 18 -> 5`, `$90M` pipeline, `$25M` bookings
- confirm the first program row appears in `Q1` and the `Quarter Summary` tab rolls it into the full-year total
- confirm `Program Year`, projected live boards, actual fields, and attainment columns appear after `Quarter`
- if imported into Google Sheets, read back the `Customer Program Form` and `Waterfall Sections` tabs after import
- mention any verification that could not be completed
