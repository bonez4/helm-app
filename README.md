# HELM — Route & Operations Management System
### Reis Trucking · Nantucket, MA

---

## What This Is

HELM is a single-file web application (`index.html`) that started as a route management system for residential garbage pickup and has grown into a comprehensive operations platform for Reis Trucking and its sister companies. It now handles client management, daily scale reports, intercompany reporting, financial projections, file storage, a transfer-station C&D balance tracker, and a private executive command center.

The app is hosted on GitHub Pages (free) and uses Supabase (paid, upgraded) as its database backend.

---

## Live App

**URL:** https://bonez4.github.io/helm-app/
**Office Password:** nantucket (shared gate password)
**Per-user logins:** See `users` table in Supabase

---

## Credentials

```javascript
SUPABASE_URL  = 'https://iiqlhqtyyqctgupalrlc.supabase.co'
SUPABASE_ANON = 'sb_publishable_JAASDdg8OERvpDTnEeLd5Q_Re48qR1I'
OFFICE_PW     = 'nantucket'
```

These three values live at the top of the `<script>` block in `index.html`. They must always be present — do not replace them with placeholders.

---

## Tech Stack

| Layer | Tool | Cost |
|---|---|---|
| Frontend | Single HTML file (vanilla JS, no framework) | Free |
| Database | Supabase (PostgreSQL + Storage) | Paid (upgraded) |
| Hosting | GitHub Pages (auto-deploys from main branch) | Free |
| Fonts | Google Fonts (DM Sans, DM Mono, DM Serif Display, Inter, Pacifico, Playfair Display) | Free |
| Charts | Chart.js v4 (CDN) | Free |
| PDFs | html2pdf.js (CDN) | Free |

No build step. No npm. No framework. One file.

---

## Users & Access Control

**Current users:** admin, david, chris, jackie, esme, hannah, kobie, maria, tom, jaime, jack

**Access control:**
- **All users** see: Client Lookup, Add Client, Reports, Roll-offs
- **Admins only** (`role='admin'`): Import tab
- **David & admins**: IRR Scale, Files
- **David + Chris + admin (hardcoded usernames)**: Xfer Station
- **David only** (hardcoded): Command tab (PIN-locked, PIN = `1144`), **Workflow** tab (Action Items / project management)

**Layout:** Every signed-in user gets the **vertical left-side nav** layout (`body.layout-side`) — the topbar is `position:fixed` at the top, nav rail is `position:fixed` on the left, content fills the rest of the viewport. Login screen unaffected. (Was originally David-only, rolled out to everyone after the topbar inline-style bug was traced and fixed.)

Per-user themes live in `applyUserTheme()`:
- **esme** — pink accents + full pink gradient topbar
- **jackie** — 🌴 "wishing I was in Jamaica" 🌴 in Pacifico italic across the topbar

---

## Database Schema

### Core Tables

**`clients`** — Residential pickup clients
| Column | Type | Notes |
|---|---|---|
| client_id | TEXT (PK) | e.g. `0001`, `200221` |
| service_day | TEXT | Comma-separated days (`Monday` or `Tuesday,Thursday`) |
| address | TEXT | Street address only |
| phone | TEXT | Optional |
| email | TEXT | Optional |
| client_name | TEXT | Optional, full name |
| autopay | BOOLEAN | Credit card on file |
| status | TEXT | `Active`, `Paused` |
| route | SMALLINT | Route number 1–14 (shown on edit form and action report) |

**`skips`** — Weekly skip records
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | Auto |
| client_id | TEXT (FK) | References clients |
| skip_week | DATE | Actual skip date |
| inquiry_method | TEXT | `phone`, `email`, `person` |
| logged_by | TEXT | Staff display name |

**`notes`** — Client notes with action types
| Column | Type | Notes |
|---|---|---|
| id | SERIAL (PK) | Auto |
| client_id | TEXT | Client ID |
| user_id | TEXT | Display name of staff |
| action | TEXT | `Skip Day`, `1XER`, `1X WK`, `2X WK`, `LPU`, `Special Pickup`, `Misc` |
| action_date | DATE | Date the action applies (nullable for Misc) |
| note | TEXT | Free-text content |

**`rolloffs`** — Construction dumpster tracking
| Column | Type | Notes |
|---|---|---|
| id | SERIAL (PK) | Auto |
| date | DATE | Date placed |
| type | TEXT | `AJ`, `REIS`, `30YD`, `40YD`, etc. |
| customer | TEXT | Customer name |
| address_number | TEXT | Street number |
| street | TEXT | Street name |
| notes | TEXT | Special instructions |
| monthly_tip | BOOLEAN | Monthly rental tipped flag (default FALSE) |
| deleted | BOOLEAN | Soft delete flag |

**`users`** — Authentication
| Column | Type | Notes |
|---|---|---|
| username | TEXT (PK) | Lowercase login |
| password | TEXT | Plaintext (internal tool) |
| display_name | TEXT | Shown in topbar and notes |
| role | TEXT | `admin` or `staff` |

**`contacts`** — Shared contact panel (office + drivers)
| Column | Type | Notes |
|---|---|---|
| id | SERIAL (PK) | |
| company | TEXT | Reis / Santos / Island / etc. |
| section | TEXT | `office` or `driver` |
| name | TEXT | |
| phone | TEXT | |
| email | TEXT | Office only |

