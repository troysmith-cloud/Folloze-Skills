# Program KPI Waterfall Board Model

## Standard Benchmarks

| Stage | Standard |
| --- | ---: |
| Accounts in market | 100% |
| Engaged accounts | 30% |
| Sales meetings scheduled | 10% |
| Pipeline opportunities | 50% |
| Closed deals | 30% |

## Core Calculations

- accounts in market = accounts targeted x selected in-market %
- engaged accounts = accounts in market x selected engage %
- sales meetings = engaged accounts x selected meeting %
- pipeline opportunities = sales meetings x selected pipeline %
- closed deals = pipeline opportunities x selected close %
- pipeline goal = average deal size x pipeline opportunities
- bookings = average deal size x closed deals

## One-Year Quarterly Plan

Each program belongs to one quarter: `Q1`, `Q2`, `Q3`, or `Q4`.

The board should show:

- program-level waterfall logic inside the selected quarter
- quarterly rollups for Q1, Q2, Q3, and Q4
- cumulative quarter-to-date totals for Q1 YTD, Q2 YTD, Q3 YTD, and Q4 YTD
- a full-year total row
- overflow-safe number formatting so large values stay inside their boxes

## Required Interactions

- add program
- duplicate active program
- delete any program, including the last one
- switch active program
- assign a program to Q1, Q2, Q3, or Q4
- choose customer success manager: `Meghan Richardson`, `Matthew Brown`, `Steven Nguyen`, or `Flor Estrada`
- update details and assumptions
- switch benchmark mode between Standard and Custom
- edit custom benchmark values
- output to slides by exporting the current planner state and opening the generated Google Slides deck URL
- output to sheets by posting the current planner state to the sheet-builder web app, copying the JDP template workbook, and opening the generated customer workbook populated from the board data

Each interaction should either track `cta_click` when it is a CTA/button or a descriptive custom event such as `model_update`, `tab-switch`, `program_add`, `program_remove`, `slides_export`, or `sheets_export`.

## Customer Name Personalization

Before saving a Folloze board, ask for the customer's name if it is not already provided. Keep the reusable template hero neutral, and use the customer name for exports plus the customer name/logo placeholder when creating a customer-specific derivative.

## Program Type Options

- 1:1 ABM
- 1:few ABM
- 1:many ABM
- Executive program
- Event follow-up
- Digital deal room
- Renewal / QBR
- Customer expansion
- Web Engager Program
- Resource Center
- Enablement Program
- Newsletter
- Test
- New Product Launch
- Content Hub
- Article Hub
- Other
