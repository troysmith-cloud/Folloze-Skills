---
name: account-org-chart
description: Build a polished, color-coded org structure workbook for a customer or prospect account with tabs for Marketing, Sales, IT, Digital, AI Titles, Strategy Titles, and Product Marketing stakeholders, then deliver it as a native Google Sheet in the company's Google Drive folder and open the final URL. Triggers when someone says "build me an org chart for [company]", "make an org structure for [company]", "do the same for [company]" (referencing a prior org chart), "create an org sheet for [company]", "update this org chart", or similar. Also triggers when the user provides meeting notes, Slack channel context, or account intel and asks to turn it into a structured org view. Also triggers when the user uploads an existing org chart xlsx and asks to update or enrich it with new contacts. Always use this skill when the task is to compile people, roles, reporting lines, LinkedIn profiles, and Folloze relationship context for a named account — even if they use casual phrasing like "do what you did for Autodesk but for Okta."
---

# Account Org Chart Skill

Produce a professional, color-coded org structure workbook for a named B2B account. Build the workbook locally as `.xlsx`, then upload and convert it into a **native Google Sheet in the correct company folder in Google Drive**, and open the final Sheet URL in the browser. The workbook contains **seven tabs**: Marketing Org, Sales Org, IT Org, Digital Org, AI Titles, Strategy Titles, Product Marketing Org — each with the same column structure and styling. Every tab includes reporting lines, LinkedIn profiles, tenure/notes, Folloze relationship context, a **Folloze Team Member to Follow Up** column, and an **Outreach Messaging** column pre-populated with persona-specific messaging.

This skill covers two modes:
- **Create**: Build a new org chart from scratch for a named account
- **Update**: Enrich an existing org chart xlsx by adding new contacts to sparse tabs, patching stale data, and preserving all existing rows and formatting

---

## Workflow

### 0. Detect Mode: Create vs. Update

**If the user uploads an existing xlsx:**
- Read all sheets with pandas: `pd.read_excel(path, sheet_name=None)`
- Identify which tabs are sparse (placeholder rows, "No contacts identified", or fewer than 3 real contacts)
- Run intel gathering (Step 1) focused on the sparse tabs
- Use `load_workbook()` + `insert_rows()` to add new contacts above any placeholder rows — do NOT rebuild the file from scratch
- Preserve all existing rows, styling, and formatting
- See **Section 4b — Updating an Existing File** for the exact pattern

**If the user provides an existing Google Sheet URL instead of an xlsx:**
- Export the sheet to `.xlsx`, patch it locally, then re-upload it as a native Google Sheet back into the correct company folder
- Preserve the existing seven-tab layout and styling as closely as the export/import cycle allows

**If no file is uploaded:** proceed with full creation (Steps 1–4a).

---

### 1. Gather Intel (run all sources in parallel)

**a) Slack channel search**
- Search for a channel matching the account name (e.g., `#okta`, `#salesforce`)
- Read full channel history (`slack_read_channel`, limit 100)
- If pagination cursor is returned, read the next page too (limit 100 again) to capture older messages
- Extract: names, titles, emails, org changes, departures, LinkedIn links, relationship notes, Folloze team ownership signals

**b) Google Drive search** (if connected)
- Search for account-related docs, decks, or prep notes
- Fetch relevant files for additional people intel

**b2) Resolve the target Google Drive folder early**
- The final deliverable must live in the company's Drive folder as a native Google Sheet
- Preferred folder resolution order:
  1. Exact folder-name match for the company
  2. Parent folder of the most recent `"[Company] ... Deal Notes"` Google Doc, but only if that parent folder also looks company-specific
  3. Folder-name contains the company
  4. Last-resort fallback to the deal-notes parent even if the folder name is generic
- If multiple plausible folders exist, pick the one with the freshest account artifacts and note the folder URL you used in the final summary

**c) Web search — run one search per org**
- `"[Company] marketing leadership"`
- `"[Company] sales leadership OR revenue operations"`
- `"[Company] CIO OR IT leadership OR enterprise technology"`
- `"[Company] digital experience OR digital transformation leadership"`
- `"[Company] AI OR artificial intelligence strategy leadership"`
- `"[Company] strategy OR corporate strategy OR chief of staff"`
- `"[Company] product marketing leadership"`