**`user_notes`** — Per-user free-form notes shown on Client Lookup home
| Column | Type | Notes |
|---|---|---|
| username | TEXT (PK) | Owner |
| notes | TEXT | Free-form content |
| updated_at | TIMESTAMPTZ | Auto |

### IRR Scale Tables

**`irr_reports`** — Daily scale reports (primary data store)
| Column | Type | Notes |
|---|---|---|
| report_date | DATE (PK) | Report date |
| reis_tons, reis_tickets | NUMERIC, INT | Reis rolloff totals |
| reis_deliveries, reis_empties, reis_double_drops | INT | Service breakdown |
| reis_tip_revenue, reis_svc_revenue | NUMERIC | Reis tip/tonnage revenue + hook fee revenue |
| pile_tons, pile_tickets | NUMERIC, INT | ZZDELTA (Reis pile pickups) |
| island_tons, island_tickets, island_revenue | NUMERIC, INT, NUMERIC | Island Rubbish (ZZISLAND) |
| santos_tons, santos_tickets, santos_revenue | NUMERIC, INT, NUMERIC | East End (ZZEASTEND) |
| walkin_tons, walkin_tickets, walkin_tip_revenue | NUMERIC, INT, NUMERIC | Walk-in customers |
| vinagro_tons, vinagro_loads | NUMERIC, INT | Outbound (ZZREIS to landfill) |
| total_inbound_tons, total_inbound_tickets | NUMERIC, INT | Grand totals |
| driver_hours, island_drivers, island_hours | NUMERIC, INT | Operational metrics (Island only so far) |

**`irr_rates`** — Intercompany hook fees + per-ton rates (current as of 4/17/2026)
| company | hook_fee | per_ton | ton_markup | Effective rate |
|---|---|---|---|---|
| `island` | $250 | $480 | 0 | $480/ton |
| `eastend` | $250 | $480 | 0 | $480/ton |

Reis walk-in and rolloff tonnage revenue is parsed **from the scale file directly** (per-ticket rates). Island & East End revenue is computed `hook_fee × tickets + per_ton × tons`.

**`crc_weekly_manual`** — Consolidated Rolloff report manual entries (hours / drivers)
| Column | Type | Notes |
|---|---|---|
| week_start | DATE (PK) | Monday of the week |
| data | JSONB | `{drivers:{0:n,...}, stHours:{}, otHours:{}, totalHours:{}, hrsDrvr:{}, hrsLoad:{}}` |
| updated_at | TIMESTAMPTZ | Auto |

### Files Tables

**`helm_folders`** / **`helm_files`** — Folder + file metadata for the Files tab. Private `helm-files` Supabase Storage bucket holds the actual blobs.

### Command Center (David only)

**`helm_command_state`** — Private strategic dashboard state (not documented here).

### Workflow Tables (David only — Action Items / project management)

Six tables backing the Workflow tab:
- **`helm_action_projects`** — top-level project (id, identifier, name, description, emoji, color, status, start_date, due_date, archived, sort_order, created_at, updated_at)
- **`helm_action_tasklists`** — sections within a project (project_id FK, name, sort_order, archived)
- **`helm_action_milestones`** — date-anchored markers (project_id FK, name, description, due_date, completed_at, color, sort_order)
- **`helm_action_tasks`** — the work items (project_id, tasklist_id, milestone_id, parent_task_id [self-FK for subtasks], task_number, title, description, status, priority 0-4, start_date, due_date, estimated_hours, percent_complete, sort_order, archived, completed_at, **`recurrence` jsonb** [`{type:'daily'|'weekly'|'monthly_day'|'monthly_last'|'every_n_days', days?:[0-6], day?:1-31, n?:N}`], created_at, updated_at)
- **`helm_action_dependencies`** — task → task blocking relationships (task_id, depends_on_task_id, dep_type, unique pair)
- **`helm_action_activity`** — append-only log (project_id, task_id, action, detail jsonb, created_at)

All tables RLS-enabled with open policies (HELM standard).

---

## App Features

### Client Lookup (all users)
- **Empty-state welcome screen** — when no search or client is open:
  - Italic "welcome back, *[Name]*" watermark in Playfair Display
  - **Service Rate Sheet card** (Tip Fee $250, Special Tonnage $480/ton, Standard Tonnage $525/ton, **Insulation $575/ton**, Rolloff Delivery $100, Pile Pickup $160/hr per worker, Metal Tonnage Disposal $125/ton)
  - **My Notes card** — per-user free-form textarea, auto-syncs to `user_notes` table (cross-device)
  - Rate Sheet and My Notes render side-by-side on desktop (collapse to stacked under 780px)
- **Tokenized search** — "viola howard" matches "HOWARD, VIOLA" regardless of word order
- Inline client card with name + company tag, Acct #, address, phone, **email** (clickable `mailto:` link in teal when set, "No email on file" placeholder when missing), pickup days, status, autopay, **route pill**, Edit button
- Notes support 7 categories (Skip Day, 1XER, 1X WK, 2X WK, LPU, Special Pickup, Misc)
- Inline Yes/No delete confirmation on notes

### Add Client (all users)
- Company picker (REIS / SANTOS) required before any other fields
- First-digit classification: 2xxxxx → REIS, 3xxxxx → SANTOS
- First add in session: max ID + 51 (safety buffer); subsequent: +1
- Day toggle buttons (Mon-Sat) for multi-day pickup
- Duplicate detection by address or name

