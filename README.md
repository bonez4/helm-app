# HELM — Route & Operations Management System
### Reis Trucking · Nantucket, MA

---

## What This Is

HELM is a single-file web application (`index.html`) that started as a route management system for residential garbage pickup and has grown into a comprehensive operations platform for Reis Trucking and its sister companies. It now handles client management, daily scale reports, intercompany reporting, financial projections, file storage, and a private executive command center.

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
| Fonts | Google Fonts (DM Sans, DM Mono) | Free |
| Charts | Chart.js (CDN) | Free |
| PDFs | html2pdf.js (CDN) | Free |

No build step. No npm. No framework. One file.

---

## Users & Access Control

**Current users:** admin, david, chris, jackie, esme, hannah, kobie, maria, tom

**Access control:**
- **All users** see: Client Lookup, Add Client, Reports, Roll-offs
- **Admins only** (`role='admin'`): Import tab
- **David & admins**: IRR Scale tab, Files tab
- **David only** (hardcoded): Command tab (PIN-locked, PIN = `1144`)

Chris has `role='admin'` so he sees IRR Scale, Files, and Import but not Command.

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
| deleted | BOOLEAN | Soft delete flag |

**`users`** — Authentication
| Column | Type | Notes |
|---|---|---|
| username | TEXT (PK) | Lowercase login |
| password | TEXT | Plaintext (internal tool) |
| display_name | TEXT | Shown in topbar and notes |
| role | TEXT | `admin` or `staff` |

### IRR Scale Tables

**`irr_reports`** — Daily scale reports (primary data store)
| Column | Type | Notes |
|---|---|---|
| report_date | DATE (PK) | Report date |
| reis_tons, reis_tickets | NUMERIC, INT | Reis rolloff totals |
| reis_deliveries, reis_empties, reis_double_drops | INT | Service breakdown |
| reis_tip_revenue, reis_svc_revenue | NUMERIC | Reis tip fees + hook fees |
| pile_tons, pile_tickets | NUMERIC, INT | ZZDELTA (Reis pile pickups) |
| island_tons, island_tickets, island_revenue | NUMERIC, INT, NUMERIC | Island Rubbish (ZZISLAND) |
| santos_tons, santos_tickets, santos_revenue | NUMERIC, INT, NUMERIC | East End (ZZEASTEND) |
| walkin_tons, walkin_tickets, walkin_tip_revenue | NUMERIC, INT, NUMERIC | Walk-in customers |
| vinagro_tons, vinagro_loads | NUMERIC, INT | Outbound (ZZREIS to landfill) |
| total_inbound_tons, total_inbound_tickets | NUMERIC, INT | Grand totals |
| driver_hours, island_drivers, island_hours | NUMERIC, INT | Operational metrics (Island only so far) |

**`irr_ytd_seeds`** — Baseline YTD figures (legacy, less used now)
| Column | Type | Notes |
|---|---|---|
| year | INT (PK) | 2025, 2026 |
| through_date | DATE | Baseline through-date |
| inbound_tons, inbound_tickets | NUMERIC, INT | |
| vinagro_tons, vinagro_loads | NUMERIC, INT | |

**`irr_rates`** — Configurable hook fees + per-ton rates
| Column | Type | Notes |
|---|---|---|
| company | TEXT (PK) | `island`, `eastend` |
| hook_fee | NUMERIC | $250 Island, $200 East End |
| per_ton | NUMERIC | $480 Island, $380 East End |
| ton_markup | NUMERIC | 0 Island, 0.10 East End (10% markup → $418/ton) |

Reis revenue is parsed from the scale file directly (variable rates per customer). Island & East End revenue is calculated using these fixed rates on upload.

### Files Tables

**`helm_folders`** — Folder organization
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | Auto |
| name | TEXT | Folder name |
| scope | TEXT | `shared` or `personal` |
| owner | TEXT | Username for personal folders, NULL for shared |
| created_by | TEXT | Username |

**`helm_files`** — File metadata
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | Auto |
| folder_id | UUID (FK) | References helm_folders |
| filename | TEXT | Display name |
| storage_path | TEXT | Path in Supabase Storage `helm-files` bucket |
| size_bytes | BIGINT | File size |
| mime_type | TEXT | Content type |
| uploaded_by | TEXT | Username |

### Command Center (David only)

**`helm_command_state`** — Private strategic dashboard state (private, not documented here)

### Storage Buckets

**`helm-files`** — Supabase Storage bucket for file uploads (private). Daily scale exports are auto-saved here.

---

## App Features

### Client Lookup (all users)
- **Inline client card** under search bar (redesigned from floating panel)
- **Tokenized search** — "viola howard" matches "HOWARD, VIOLA" regardless of word order
- Searches client ID, name, address, phone simultaneously
- Single match auto-opens the card; multiple matches show a clickable list
- **Clear button** removes card and resets search
- Two-column card layout:
  - **Left:** Name + company tag, Acct #, address, phone, pickup days, status, autopay, Edit button
  - **Right:** Note entry form + scrollable chronological note history