**d) Apollo MCP — use `apollo_mixed_people_api_search` per tab (primary people source)**

Apollo is the primary enrichment engine. Use `apollo_mixed_people_api_search` (NOT `apollo_contacts_search`) with `q_organization_domains_list` to search by company domain — this gives richer results than name-based search.

For each tab, use these parameters:

| Tab | `person_titles` keywords | `person_seniorities` |
|-----|--------------------------|----------------------|
| Marketing Org | `"CMO", "VP Marketing", "Head of Marketing", "ABM", "Marketing Operations", "Demand Gen", "Field Marketing", "Content Marketing", "Brand"` | `["vp", "c_suite", "director", "manager"]` |
| Sales Org | `"CRO", "VP Sales", "Revenue Operations", "Sales Enablement", "Sales Director", "VP Revenue", "Head of Sales", "GTM Enablement"` | `["vp", "c_suite", "director"]` |
| IT Org | `"CIO", "CTO", "VP IT", "Enterprise Architect", "IT Director", "Field CTO", "Head of Engineering"` | `["vp", "c_suite", "director"]` |
| Digital Org | `"CDO", "VP Digital", "Head of Digital", "Digital Experience", "UX", "MarTech", "Web Strategy", "Digital Analytics"` | `["vp", "c_suite", "director"]` |
| AI Titles | `"Chief AI Officer", "VP AI", "Head of AI", "AI Strategy", "Machine Learning", "AI Transformation", "Marketing AI Strategy"` | `["vp", "c_suite", "director"]` |
| Strategy Titles | `"Chief Strategy Officer", "VP Strategy", "Corporate Strategy", "Chief of Staff", "Strategic Planning", "GTM Strategy"` | `["vp", "c_suite", "director"]` |
| Product Marketing Org | `"VP Product Marketing", "Product Marketing Manager", "Solutions Marketing", "Go-to-Market", "Launch Manager", "AI Product Marketing"` | `["vp", "c_suite", "director", "manager"]` |

**Apollo search pattern (per tab):**
```python
apollo_mixed_people_api_search(
    q_organization_domains_list=["company.com"],
    person_titles=["<title keywords for this tab>"],
    person_seniorities=["vp", "c_suite", "director"],
    page=1,
    per_page=15
)
```

From each Apollo result, extract:
- `first_name`, `last_name_obfuscated` — use obfuscated form in the sheet until enriched
- `title` — job title
- `has_email` — flag; enrich with `apollo_people_match` if True and contact is high priority
- `organization.name` — confirm it matches the target account
- `seniority` — use to assign tier

**Apollo names are obfuscated in search results** (e.g., `"Sh***y"`). For Tier 1 and key Tier 2 contacts, run `apollo_people_match(id=apollo_id, domain="company.com")` to retrieve the full name and verified email. This consumes enrichment credits — prioritize execs and budget owners.

**e) Apollo `people_match` enrichment — unlock real names and emails**

After identifying high-priority contacts from search results, enrich them:
```python
apollo_people_match(
    id="<apollo_id_from_search>",
    domain="company.com"
)
```
This returns:
- `first_name` + `last_name` (full, unobfuscated)
- `email` + `email_status` (use "verified" status as ground truth)
- `employment_history` — use to add tenure context (start dates, prior roles at same company)
- `linkedin_url` — use if returned; otherwise construct best-guess

Write the verified email into the **Tenure / Notes** cell (e.g., `"Email: deepti.arora@okta.com (verified)"`).

**f) User-provided notes**
- Parse any pasted meeting notes, call notes, or raw intel
- Note which org each person belongs to

---

### 2. Compile the People List (per tab)

Merge all sources — Apollo, Slack, web search, Google Drive, user notes — into a unified list per tab. Deduplicate by name. If Apollo returns an email or LinkedIn URL that Slack or web search didn't have, use Apollo's data.

Use the same tier classification across all seven tabs:

| Tier | Examples |
|------|----------|
| Exec (Tier 1) | C-Suite, VP, SVP, EVP of the function |
| Director/Sr. Manager (Tier 2) | Sr. Director, Director, Head of |
| Manager/IC/Specialist (Tier 3) | Manager, Specialist, Analyst, Contractor |