### Edit Client
- Name / address / phone / email / pickup days / **route 1-14 dropdown** / autopay
- Routes chosen from "Select Route" dropdown; renders as a navy pill on the card

### Reports (all users)
Four cards on the Reports tab:

1. **Daily Action Report** — actionable notes for a specific date
   - Split by REIS / SANTOS / Other (first-digit classification)
   - **Grouped by Route** within each company (Route 1, Route 2, … Route 14, then "No Route Assigned"); rows sorted by account # within a route
   - Columns: #, Acct, Action (colored chip), Name, Address, Note
   - Print popup mirrors the on-page layout in an Arial print template

2. **Notes Added Today** — every note input on a specific date (filters by `notes.created_at`, not `action_date`, so future-dated notes still show)
   - Section per **For Date** (the date the note's action falls on); within each section, **sorted by Route** ascending (no-route last; ties broken by acct #)
   - Date section headers include the day of week ("For Wednesday, Apr 29")
   - Columns: # / Route / Acct / Co (single-letter chip) / Action / Client / Address / Note / Time
   - Summary strip of action-type counts at the top
   - Print version uses **enlarged date headers** (≈20px h2) so CSRs can scan from arm's length

3. **Everything Report** — every note ever input, with author column
   - **Custom date range filter** on `created_at` (when the note was input). `Input from` + `Input to` pickers + `Last 7d / 30d / 90d / All time` quick presets. Either side may be left blank for an open-ended range.
   - Same layout as Notes Added Today (For Date sections, sorted by Route within), plus a **By** column showing which user logged each note
   - Header strip shows the chosen range and the For-date span across the result
   - Print version uses the same enlarged date-header treatment

4. **Export Clients to Excel** — column-picker export
   - Toggleable columns: Account # / Company / Name / Address / Phone / Email / Pickup Days / Route / Status / Autopay / Date Added
   - Filters: Company (REIS / SANTOS), Status (Active / Paused), Email (with / without — useful for gap-hunting), Route (1-14 or "no route")
   - Downloads as `HELM_Clients_YYYYMMDD.xls`

### Roll-offs (all users)
- Editable spreadsheet with sortable columns, soft delete + undo, show/restore deleted
- **Customer + Street auto-suggest** — both fields use a `<datalist>` populated from previously-used values; type a few letters then Tab/Enter to accept
- **Monthly Tip** column — click the pill to toggle No (gray) ↔ Yes (green)
- **Reset Monthly Tips** button — yellow-highlighted, clears all tipped flags with confirmation
- **Banner** "⚠ RESET MONTHLY RENTAL FEES" appears on the **last day of each month** if any tipped rolloffs remain (configurable via `ROLLOFF_TIP_RESET_DAY`). Clicking Reset auto-hides the banner
- **Export Untipped** button — `.xls` of all non-deleted, untipped rolloffs. Output sheet has two trailing empty columns (manual day-count + auto `=prev*4` charge formula); the legacy "days on site" pre-calculated column was removed in favor of this manual entry pattern
- **Export Print Sheet** button — alpha-by-company `.xls` matching the legacy Times New Roman template, with 20 blank rows for handwriting

### IRR Scale (David + admins)

Four sub-views:

**1. Daily Scale Report**
- Drag/drop `.xls` upload
- **Review IC Tickets modal** (post-parse) lists Island / East End / **Delta** tickets with three checkbox columns:
  - **Exclude** — drop the ticket entirely (tons/tickets/revenue removed)
  - **Pile Pickup** — Island/East End only; move to walk-in
  - **Walk In** — any IC ticket that's actually a walk-in; move to walk-in
  - Exclude wins if multiple boxes are checked
- Driver hours prompt — asks for Island Rubbish driver count + hours
- Auto-save — raw .xls saved to Files → shared "Daily Scale Reports" folder
- Generates formatted **daily email** in a unified three-section layout (no per-company breakdown). Identical structure renders both inside the Daily Scale Report tab (`irrRenderReportView`) and as the email body the Copy/Gmail buttons emit:
  - **Section 1: Rolloff Internal Volume** (combined Reis + Island + East End rolloff tonnage)
    - **Today** row: `X trips · Y.YY tons` — **highlighted across the whole row** (soft yellow `#fff4cc`)
    - WTD / MTD / **MOM** / YTD / **YOY** — each in tons
    - **MOM** = sum across the same days of the prior month (capped if prior month is shorter); shows the prior-period absolute total + a signed `(+X.XX tons, +Y.Y% vs MTD)` delta colored green when this month is up, red when down
    - **YOY** = sum from Jan 1 of prior year through the prior-year equivalent of today (handles Feb 29 → Feb 28 in non-leap years); shows the same `(±X tons, ±Y% vs YTD)` delta
  - **Section 2: Inbound vs Outbound — Xfer Station, Rolloffs + Walk-Ins**
    - **Today** row formatted `inbound, outbound : net` — **highlighted across the whole row**
    - WTD / MTD / YTD rows in the same format
    - Net = inbound − outbound. **Red** when net is positive (material accumulating); **green** when net is negative (material clearing out)
    - **MTD YOY** and **YTD YOY** rows render as a two-line block: `2025: X.XX tons, 2026: Y.YY tons` followed by `% Change: ±Z%` (green when current year is up, red when down). Single tonnage figure = total inbound (rolloff + walkin); year labels track the report's date so historical reports show the correct year pair.
  - **Section 3: Revenue**
    - **Total Revenue Today** (bold) — **highlighted across the whole row**
    - **Rolloff Revenue** with two indented sub-rows: `Hook Fee Revenue` and `Tonnage Revenue` (split using `irr_rates` to back out IC hook contribution)
    - **Walk-In Revenue** displayed as `$X · N tickets` (ticket count includes walkin + pile pickups, since pile pickups don't have their own revenue line)
- Copy to clipboard / Gmail draft creation
- Historical report viewer (click any past date)
- **Historical bulk import** — upload date-range .xls to upsert history

**2. Intercompany Rolloff Report**
- Weekly view: Mon-Sat + WTD, MTD, YTD
- TOTALS at top, then Vinagro (Outbound), then Total Tonnage Inbound v Outbound, then REIS / ISLAND / SANTOS sub-blocks (Rev/Load, Total Revenue, Loads, Tons/Load, Total Tons, # Drivers, # Hours)
- Prev/next week arrows, date picker
- **Export File** — generates .xlsx + .pdf in the consolidated layout
- **Print** — print preview
- **Quarterly Report** — quarter-vs-prior-year overlay with KPI tables + per-month bar/line charts
- **Yearly Report** — *(new)* custom-range modal with two daily line charts (Tickets per Day, Revenue per Day). Each chart overlays Rolloff (Reis+Island+East End combined, teal) vs Walk-In (gold). `From / To` date pickers + `90d / 6mo / 1yr / 2yr` quick presets (default = trailing 12 months). Stock-chart styling: Y axis auto-fits the data range (no forced zero baseline), no point markers, smooth lines. Days without a scale report (Sundays, holidays) show as **gaps** in the line rather than dropping to zero. Indexed hover tooltip shows both series' exact values for any day.
- **Projections** overlay

**3. Consolidated Rolloff**
- Weekly table combining Reis + Island + East End
- Columns: Mon–Sat + Total
- Rows (auto): Date, Revenue, Loads, Tons, Loads/Day, Rev/Load, Tons/Load
- Rows (manual, editable): # of Drivers, ST Hours, OT Hours
- Rows (derived, auto-calc with manual override): Total Hours, Hrs/Drvr, Hrs/Load
- Manual entries saved to `crc_weekly_manual` (shared across users via Supabase)
- Prev/next week arrows, date picker, **Export to Excel** button
- **2025 Historical Rolloff/C&D table** *(new)* below the weekly grid — 12 month columns (Jan→Dec) with 4 rows: `Loads/Month` (rolloff), `Rev/Load (Rolloff)`, `C&D Loads/Month` (rolloff + walk-ins), `Rev/Load (C&D)`. Sourced from `irr_reports` for calendar 2025; cached on `window._crc2025Data` so week-flipping doesn't re-fetch.

**4. Dashboard**
- Date range (WTD/MTD/30D/YTD/Custom) + company filter (All/Reis/Island/East End)
- KPI cards + Chart.js line chart with toggleable series
- Driver Hours Entry form (Island only currently)
- Generate Report → date-range period report with KPIs, daily breakdown, WoW summary, print/Gmail/PDF

### Xfer Station (David + Chris + admin)
- **Seed balance panel** — shared "on this date the C&D room held X tons" anchor; edit button requires confirmation
- **KPI cards** — Currently in station · 30-day avg daily net · Days to capacity · YTD inbound · YTD outbound
- **Weekly grid** with prev/next + date picker — Inbound / Outbound / Net / End-of-day balance rows × Mon–Sat + WTD + MTD + YTD columns
- **Running balance line chart** (Chart.js) — full history, walking forward + backward from the seed; capacity target shown as dashed red line
- **Capacity** input field — personal target (localStorage, not shared) for % over calculations on date cells

### Files (David + admins)
- Two sub-views: Shared / My Files
- Single-level folders (create/delete with confirmation)
- Multi-file upload, any type
- Download via 5-minute signed URLs
- Auto-saves daily .xls uploads to shared "Daily Scale Reports" folder

### Command (David only, PIN-locked)
- Private strategic dashboard (PIN `1144`)
- Persists state per-user in `helm_command_state`

### Workflow (David only) — Project Management
Full project-management surface, Linear/Notion polish on top of a Zoho-style hierarchy. **David-only** (gated via username check, no separate PIN). Lands as the default tab on login.
- **Sidebar** with Inbox / Today / My Tasks / Activity cross-project views, plus a Projects list (each project gets an emoji + auto-color)
- **Per-project workspace** with sub-nav: Dashboard / List / Board (Kanban) / Gantt / Milestones
- **Task model**: project → tasklist → task → subtask, plus milestones and dependencies. Per-project task identifiers (e.g. `HELM-42`)
- **Recurring tasks**: tasks can have a recurrence rule (Daily / Weekly on chosen weekdays / Monthly day-of-month / Last day of month / Every N days). Marking a recurring task **Done** auto-rolls it forward to the next occurrence with status reset and `due_date` advanced. 🔁 icon next to recurring tasks in list views.
- **Slide-in detail panel** (right side, 580px) for any task — inline-editable title, status / priority / tasklist / milestone / dates / % complete (slider) / estimate, description, subtasks, blocked-by + blocking deps, duplicate, archive
- **Quick add** via FAB (bottom right) or `C` key — chip-picker for project / tasklist / status / priority / due
- **Command palette** via `Cmd/Ctrl+K` — fuzzy search projects, tasks (by ID or title), and 6 jump commands; arrow keys + Enter to fire
- **Esc** closes anything open (panel / modal / palette)
- Status workflow: Backlog → Todo → InProgress → InReview → Done → Cancelled. Click status chip to cycle.
- Activity log entries on create / status change / archive / recurring roll
- Top-bar nav badge shows count of Active+InProgress when >0
- Six dedicated Supabase tables — see "Workflow tables" under Database Schema

### Import (Admins only)
Three cards on the Import tab:
- **Staff Activity Report** — date picker, lists user heartbeats + activity log entries for the selected day
- **Import Clients from CSV** — batched 500 rows, upsert on `client_id`. Headers: `client_id, address, phone, client_name`
- **Bulk Update Emails** — CSV upload that auto-detects account-# and email columns from the header row (recognizes `account_id`, `client_id`, `acct`, etc. + `email` / `email_address`). Shows a preview table (acct / name / old email / new email) with counts: `X to update / Y unchanged / Z unknown acct` (unknowns listed in a collapsed details block). Confirm runs row-by-row UPDATEs and updates the in-memory client cache so cards refresh immediately.
- **Import Roll-offs from CSV** (handles MM/DD/YYYY or YYYY-MM-DD dates)

### Contacts Panel (top-bar, all users)
- Draggable, resizable panel pinned to the top bar
- Office / Driver sections per company, inline-editable cells (name, phone, email)
- Click any cell, type, Enter/blur to save

### Sticky Notes (top-bar, all users)
- Personal scratchpad for quick notes

---

## Business Context

### Company Structure
- **Reis Trucking** — residential garbage, rolloff dumpsters, scale operations
- **Island Rubbish (ZZISLAND)** — intercompany sister business, rolloffs only
- **East End / SANTOS (ZZEASTEND)** — intercompany sister business
- **Vinagro (ZZREIS)** — outbound waste hauling to mainland landfill
- **ZZDELTA** — Reis pile pickup jobs
- **ZZTNT** and others — walk-in-style ZZ customers

### Growth Goal
**50% increase in rolloff volume over 2025** (full-year 2025 × 1.5 = 2026 target).

### Seasonality
Nantucket follows Northeast peak construction pattern: peak May-October (tourists + construction), slow Nov-April. Derived automatically from 2025 monthly data for projections.

### Pricing (effective April 17, 2026)

**Walk-in tonnage rates** (per-ticket, parsed from scale file):
- Standard tier: **$525/ton**
- Special tier: **$480/ton**
- Older tiers ($380 / $425) existed before 4/17 and persist on pre-4/17 reports

**Reis rolloff hook fees** (hardcoded in helm, effective 4/17/2026; pre-4/17 uses file values):
| Service | Price |
|---|---|
| ROLLOFF DELIVERY | $100 |
| EMPTY ROLLOFF / EMPTY ROLL-OFF & RETURN | $250 |
| ROLLOFF DOUBLE DROP | $250 |
| MOVE ROLLOFF ON JOB SITE | $100 |

**Per-unit disposal fees** (hardcoded, always applied regardless of file rate):
| Line item | Price | Routes to |
|---|---|---|
| MATTRESS LANDFILL DISPOSAL FEE | $50 | Reis tipRev if rolloff ticket, else walkin tipRev |
| STOVE DISHWASH APPLIANCE DISP | $11 | Same |
| FRION LANDFILL DISPOSAL FEE | $45 | Same |
| MONITOR LANDFILL DISPOSAL FEE | $16.50 | Same |
| DUMPTIRE | $16.50 | Same |
| METAL DROPPED OFF @ REIS YARD/ | $125/ton | Not captured — goes to metal yard, not C&D room |

**Intercompany** (from `irr_rates`):
- Island: $250 hook + $480/ton, 0% markup
- East End: $250 hook + $480/ton, 0% markup (was $200 + $380 + 10% pre-4/17)

---

## Parsing Notes (critical)

### Revenue routing (as of 4/19/2026)

Each ticket's revenue is routed based on its ticket type and the kind of fee:

**Hook Fee Revenue (`reis_svc_revenue`)** — ONLY these:
- ROLLOFF DELIVERY, EMPTY ROLLOFF, ROLLOFF DOUBLE DROP, MOVE ROLLOFF ON JOB SITE
- Uses hardcoded prices for dates ≥ 4/17/2026; uses scale-file dollar amount for earlier dates

**Tonnage Revenue (`reis_tip_revenue`)** — the ticket's tip fee (net tons × rate from file) PLUS any per-unit disposal fees that happen on the same rolloff ticket

**Walk-in Revenue (`walkin_tip_revenue`)** — walk-in tip fees PLUS any per-unit disposal fees on walk-in tickets (including non-intercompany ZZ codes)

### Service Fee Parser Bug (fixed)
Earlier versions walked backward through row data for a positive number and sometimes grabbed the **ticket number** as a fee. Fixed by only scanning AFTER the service keyword position:

```javascript
const kwIdx = dataVals.findIndex(v => v && v.toUpperCase().includes(kw));
if (kwIdx >= 0) {
  for (let j=dataVals.length-1; j>kwIdx; j--) { /* scan after */ }
}
```

When re-importing historical data, verify Reis service fees average $180-$210 per ticket pre-4/17. Anything >$500/ticket indicates the old bug is back.

### YTD Calculations
- Current year YTD: sum of `irr_reports` where `report_date >= {year}-01-01 AND report_date <= today`
- Prior year same-period: sum through same MM-DD in prior year (grows day by day with current year)

### HELM revenue vs Scale-file "Report Totals" — why they differ

A common question: "the scale .xls says $51,863 in revenue, but HELM's daily email says $56,335 — is something wrong?"

Nothing's wrong. HELM's revenue is **not** a copy of the file's grand total. It's a recomputation that intentionally diverges in three predictable places. When you reconcile by hand, the gap will always come from one or more of these:

1. **Hardcoded rolloff service fees (post-4/17/2026).** Scale tickets often list rolloff service line items (DELIVERY, EMPTY, DOUBLE DROP, MOVE) at $0/EA or at older rates. HELM ignores the file value and applies the current schedule (`$100 / $250 / $250 / $100`). Effect: HELM total > file total whenever the file under-prices these.

2. **Per-unit disposal fees applied at fixed prices.** Mattress / appliance / freon / monitor / tire line items are billed by HELM at hardcoded rates regardless of file value (`$50 / $11 / $45 / $16.50 / $16.50`). If the file shows them at $0 but the count is N, HELM still bills N × rate.

3. **Intercompany hook fees that the file doesn't carry.** The scale file's tip-fee total reflects net tons × rate for IC tickets but does NOT add a hook fee per IC ticket — that's an inter-company billing arrangement, not a scale-house charge. HELM, by design, computes IC revenue as `hook_fee × tickets + per_ton × tons` (see `irr_rates`), so it adds **$250 per Island ticket + $250 per East End ticket** on top of the per-ton portion. On a heavy IC day this is the largest single contributor to the gap.

Quick reconciliation pattern when investigating a difference:
- Total file rolloff-service line items, compare against what HELM applies (1×$100 + N×$250 etc) → service uplift component
- Count IC tickets (East End + Island), multiply by $250 → IC hook lift component
- Sum should approximately equal `HELM total − file Report Totals`

Reclassifications also matter: if any IC tickets were marked **Pile Pickup**, **Walk In**, or **Exclude** in the Review IC modal during upload, that revenue moved between buckets (or was removed entirely) — the on-screen / email totals reflect the post-reclassification state, not the raw file.

---

## Deployment

### To update the live site:
1. Edit `index.html`
2. Run `git add index.html && git commit -m "description" && git push`
3. GitHub Pages auto-deploys in ~1-2 minutes

### To add a new staff user:
```sql
INSERT INTO users (username, password, display_name, role)
VALUES ('newname', 'password', 'Display Name', 'staff');
```

### To promote a user to admin:
```sql
UPDATE users SET role = 'admin' WHERE username = 'username';
```

### To re-import historical scale data:
IRR Scale → Daily Scale Report → Historical Import. Upserts on `report_date`. Applies current parsing logic (hardcoded fees for dates ≥ 4/17, per-unit fees, disposal revenue routing).

---

## Supabase Setup Requirements

### All tables require RLS + open policies (pattern):
```sql
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
CREATE POLICY "{table}_all" ON {table} FOR ALL USING (true) WITH CHECK (true);
```

### Non-obvious tables/columns (run these if setting up fresh):
```sql
-- Route on clients
ALTER TABLE clients ADD COLUMN IF NOT EXISTS route SMALLINT;

-- Monthly Tip on rolloffs
ALTER TABLE rolloffs ADD COLUMN IF NOT EXISTS monthly_tip BOOLEAN DEFAULT FALSE;

-- Consolidated Rolloff manual entries
CREATE TABLE IF NOT EXISTS crc_weekly_manual (
  week_start DATE PRIMARY KEY,
  data JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE crc_weekly_manual ENABLE ROW LEVEL SECURITY;
CREATE POLICY "crc_weekly_manual_all" ON crc_weekly_manual FOR ALL USING (true) WITH CHECK (true);

-- Per-user notes
CREATE TABLE IF NOT EXISTS user_notes (
  username TEXT PRIMARY KEY,
  notes TEXT DEFAULT '',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE user_notes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user_notes_all" ON user_notes FOR ALL USING (true) WITH CHECK (true);

-- created_at on clients (for the "Clients added by date" lookup; harmless if not used)
ALTER TABLE clients ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- Workflow tab schema (David only) — six tables for project management
CREATE TABLE IF NOT EXISTS helm_action_projects (
  id BIGSERIAL PRIMARY KEY, identifier TEXT UNIQUE, name TEXT NOT NULL,
  description TEXT, emoji TEXT DEFAULT '📁', color TEXT DEFAULT '#7c5cff',
  status TEXT DEFAULT 'Active', start_date DATE, due_date DATE,
  archived BOOLEAN DEFAULT FALSE, sort_order INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS helm_action_tasklists (
  id BIGSERIAL PRIMARY KEY,
  project_id BIGINT NOT NULL REFERENCES helm_action_projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL, sort_order INT DEFAULT 0,
  archived BOOLEAN DEFAULT FALSE, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS helm_action_milestones (
  id BIGSERIAL PRIMARY KEY,
  project_id BIGINT NOT NULL REFERENCES helm_action_projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL, description TEXT, due_date DATE, completed_at TIMESTAMPTZ,
  color TEXT DEFAULT '#a78bfa', sort_order INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS helm_action_tasks (
  id BIGSERIAL PRIMARY KEY,
  project_id BIGINT NOT NULL REFERENCES helm_action_projects(id) ON DELETE CASCADE,
  tasklist_id BIGINT REFERENCES helm_action_tasklists(id) ON DELETE SET NULL,
  milestone_id BIGINT REFERENCES helm_action_milestones(id) ON DELETE SET NULL,
  parent_task_id BIGINT REFERENCES helm_action_tasks(id) ON DELETE CASCADE,
  task_number INT, title TEXT NOT NULL, description TEXT,
  status TEXT DEFAULT 'Backlog', priority SMALLINT DEFAULT 0,
  start_date DATE, due_date DATE, estimated_hours NUMERIC,
  percent_complete SMALLINT DEFAULT 0, sort_order INT DEFAULT 0,
  archived BOOLEAN DEFAULT FALSE, completed_at TIMESTAMPTZ,
  recurrence JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS helm_action_dependencies (
  id BIGSERIAL PRIMARY KEY,
  task_id BIGINT NOT NULL REFERENCES helm_action_tasks(id) ON DELETE CASCADE,
  depends_on_task_id BIGINT NOT NULL REFERENCES helm_action_tasks(id) ON DELETE CASCADE,
  dep_type TEXT DEFAULT 'FS', created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(task_id, depends_on_task_id)
);
CREATE TABLE IF NOT EXISTS helm_action_activity (
  id BIGSERIAL PRIMARY KEY,
  project_id BIGINT REFERENCES helm_action_projects(id) ON DELETE CASCADE,
  task_id BIGINT REFERENCES helm_action_tasks(id) ON DELETE CASCADE,
  action TEXT NOT NULL, detail JSONB, created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE helm_action_projects     ENABLE ROW LEVEL SECURITY;
ALTER TABLE helm_action_tasklists    ENABLE ROW LEVEL SECURITY;
ALTER TABLE helm_action_milestones   ENABLE ROW LEVEL SECURITY;
ALTER TABLE helm_action_tasks        ENABLE ROW LEVEL SECURITY;
ALTER TABLE helm_action_dependencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE helm_action_activity     ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ap_projects_all"     ON helm_action_projects     FOR ALL USING(true) WITH CHECK(true);
CREATE POLICY "ap_tasklists_all"    ON helm_action_tasklists    FOR ALL USING(true) WITH CHECK(true);
CREATE POLICY "ap_milestones_all"   ON helm_action_milestones   FOR ALL USING(true) WITH CHECK(true);
CREATE POLICY "ap_tasks_all"        ON helm_action_tasks        FOR ALL USING(true) WITH CHECK(true);
CREATE POLICY "ap_dependencies_all" ON helm_action_dependencies FOR ALL USING(true) WITH CHECK(true);
CREATE POLICY "ap_activity_all"     ON helm_action_activity     FOR ALL USING(true) WITH CHECK(true);
```

### Storage buckets
- `helm-files` (Private) — with RLS policies allowing anon key to read/write/delete

---

## Known Constraints

- **Authentication** is shared password + per-user login. Fine for small internal team (~9 users).
- **No real-time sync** — users must refresh to see others' changes.
- **Single file** — all HTML, CSS, and JS in `index.html` (~7,200 lines). Intentional simplicity.
- **Autopay** is informational only — billing is external.
- **Driver hours** only captured for Island Rubbish currently (Reis & East End pending — entered manually on Consolidated Rolloff).
- **Walk-in revenue** pre-imports (before walk-in revenue tracking was added) show $0. Recent re-imports fixed this.
- **Xfer Station capacity** is per-browser localStorage; seed balance is shared via app state (experimental — may move to DB).

---

## File Structure

```
helm-app/
├── index.html                                    ← The entire application
├── IRR_DailyScaleReport.gs                       ← Legacy Google Apps Script (not used)
├── irr-daily-report.html                         ← Standalone daily report tool (legacy)
├── sample_clients.csv                            ← Client CSV import template
├── rolloffs_clean.csv                            ← Sample rolloff data
├── 1776188206521-JAN12025TOAPR132026.xls         ← Historical scale export (Jan 1 2025 → Apr 13 2026)
├── README.md                                     ← This file
```

---

## Recent Major Changes

- **April 26, 2026** — **Yearly Report** added to Intercompany Rolloff (next to Quarterly): custom date range, daily-granularity line charts, stock-chart styling (Y auto-fits, no point markers, missing days gap out via null + `spanGaps:false`, no fill). Two stacked charts — Tickets and Revenue — each with Rolloff vs Walk-In lines.
- **April 26, 2026** — **Consolidated Rolloff** sub-tab gets a new 2025 Historical Rolloff/C&D table beneath the weekly grid (12 month columns, 4 metric rows: Loads/Month, Rev/Load Rolloff, C&D Loads/Month, Rev/Load C&D).
- **April 25, 2026** — Daily email/report final shape: Section 1 Today shows `X trips · Y.YY tons` (was just tons); Section 3 renamed to "Revenue" (dropped "(today)"), Rolloff Revenue gets indented Hook Fee + Tonnage sub-rows, Walk-In Revenue shows ticket count (incl. pile pickups), Total Revenue Today highlighted in soft yellow alongside the existing Today highlights in Sections 1 + 2. Pile Pickups section removed entirely. YOY block label "Delta:" → "% Change:".
- **April 24-25, 2026** — Side-nav layout (vertical left rail) rolled out from David-only to all users. Topbar + nav rail now `position:fixed`. The original David rollout had been blocked by an inline `style="position:relative"` on the topbar markup; once that was removed, the layout was safe to apply universally.
- **April 24, 2026** — **Workflow** tab (David-only project management): Projects → Tasklists → Tasks → Subtasks ladder + Milestones + Dependencies; Linear-style slide-in detail panel, Cmd+K command palette, C-key quick add; Recurring tasks auto-roll on completion (daily / weekly on chosen weekdays / monthly day / last day / every N days). Six new Supabase tables.
- **April 24, 2026** — Reports tab: Daily Action Report restructured to group by Route (within Company) instead of by Action; new **Notes Added Today** report (filters by `created_at`, sorted by For Date → Route); new **Everything Report** with custom date range and `By` column; new **Export Clients to Excel** with column picker + filters (incl. with/without email).
- **April 24, 2026** — Roll-offs tab: customer + street fields get native `<datalist>` autosuggest from previously-used values; export-untipped sheet swapped pre-calculated days-on-site for two trailing empty columns (manual day count + auto `=prev*4` formula).
- **April 24, 2026** — Client lookup card now displays email below phone (clickable `mailto:` link in teal, "No email on file" placeholder otherwise). Email entry was already in Add Client / Edit Client; only the display was missing.
- **April 24, 2026** — Insulation $575/ton added to the Service Rate Sheet.
- **April 24, 2026** — Bulk Update Emails tool moved from Reports → Import (admin-only, gated alongside other bulk operations).
- **April 23, 2026** — Documented the HELM-vs-scale-file revenue reconciliation in Parsing Notes. The gap between HELM's daily total and the file's "Report Totals" line is by design — comes from (1) hardcoded post-4/17 service fees overriding file values, (2) hardcoded per-unit disposal fees, and (3) IC hook fees that aren't on the scale ticket.
- **April 23, 2026** — Daily email rebuild: unified sections (Rolloff Internal Volume / Inbound vs Outbound / Revenue), no per-company breakdown. MOM + YOY rows on Section 1 show prior-period totals plus a signed (±tons, ±%) delta. MTD YOY / YTD YOY on Section 2 render as a two-line block (`2025: X tons, 2026: Y tons` + `% Change: ±Z%`). Net inbound vs outbound colored red (accumulating) / green (clearing). Today rows in Sections 1, 2 and Total Revenue Today in 3 highlighted edge-to-edge in soft yellow. Same layout drives both the email body and the in-app Daily Scale Report view (`irrRenderReportView`), all from one shared `irrLoadYTD` data fetch.
- **April 19, 2026** — Hook fee vs disposal fee split. Disposal fees (mattress, appliance, freon, monitor, tire) now route based on ticket: Reis rolloff ticket → tonnage revenue; walk-in → walk-in revenue. Move Rolloff stays in hook fees.
- **April 19, 2026** — Review IC Tickets modal extended: includes Delta; three columns (Exclude / Pile Pickup / Walk In).
- **April 18, 2026** — Consolidated Rolloff sub-tab added under IRR Scale. Excel export + shared manual hours/drivers entry.
- **April 17, 2026** — Rate change: rolloff service fees hardcoded ($100/$250/$250/$60) for dates ≥ 4/17. East End billing: $200+$380+10% → $250+$480+0%. Walk-in tiers: $380→$480, $425→$525.
- **April 17, 2026** — Per-unit fee tracking (mattress/appliance/freon/monitor/tire/move rolloff) with fixed HELM-side prices.
- **April 17, 2026** — Route dropdown (1-14) on client edit form; Route column on daily action reports.
- **April 17, 2026** — Roll-offs: Monthly Tip toggle, Export Untipped, Reset button, last-day-of-month banner, Export Print Sheet mirroring the alpha-by-company legacy template.
- **April 17, 2026** — Xfer Station tab (David/Chris/admin): seed balance, KPIs, weekly grid, running balance chart.
- **April 17, 2026** — Daily email restructure: Total Revenue headline, Vinagro/Walk-In at top, Day Totals + WTD Net + YTD Net.
- **April 16-17, 2026** — Lookup empty state redesign: italic Playfair welcome watermark + Service Rate Sheet card + My Notes card (side-by-side). User notes sync via `user_notes` table.
- **April 16, 2026** — Per-user themes (esme pink + pink topbar; jackie Jamaica topbar).
- **April 16, 2026** — Contacts panel cells inline-editable.
- **Oct 2025 → present**: Full IRR Scale system (daily parsing, email drafts, historical viewing, intercompany report, quarterly charts, projections, dashboard).
- **Files tab** with Supabase Storage.
- **Command Center** (David only, PIN-gated).
- **Chris user** added as admin.