- Notes support 7 categories (Skip Day, 1XER, 1X WK, 2X WK, LPU, Special Pickup, Misc)
- Inline Yes/No delete confirmation on notes

### Add Client (all users)
- **Company picker** (REIS or SANTOS) at top of form — determines ID prefix (20xx or 30xx)
- Auto-suggests next available ID for the selected company (20 or 30 prefix, incrementing)
- Name, address, phone, email fields
- Day toggle buttons (Mon-Sat) for multi-day pickup
- Duplicate detection by address or name

### Reports (all users)
- Daily Action Report for any date
- Summary pills by action type
- Grouped tables with client details
- Print-friendly version

### Roll-offs (all users)
- Editable spreadsheet-style table
- Click any cell to edit inline, auto-saves
- Sortable columns, soft delete with undo, show/restore deleted

### IRR Scale (David + admins)

The IRR Scale tab has three sub-views:

**1. Daily Scale Report**
- Drag/drop `.xls` upload from scale software
- Parser handles SpreadsheetML format with service fee fix (scans AFTER keyword position to avoid grabbing ticket numbers)
- **Ticket reclassification modal** — after parse, checkboxes for Island/East End tickets to flag pile pickups (moves them to walk-in bucket)
- **Driver hours prompt** — after upload, modal asks for Island Rubbish driver count and hours
- **Auto-save** — raw .xls file saved to Files tab in shared "Daily Scale Reports" folder
- Generates formatted email draft with per-company breakdown:
  - Reis, Island, East End: Loads, Hook Fee Revenue, Tonnage Revenue, Total Revenue, Rev/Load, Total Tons, Tons/Load
  - Pile Pickups (Reis): shown only if > 0, no dollar amounts
  - Walk-In / Drive-Through: tickets, tons, revenue
  - Total Inbound summary
  - Vinagro Output (loads, total tons)
  - Year-to-date comparison by company (current year vs prior year)
- Copy to clipboard + Gmail draft creation
- Historical report viewer (click any past date in history log)
- **Historical bulk import** — upload a date-range .xls to backfill history

**2. Intercompany Rolloff Report**
- Matches the `Column A` template structure requested
- Weekly view: Mon-Sat columns + WTD, MTD, YTD aggregate columns
- Year selector (2025 / 2026) moved into Quarterly Report overlay
- Four company blocks: REIS, SANTOS (East End), ISLAND, TOTALS
- Each block shows: Rev/Load, Total Revenue, Loads, Tons/Load, Total Tons, # Drivers, # Hours
- Plus Vinagro (Outbound) block and Total Inbound vs Total Outbound summary
- Prev/next week arrows and date picker
- **Print button** opens clean print-friendly overlay
- **Quarterly Report button** opens full quarterly overlay:
  - Year + Quarter selectors (2025/2026, Q1-Q4)
  - Dynamic data loading (selected year vs prior year)
  - Company sections with monthly columns, Q totals, YoY % change (color-coded)
  - Loads/Day row with avg across quarter
  - Vinagro outbound + Inbound/Outbound summary
  - **Consolidated Visuals** at the bottom:
    - Rev/Load (line, 3 companies)
    - Total Revenue / Month (stacked bar by company)
    - Loads/Day (line, 3 companies)
    - Loads / Month (stacked bar by company)
    - Tons/Load (line, 3 companies, fixed y-axis 0.6-2.6 stepping 0.5)
    - Tons / Month (stacked bar by company)
    - Rolloff vs Walk-In Tonnage (monthly doughnut pie row, with labels)
    - Rolloff vs Walk-In Revenue (monthly doughnut pie row, with labels)
  - Click outside to close
- **Projections button** opens monthly forecast overlay:
  - Monthly forecast Jan-Dec with actuals filled for past months
  - 50% growth target baseline (2025 full year × 1.5)
  - Uses 2025 monthly actuals × company growth rates × seasonality
  - Editable assumptions panel: per-company annual growth rate, Island tapering curve, pricing rate change %
  - KPI cards: Projected Full Year loads, Target, Projected Revenue, % On Track

**3. Dashboard**
- Date range selector (WTD, MTD, 30D, YTD, Custom)
- Company filter (All Combined, Reis, Island Rubbish, East End)
- KPI cards: Avg Rev/Load, Avg Tons/Load, Avg Hours/Load, Avg Loads/Day
- Chart.js line chart with toggleable series:
  - Rev/Load, Tons/Load, Hours/Load, Loads/Day
  - Per-company load toggles (Reis, Island, East End) visible in "All Combined" view
- Resizable chart height (+/- buttons, 300-900px)
- Driver Hours Entry form (Island only data currently)
- **Generate Report** button — date-range period report with KPIs, daily breakdown, WoW weekly summary, print/Gmail/PDF

### Files (David + admins)
- Two sub-views: Shared / My Files
- Single-level folders (create/delete with confirmation)
- Multi-file upload, any file type
- File list: name, size, uploader, upload timestamp
- Download via 5-minute signed URLs
- Delete files and folders
- Auto-saves daily .xls uploads to shared "Daily Scale Reports" folder

### Command (David only, PIN-locked)
- Private strategic dashboard
- PIN gate on first access per session (PIN: `1144`)
- Persists state per-user in `helm_command_state` table
- Falls back to in-memory state if table missing