For each person, capture all nine fields (maps to columns A–I):

| Field | Notes |
|-------|-------|
| **Name** | Full name if enriched; "First La***y" format if obfuscated and not yet enriched |
| **Title** | Exact if known, best guess otherwise |
| **Department / Focus Area** | e.g., "Revenue Ops", "AI Center of Excellence", "GTM Strategy" |
| **Reports To** | Append "(assumed)" if inferred |
| **Tenure / Notes** | Tenure, departures, contractor status, email if known, prior roles at company if relevant |
| **LinkedIn Profile** | Full URL from Apollo if available; construct `/in/firstname-lastname/` if not; flag as best-guess |
| **Relationship to Folloze** | Power user, budget owner, target, departed, etc. |
| **Folloze Team Member to Follow Up** | The Folloze AE, CSM, or SE who should own outreach — pull from Slack channel context, or leave as "TBD — assign before send" |
| **Outreach Messaging** | Pre-populated persona message — customize with name and company |

**Reporting line inference:** use explicit signals first; infer by seniority otherwise; always append "(assumed)."

---

### 3. Tab-Specific Role Guidance & Outreach Messaging Templates

For each tab, use the messaging template below as the base for the **Outreach Messaging** column. Keep it to 3–4 sentences max per cell.

#### TAB 1 — Marketing Org
**Who to include:** CMO, VP/SVP Marketing, Head of ABM, Marketing Ops, Campaign Managers, Field Marketers, Content, Brand, Demand Gen

**Outreach Messaging Template:**
> Hi {name} — teams like yours at {company} are using Folloze to launch AI-powered, personalized content destinations in hours instead of weeks. Whether it's ABM campaigns, field events, or pipeline acceleration plays, Folloze gives your marketers a no-code canvas to build and measure experiences that actually move deals. Would love to show you how [similar company] cut campaign launch time by 60%. Open to a quick look?

#### TAB 2 — Sales Org
**Who to include:** CRO, VP/SVP Sales, Regional Sales Directors, Sales Ops/Enablement, Revenue Ops, GTM Enablement, Partnerships

**Outreach Messaging Template:**
> Hi {name} — Folloze helps revenue teams at companies like {company} automatically trigger personalized digital sales rooms the moment a deal reaches a key CRM stage. No more waiting on marketing — reps get branded, buyer-specific destinations that surface intent signals in real time. This is how modern sales orgs cut time-to-close without adding headcount. Worth 20 minutes to see it live?

#### TAB 3 — IT Org
**Who to include:** CIO, CTO, VP IT, IT Directors, Enterprise Architects, Field CTO, Procurement/Vendor Management, Security/InfoSec

**Outreach Messaging Template:**
> Hi {name} — one of the biggest challenges IT leaders tell us about is GTM teams spinning up dozens of ungoverned tools for content and digital experiences. Folloze gives {company} a single, enterprise-grade platform that IT can control — SSO, data governance, security compliance — while Marketing and Sales self-serve campaigns. Happy to walk through the architecture — is that useful?

#### TAB 4 — Digital Org
**Who to include:** CDO, VP Digital, Head of Digital Experience, Web/UX leads, Digital Marketing, MarTech

**Outreach Messaging Template:**
> Hi {name} — digital leaders at companies like {company} are using Folloze to extend their web strategy with AI-personalized microsites and content hubs that no-code teams can build without dev resources. It connects to your existing MarTech stack and gives you behavioral analytics on every interaction. Open to seeing how this fits your roadmap?

#### TAB 5 — AI Titles
**Who to include:** Chief AI Officer, VP of AI, Head of AI Strategy, AI Center of Excellence leads, AI Program Managers, Marketing AI Strategy leads, AI Product Marketing leads

**Outreach Messaging Template:**
> Hi {name} — as {company} scales its AI transformation, one of the highest-leverage GTM applications is using AI to auto-generate personalized content destinations, recommend next-best assets, and eliminate manual campaign production. Folloze is doing this for enterprise teams today — AI-assisted content creation, dynamic personalization, all governed through one platform. Would love to show you how this fits your AI standardization strategy. Interested?

