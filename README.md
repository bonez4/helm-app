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

**Current users:** admin, david, chris, jackie, esme, hannah, kobie, maria, tom

**Access control:**
- **All users** see: Client Lookup, Add Client, Reports, Roll-offs
- **Admins only** (`role='admin'`): Import tab
- **David & admins**: IRR Scale, Files
- **David + Chris + admin (hardcoded usernames)**: Xfer Station
- **David only** (hardcoded): Command tab (PIN-locked, PIN = `1144`)

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

---

## App Features

### Client Lookup (all users)
- **Empty-state welcome screen** — when no search or client is open:
  - Italic "welcome back, *[Name]*" watermark in Playfair Display
  - **Service Rate Sheet card** (Tip Fee $250, Special Tonnage $480/ton, Standard Tonnage $525/ton, Rolloff Delivery $100, Pile Pickup $160/hr per worker, Metal Tonnage Disposal $125/ton)
  - **My Notes card** — per-user free-form textarea, auto-syncs to `user_notes` table (cross-device)
  - Rate Sheet and My Notes render side-by-side on desktop (collapse to stacked under 780px)
- **Tokenized search** — "viola howard" matches "HOWARD, VIOLA" regardless of word order
- Inline client card with name + company tag, Acct #, address, phone, pickup days, status, autopay, **route pill**, Edit button
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
- Daily Action Report for any date, split by REIS / SANTOS / Other using first-digit classification
- Columns: #, Acct, **Route**, Name, Address, Note (Phone removed)
- Print popup: 14px body font, tall (~9px padded) rows, portrait, auto-prints
- Grouped tables with per-company and per-action subtotals

### Roll-offs (all users)
- Editable spreadsheet with sortable columns, soft delete + undo, show/restore deleted
- **Monthly Tip** column — click the pill to toggle No (gray) ↔ Yes (green)
- **Reset Monthly Tips** button — yellow-highlighted, clears all tipped flags with confirmation
- **Banner** "⚠ RESET MONTHLY RENTAL FEES" appears on the **last day of each month** if any tipped rolloffs remain (configurable via `ROLLOFF_TIP_RESET_DAY`). Clicking Reset auto-hides the banner
- **Export Untipped** button — `.xls` of all non-deleted, untipped rolloffs with calculated days on site and $4/day charge
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
- Generates formatted **daily email** in a unified three-section layout (no per-company breakdown):
  - **Section 1: Rolloff Internal Volume** (combined Reis + Island + East End rolloff tonnage)
    - Today / WTD / MTD
    - **MOM** — same-period prior month for direct comparison
    - YTD
    - **YOY** — same-period prior year for direct comparison
  - **Section 2: Inbound vs Outbound — Xfer Station, Rolloffs + Walk-Ins**
    - One row per period (Today / WTD / MTD / YTD), formatted `inbound, outbound : net`
    - Net = inbound − outbound. **Red** when net is positive (material accumulating); **green** when net is negative (material clearing out)
    - Plus **MTD YOY** and **YTD YOY** rows showing the same-period prior-year figures
  - **Section 3: Revenue (today only)**
    - Total Revenue Today
    - Rolloff Revenue (today)
    - Walk-In Revenue (today)
- Copy to clipboard / Gmail draft creation
- Historical report viewer (click any past date)
- **Historical bulk import** — upload date-range .xls to upsert history

**2. Intercompany Rolloff Report**
- Weekly view: Mon-Sat + WTD, MTD, YTD
- REIS · SANTOS · ISLAND · TOTALS blocks with Rev/Load, Total Revenue, Loads, Tons/Load, Total Tons, # Drivers, # Hours
- Vinagro (Outbound) + Inbound vs Outbound summary
- Prev/next week arrows, date picker, Print button, Quarterly Report overlay, Projections overlay

**3. Consolidated Rolloff** *(new)*
- Weekly table combining Reis + Island + East End
- Columns: Mon–Sat + Total
- Rows (auto): Date, Revenue, Loads, Tons, Loads/Day, Rev/Load, Tons/Load
- Rows (manual, editable): # of Drivers, ST Hours, OT Hours
- Rows (derived, auto-calc with manual override): Total Hours, Hrs/Drvr, Hrs/Load
- Manual entries saved to `crc_weekly_manual` (shared across users via Supabase)
- Prev/next week arrows, date picker, **Export to Excel** button

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

### Import (Admins only)
- Client CSV import (batched 500 rows, upsert on `client_id`)
- Roll-offs CSV import (handles MM/DD/YYYY or YYYY-MM-DD dates)

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
| MOVE ROLLOFF ON JOB SITE | $60 |

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

- **April 23, 2026** — Daily email rebuild: three unified sections (Rolloff Internal Volume / Inbound vs Outbound / Revenue), no per-company breakdown. Adds MOM + YOY comparison rows. Net inbound vs outbound colored red (accumulating) / green (clearing).
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