### Import (Admins only)
- Client CSV import (batched 500 rows, upsert on `client_id`)
- Roll-offs CSV import (handles MM/DD/YYYY or YYYY-MM-DD dates)

---

## Business Context

### Company Structure
- **Reis Trucking** — residential garbage, rolloff dumpsters, scale operations
- **Island Rubbish (ZZISLAND)** — intercompany sister business, rolloffs only
  - Billing: $250 hook fee per load + $480/ton
- **East End / SANTOS (ZZEASTEND)** — intercompany sister business
  - Billing: $200 hook fee per load + $380/ton + 10% markup ($418 effective)
- **Vinagro (ZZREIS)** — outbound waste hauling to mainland landfill
- **ZZDELTA** — Reis pile pickup jobs
- **ZZTNT** and others — walk-in-style ZZ customers

### Growth Goal
**50% increase in rolloff volume over 2025** (full-year 2025 × 1.5 = 2026 target).

### Seasonality
Nantucket follows Northeast peak construction pattern: peak May-October (tourists + construction), slow Nov-April. Derived automatically from 2025 monthly data for projections.

### Pricing
Walk-in tip fees vary per customer ($380-$425/ton, parsed from scale file). Rolloff hook fees are $200-$400 depending on container type. Rates change April 15, 2026 — configurable in `irr_rates` table.

---

## Parsing Notes (critical)

### Service Fee Parser Bug (fixed)
Earlier versions had a critical bug where the service fee scanner would walk backward through row data looking for a positive number and sometimes grab the **ticket number** (e.g., 135172) as a fee. Fixed by only scanning AFTER the service keyword position:

```javascript
const kwIdx = dataVals.findIndex(v => v && v.toUpperCase().includes(kw));
if (kwIdx >= 0) {
  for (let j=dataVals.length-1; j>kwIdx; j--) {
    // ...
  }
}
```

Fix applied to both daily parser and bulk import parser. When re-importing historical data, always verify Reis service fees average $180-$210 per ticket. Anything >$500/ticket indicates the old bug is back.

### Walk-in Revenue
Parsed from `REIS SITE TRANSFER FEE` line × rate. Stored in `walkin_tip_revenue` column. Bulk import captures this properly now.

### YTD Calculations
- Current year YTD: sum of `irr_reports` where `report_date >= {year}-01-01 AND report_date <= today`
- Prior year same-period: sum through same MM-DD in prior year (grows day by day with current year)

---

## Deployment

### To update the live site:
1. Edit `index.html`
2. Run `git add index.html && git commit -m "description" && git push`
3. GitHub Pages auto-deploys in ~1-2 minutes
4. Live at same URL: https://bonez4.github.io/helm-app/

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
Upload the YTD .xls through IRR Scale > Daily Scale Report > "Historical Import" button. Upserts on `report_date`, safe to re-run.

---

## Supabase Setup Requirements

### Tables (all RLS enabled with open policies for the anon key)
Standard tables plus IRR-specific: `irr_reports`, `irr_ytd_seeds`, `irr_rates`, `helm_folders`, `helm_files`, `helm_command_state`

### Storage buckets
- `helm-files` (Private) — with RLS policies allowing anon key to read/write/delete

### SQL policies (match pattern across all tables)
```sql
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
CREATE POLICY "{table}_all" ON {table} FOR ALL USING (true) WITH CHECK (true);
```

---

## Known Constraints

- **Authentication** is shared password + per-user login. Fine for small internal team (~9 users).
- **No real-time sync** — users must refresh to see others' changes.
- **Single file** — all HTML, CSS, and JS in `index.html` (~5,900 lines). Intentional simplicity.
- **Autopay** is informational only — billing is external.
- **Driver hours** only captured for Island Rubbish currently (Reis & East End pending).
- **Walk-in revenue** pre-imports (before walk-in revenue tracking was added) show $0. Recent re-imports fixed this.

---

## File Structure

```
helm-app/
├── index.html                       ← The entire application
├── IRR_DailyScaleReport.gs          ← Legacy Google Apps Script (not used, manual upload preferred)
├── irr-daily-report.html            ← Standalone daily report tool (legacy)
├── sample_clients.csv               ← Client CSV import template
├── rolloffs_clean.csv               ← Sample rolloff data
├── README.md                        ← This file
```

---

## Recent Major Changes

- **Oct 2025 → present**: Full IRR Scale system built from scratch
  - Daily scale report parsing, email drafts, historical viewing
  - Intercompany Rolloff Report with weekly/quarterly/projections
  - Dashboard with Chart.js analytics
  - Ticket reclassification UI for Island/East End pile pickups
  - Service fee parser fix (critical bug)
  - Walk-in revenue capture in bulk import
  - Quarterly visual charts (line, stacked bar, pie)
  - Year/quarter dynamic data loading
- **Files tab** added with Supabase Storage integration
- **Command Center** added (David only, PIN-gated)
- **Client Lookup redesign**: floating panel → inline card, tokenized search, Clear button
- **Chris user** added as admin