#### TAB 6 — Strategy Titles
**Who to include:** Chief Strategy Officer, VP Strategy, Head of Corporate Strategy, Chief of Staff (Sr. Director+), Strategic Planning Directors, GTM Strategy leads, SVP GTM Strategy & Operations

**Outreach Messaging Template:**
> Hi {name} — strategy leaders we work with are looking at Folloze as part of GTM modernization: standardizing how content experiences are created, measured, and iterated across Marketing, Sales, and Digital — powered by AI. The business case is clear: faster campaign cycles, lower cost per experience, and deal-level engagement data feeding directly into forecasting. Happy to share the framework — would that be a useful conversation?

#### TAB 7 — Product Marketing Org
**Who to include:** VP/Director Product Marketing, PMM Managers, Solutions Marketing, Competitive Intel, Go-to-Market leads, Launch Managers, AI Product Marketing leads, Chief of Staff to PMM

**Outreach Messaging Template:**
> Hi {name} — product marketers at companies like {company} are using Folloze to take a single launch asset and instantly generate tailored experiences for every segment — enterprise vs. mid-market, vertical by vertical — all from one platform. AI handles the variants; your team controls the narrative. It means launches reach buyers in context, not just inboxes. Worth a look?

---

### 4a. Build the Local Workbook (Create Mode)

Use `openpyxl`. Create **seven sheets**: Marketing Org, Sales Org, IT Org, Digital Org, AI Titles, Strategy Titles, Product Marketing Org.

#### Color Scheme
```python
HEADER_BG = "003366"   # Dark navy
TIER1_BG  = "00297A"   # Deep blue — Exec
TIER2_BG  = "CCE0F5"   # Light blue — Director
TIER3_BG  = "EAF4FF"   # Pale blue — IC/Manager
TIER1_FG  = "FFFFFF"
TIER2_FG  = "003366"
TIER3_FG  = "003366"
BORDER    = "0055B3"
```

Adapt accent to company brand (Okta `#0055B3`, Salesforce `#00A1E0`, Workday `#F07027`; default navy).

#### Column Layout (9 columns, A–I)
| Col | Header | Width |
|-----|--------|-------|
| A | Name | 22 |
| B | Title | 32 |
| C | Department / Focus Area | 28 |
| D | Reports To | 25 |
| E | Tenure / Notes | 38 |
| F | LinkedIn Profile | 42 |
| G | Relationship to Folloze | 32 |
| H | Folloze Team Member to Follow Up | 28 |
| I | Outreach Messaging | 55 |

#### Structure
- Row 1: Merged title banner — `"[Company] [Tab Name] — Folloze Account Intelligence"`
- Row 2: Bold white headers on dark navy
- Rows 3+: One person per row, color-coded by tier
- Freeze panes at A3; row height 60; wrap_text=True on all cells
- LinkedIn cells (col F): blue underline `color="0563C1"`
- Outreach Messaging cells (col I): italic font
- Legend 3 rows below last data row

#### Required Python pattern
```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = Workbook()
wb.remove(wb.active)

for tab_name, people in tabs:
    ws = wb.create_sheet(tab_name)
    build_sheet(ws, company_name, tab_name, people)

def fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)

def thin_border(color="0055B3"):
    s = Side(style='thin', color=color)
    return Border(left=s, right=s, top=s, bottom=s)

def build_sheet(ws, company, tab_label, people):
    NUM_COLS = 9
    col_letters = [get_column_letter(i) for i in range(1, NUM_COLS + 1)]
    ws.merge_cells(f"A1:{col_letters[-1]}1")
    t = ws["A1"]
    t.value = f"{company} {tab_label} — Folloze Account Intelligence"
    t.font = Font(bold=True, color="FFFFFF", size=13)
    t.fill = fill("003366")
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36
    headers = ["Name","Title","Department / Focus Area","Reports To","Tenure / Notes",
               "LinkedIn Profile","Relationship to Folloze","Folloze Team Member to Follow Up","Outreach Messaging"]
    col_widths = [22,32,28,25,38,42,32,28,55]
    for i,(h,w) in enumerate(zip(headers,col_widths),start=1):
        cell = ws.cell(row=2,column=i,value=h)
        cell.font = Font(bold=True,color="FFFFFF")
        cell.fill = fill("003366")
        cell.alignment = Alignment(horizontal="center",vertical="center",wrap_text=True)
        cell.border = thin_border()
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[2].height = 32
    tier_colors = {1:("00297A","FFFFFF"),2:("CCE0F5","003366"),3:("EAF4FF","003366")}
    keys = ["name","title","department","reports_to","notes","linkedin","folloze","followup","outreach"]
    for row_num,person in enumerate(people,start=3):
        tier = person.get("tier",3)
        bg,fg = tier_colors.get(tier,("EAF4FF","003366"))
        for col_idx,key in enumerate(keys,start=1):
            val = person.get(key,"")
            cell = ws.cell(row=row_num,column=col_idx,value=val)
            cell.fill = fill(bg)
            is_linkedin = (col_idx==6 and val and val.startswith("http"))
            is_messaging = (col_idx==9)
            cell.font = Font(color="0563C1" if is_linkedin else fg,
                             underline="single" if is_linkedin else None,
                             bold=(tier==1 and not is_messaging),italic=is_messaging)
            cell.alignment = Alignment(wrap_text=True,vertical="top")
            cell.border = thin_border()
        ws.row_dimensions[row_num].height = 60
    legend_row = len(people)+5
    ws.cell(row=legend_row,column=1,value="Legend:").font = Font(bold=True)
    for offset,(label,bg,fg) in enumerate([
        ("Tier 1 — Executive","00297A","FFFFFF"),
        ("Tier 2 — Director / Sr. Manager","CCE0F5","003366"),
        ("Tier 3 — Manager / IC / Specialist","EAF4FF","003366")],start=1):
        c = ws.cell(row=legend_row+offset,column=1,value=label)
        c.fill = fill(bg); c.font = Font(color=fg); c.border = thin_border()
    ws.freeze_panes = "A3"

wb.save(output_path)
```

After saving, do a local smoke test by reopening the workbook with `load_workbook(output_path)`. If you have a separate workbook recalculation utility available in the active environment, run it; otherwise note that Google Sheets will recalculate formulas on open.

---

### 4b. Update an Existing File (Update Mode)

Load and patch — do NOT rebuild from scratch:

```python
from openpyxl import load_workbook
wb = load_workbook(existing_xlsx_path)
```

**Finding the insertion point** — scan for placeholder rows and insert above them:
```python
for r in range(3, ws.max_row + 1):
    v = ws.cell(row=r, column=1).value
    if v and any(x in str(v) for x in ['No additional', 'No confirmed', 'No CIO', 'No contacts']):
        ws.insert_rows(r, amount=len(new_contacts))
        for i, person in enumerate(new_contacts):
            insert_person_row(ws, r + i, person, person['tier'])
        break
```

**Row insertion helper:**
```python
def insert_person_row(ws, row_num, person, tier):
    tier_colors = {1:("00297A","FFFFFF"),2:("CCE0F5","003366"),3:("EAF4FF","003366")}
    bg, fg = tier_colors.get(tier, ("EAF4FF","003366"))
    keys = ["name","title","department","reports_to","notes","linkedin","folloze","followup","outreach"]
    for col_idx, key in enumerate(keys, start=1):
        val = person.get(key, "")
        cell = ws.cell(row=row_num, column=col_idx, value=val)
        cell.fill = PatternFill("solid", fgColor=bg)
        is_linkedin = (col_idx == 6 and val and str(val).startswith("http"))
        is_messaging = (col_idx == 9)
        cell.font = Font(color="0563C1" if is_linkedin else fg,
                         underline="single" if is_linkedin else None,
                         bold=(tier == 1 and not is_messaging), italic=is_messaging)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        s = Side(style='thin', color="0055B3")
        cell.border = Border(left=s, right=s, top=s, bottom=s)
    ws.row_dimensions[row_num].height = 60
```

**Patching individual cells:**
```python
for r in range(3, ws.max_row + 1):
    if ws.cell(row=r, column=1).value == 'Person Name':
        ws.cell(row=r, column=5).value = "Updated notes here"
        break
```

Save the updated workbook under a repo-backed path such as `outputs/account-org-chart/[company]_org_chart.xlsx`, unless the user asked for a different repository location. This local `.xlsx` is an intermediate artifact used for the final Google Sheet upload.

---

### 4c. Upload, Convert, Place, and Open (Required)

The final deliverable is **not** the local `.xlsx`. The final deliverable is a **native Google Sheet** in the correct company folder in Google Drive.

Use the helper script in this skill directory:

```bash
python3 /Users/treyharnden/skills/account-org-chart/upload_org_chart.py \
  --company "[Company]" \
  --xlsx "/absolute/path/to/outputs/account-org-chart/[company]_org_chart.xlsx" \
  --open
```

What the helper does:
- Refreshes the local Google OAuth token at `~/.config/openclaw/google/token.json`
- Resolves the target company folder using the Drive search order from Step 1
- Uploads the local `.xlsx` and converts it to `application/vnd.google-apps.spreadsheet`
- Places the new Google Sheet in the resolved company folder
- Prints the final file metadata and opens the `webViewLink` in the browser when `--open` is provided

Optional overrides:
- `--folder-id <id>` if the target Drive folder is already known
- `--sheet-title "<Company> Org Chart"` to override the default title
- `--dry-run` to verify folder resolution before upload

---

### 5. Populating the Two New Columns

#### Folloze Team Member to Follow Up (col H)
- Pull from Slack: look for which Folloze AE/CSM/SE is mentioned as owner or last touch
- If not found: write `"TBD — assign before send"`
- Format: `"[First Last] — [Role, e.g. AE / CSM / SE]"`

#### Outreach Messaging (col I)
- Use the tab template (Section 3); replace `{name}` and `{company}`; max 3–4 sentences
- Tier 1: strategic/outcome language; Tier 2: operational efficiency; Tier 3: practical/workflow

---

### 6. Deliver the File

- Save the intermediate local workbook to a repo-backed path such as `outputs/account-org-chart/[company]_org_chart.xlsx`
- Upload and convert it to a native Google Sheet in the resolved company folder
- Open the resulting Google Sheet URL in the browser
- Return:
  - the absolute local `.xlsx` path
  - the Drive folder URL used
  - the final Google Sheet URL
- Summary must include:
  - Tabs with new contacts added (count per tab)
  - ⚠️ Departed contacts flagged
  - Contacts with still-obfuscated Apollo names (need enrichment credits to unlock)
  - Verified emails obtained via `apollo_people_match`
  - Folloze team member assignments that are TBD
  - Key Slack intel (departures, org changes, outreach already in motion)
  - Which folder-resolution strategy was used (`exact_folder_name`, `deal_notes_parent`, `contains_folder_name`, or `deal_notes_parent_fallback`)

---

## Key Conventions

- **Always guess reporting lines** — append "(assumed)"
- **Always include LinkedIn** — use Apollo URL if returned; construct `/in/firstname-lastname/` if not; flag as best-guess
- **Flag departures** with ⚠️ in Tenure/Notes
- **Contractors**: note in Tenure/Notes — "Contractor, X months"
- **Sort rows** by tier (Exec → Director → IC) within each tab
- **Empty tabs**: still create the tab; add one row with Name="No contacts found", Outreach Messaging="Enrich manually before outreach"
- **Cross-functional contacts**: place in most relevant tab; note overlap in Tenure/Notes
- **Obfuscated Apollo names**: use `First La***y` format; note "Full name requires enrichment credit" in Tenure/Notes
- **Enriched contacts**: include verified email and employment history context in Tenure/Notes

---

## Notes on Sources

| Source | What to extract |
|--------|----------------|
| **Apollo `apollo_mixed_people_api_search`** | Primary people discovery — domain-filtered, per tab |
| **Apollo `apollo_people_match`** | Full name, verified email, employment history — Tier 1 and key Tier 2 only |
| Slack `#[account]` channel | Names, titles, emails, org changes, departures, Folloze team ownership; paginate fully |
| Google Drive | Org charts, account plans, QBR notes |
| User notes | Names, roles, reporting hints, strategic context |
| Web search | Confirm titles, LinkedIn URLs, leadership changes |

**Source priority:** Apollo `people_match` verified email = ground truth. Slack/user notes override Apollo for titles if more recent. Web search confirms.
