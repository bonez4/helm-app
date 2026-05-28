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
- **All users** see: Client Lookup, Add Client, Reports, Roll-offs, **Dispatch group → Dispatch Input + History**
- **Admins only** (`role='admin'`): Import tab
- **Jack + admins**: Import tab
- **David / Jack / admins**: Files
- **David / Chris / Jack / admins**: every Analysis tab — Daily Scale Report, Intercompany Rolloff, Consolidated Rolloff, Scale KPIs, Rolloff Visual, Xfer Station, Business Line Analysis
- **David / Chris / admin**: **Dispatch group → Rolloff Queue** (the dispatcher view)
- **David only**: Workflow tab (Action Items / project management) **and Routing group → Residential Routing tab**
- **David + Chris + admin (per-user nav variant):** Roll-offs tab moves *into* the Client Management group (rather than sitting standalone). Other users still see Roll-offs as a top-level item.

**Nav grouping:** the side rail uses two collapsible groups — **Client Management** (Client Lookup / Add Client / Reports, plus Roll-offs for David/Chris/admin) and **Analysis** (the seven analysis tabs above). Standalone tabs sit beneath the groups: Roll-offs (for non-D/C/admin users), Files, Workflow, Import. Group state persists in localStorage (`helm_nav_groups`) and the entire side rail can be collapsed via the chevron toggle in the topbar (state persisted as `helm_nav_collapsed`).

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
| route_note | TEXT | Optional per-client route note; rendered inline on every report |
| rate1 | NUMERIC(8,2) | Per-pickup price: regular trash pickup |
| rate2 | NUMERIC(8,2) | Per-pickup price: extra bag of trash |
| rate3 | NUMERIC(8,2) | Per-pickup price: per bag of recyclables |
| rate4 | NUMERIC(8,2) | Per-pickup price: intermittent pickup (rarely used) |
| rate5 | NUMERIC(8,2) | Per-pickup price: cardboard armload |

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
| action | TEXT | `Skip Day`, `1XER`, `1X WK`, `2X WK`, `3X WK`, `LPU`, `Special Pickup`, `Complaint`, `Misc` |
| action_date | DATE | Date the action applies (nullable for Misc) |
| note | TEXT | Free-text content |

**`rolloffs`** — Construction dumpster tracking
| Column | Type | Notes |
|---|---|---|
| id | SERIAL (PK) | Auto |
| date | DATE | Date placed |
| type | TEXT | `AJ`, `REIS`, `30YD`, `40YD`, etc. |
| tare_id | TEXT | Sticker ID on the physical box (e.g. `AJ55`, `REIS12`) — pinpoints which exact dumpster is at this location |
| customer | TEXT | Customer name |
| address_number | TEXT | Street number |
| street | TEXT | Street name |
| phone | TEXT | Job-site contact phone, normalized to `XXX-XXX-XXXX` on save |
| notes | TEXT | Special instructions |
| monthly_tip | BOOLEAN | Monthly rental tipped flag (default FALSE) |
| deleted | BOOLEAN | Soft delete flag |

**`dispatch_tickets`** — Rolloff request queue (Office → Dispatcher → Docket flow)
| Column | Type | Notes |
|---|---|---|
| id | BIGSERIAL (PK) | Auto |
| ticket_number | TEXT (UNIQUE) | `ROLL0001`, `ROLL0002`, … sequential |
| created_at | TIMESTAMPTZ | When the office hit Send to Dispatch |
| created_by | TEXT | Username of the office staff |
| entry_kind | TEXT | `existing` (use existing rolloff data) or `new` (new site) |
| customer_name | TEXT | |
| address | TEXT | |
| box_id | TEXT | Tare ID like `AJ55` if known, otherwise just the type |
| phone | TEXT | Normalized `XXX-XXX-XXXX` |
| job_type | TEXT | `Delivery`, `Empty and Return`, `Move on Site`, `Empty and Home` |
| notes | TEXT | Free-form for the dispatcher |
| status | TEXT | `queued` or `completed` |
| completed_at | TIMESTAMPTZ | When the dispatcher checked it off |
| completed_by | TEXT | Username of the dispatcher who closed it |

**`complaints`** — Customer complaints with case-management lifecycle (David's inbox)
| Column | Type | Notes |
|---|---|---|
| id | BIGSERIAL (PK) | Auto |
| client_id | TEXT | Client the complaint is about |
| client_name / client_address / client_phone / client_email / client_route / client_days | snapshot fields | Frozen at time of logging so case files don't change if the client record changes later |
| type | TEXT | `DRIVER` / `BILLING` / `MISSED_STOP` / `OTHER` |
| driver_name | TEXT | Required for `DRIVER` complaints; plain text input (no autosuggest). Powers the Monthly Complaint Summary's driver sub-grouping. |
| notes | TEXT | Rep's free-text description of the complaint |
| logged_by | TEXT | Display name of the rep who logged it |
| logged_at | TIMESTAMPTZ | When it was logged |
| status | TEXT | `new` (untriaged) / `case_open` / `resolved` / `ignored` |
| ignored_reason / ignored_at / ignored_by | — | Required when status=ignored |
| case_opened_at / case_opened_by | — | When David opened a case |
| resolved_at / resolved_by / resolution_notes | — | When David closed the case |

**`complaint_actions`** — Per-case timeline of standardized steps
| Column | Type | Notes |
|---|---|---|
| id | BIGSERIAL (PK) | Auto |
| complaint_id | BIGINT (FK) | References complaints.id, ON DELETE CASCADE |
| action_type | TEXT | `opened` / `called_client` / `spoke_to_driver` / `spoke_to_rep` / `note` / `resolved` / `reopened` |
| notes | TEXT | Free-text detail for this step |
| performed_by | TEXT | Display name |
| performed_at | TIMESTAMPTZ | Auto |

**`bulky_pickups`** — Bulky / prohibited items left behind on a residential route (David + admin only)
| Column | Type | Notes |
|---|---|---|
| id | BIGSERIAL (PK) | Auto |
| client_id | TEXT | Nullable — not every address is a HELM client |
| address | TEXT | Snapshot of the street address at log time |
| client_name | TEXT | Snapshot (when client_id is set) |
| reporting_driver | TEXT | Free text — which driver flagged it |
| notes | TEXT | What was left out (e.g. "3 mattresses + a fridge") |
| photos | JSONB | Array of `{path, uploaded_at, uploaded_by}` pointing into the `helm-files` Supabase Storage bucket under `bulky/YYYY-MM/...` |
| received_at | DATE | Date the driver originally reported it. Drives the calendar view; back-datable so David can catch up on a backlog. |
| logged_at | TIMESTAMPTZ | When the record was created in HELM |
| logged_by | TEXT | Display name of whoever logged it |
| status | TEXT | `pending` or `completed` |
| picked_up_at / picked_up_by | — | Set when Mark Picked Up is clicked |

**`beacon_accounts`** — BEACON CRM accounts (new business + lost business + exit pipeline)
| Column | Type | Notes |
|---|---|---|
| id | BIGSERIAL (PK) | Auto |
| client_id | TEXT | Nullable HELM clients link (free-text accounts allowed too) |
| business_name | TEXT | Required |
| account_number | TEXT | The customer's billing acct # |
| contact_name / contact_phone / contact_email | TEXT | Decision-maker info |
| original_start_date | DATE | When they originally started service with us |
| effective_date | DATE | When the new/lost event happened (required) |
| event_type | TEXT | `new` or `lost` (CHECK) |
| line_of_business | TEXT | `residential` / `commercial_route` / `commercial_rolloff` / `walk_in` / `intercompany` / `other` |
| monthly_dollar_amount | NUMERIC(10,2) | Recurring monthly revenue |
| sales_rep | TEXT | HELM user display name (dropdown excludes the literal `admin`) |
| reason | TEXT | Why they signed / why they left |
| competitor | TEXT | If lost to a competitor — who |
| pipeline_stage | TEXT | Contextual. For lost: `new_loss` → `first_contact` → `engaged` → `negotiating` → `won_back` / `permanent`. For new: `new` → `active` / `at_risk` / `won_back` |
| notes | TEXT | Additional free-form notes |
| next_review_date | DATE | When to revisit |
| archived | BOOLEAN | Soft-hide from active views |
| created_at/by, updated_at/by | — | Audit |

**`beacon_outreach`** — Outreach attempts logged against a BEACON account (exit-pipeline timeline)
| Column | Type | Notes |
|---|---|---|
| id | BIGSERIAL (PK) | Auto |
| account_id | BIGINT (FK) | References beacon_accounts.id, ON DELETE CASCADE |
| outreach_type | TEXT | `phone_call` / `voicemail` / `email` / `sms` / `in_person` / `mailer` / `note` |
| outreach_date | DATE | Required |
| performed_by | TEXT | HELM user display name |
| outcome | TEXT | `no_answer` / `voicemail` / `spoke` / `interested` / `declined` / `won_back` / `other` |
| notes | TEXT | What happened |
| next_step_date / next_step_note | DATE, TEXT | Follow-up |

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

### Business Line Analysis Tables

**`bla_staff`** — drivers + helpers roster
| Column | Type | Notes |
|---|---|---|
| id | BIGSERIAL (PK) | |
| name | TEXT | |
| role | TEXT | `driver` or `helper` (CHECK constraint) |
| active | BOOLEAN | Defaults TRUE |
| created_at | TIMESTAMPTZ | |

**`bla_resi_entries`** — daily Residential entries (one per driver per slip)
| Column | Type | Notes |
|---|---|---|
| id | BIGSERIAL (PK) | |
| entry_date | DATE | |
| driver_id | BIGINT (FK -> bla_staff) | ON DELETE SET NULL |
| driver_minutes | INT | |
| helper_minutes | INT | |
| net_weight_lbs | NUMERIC | from landfill slip |
| landfill_minutes | INT | |
| landfill_trips | INT | Defaults 1 |
| total_miles | NUMERIC | |
| routes | JSONB | `[{name, stops, helper_id}, ...]` |
| notes | TEXT | |
| created_at, updated_at | TIMESTAMPTZ | |

**`bla_comm_entries`** — daily Commercial entries (same shape as Residential, helpers supported)

**`bla_rolloff_manual`** — manual ST/OT hours per driver per day
| Column | Type | Notes |
|---|---|---|
| entry_date | DATE (PK) | |
| driver_hours | JSONB | `[{driver_id, st_hours, ot_hours}, ...]` |
| notes | TEXT | |
| updated_at | TIMESTAMPTZ | |

**`bla_xfer_manual`** — manual Xfer Station fields per day
| Column | Type | Notes |
|---|---|---|
| entry_date | DATE (PK) | |
| trlrs_loaded | INT | |
| tons_loaded | NUMERIC | |
| loads_hauled | INT | optional override of Vinagro auto-pull |
| tons_hauled | NUMERIC | optional override |
| notes | TEXT | |
| updated_at | TIMESTAMPTZ | |

### Residential Routing Tables (David only)

**`route_assignments`** — Per-(client, day) route position + driver note. Source of truth for the Routing → Residential Routing tab.
| Column | Type | Notes |
|---|---|---|
| client_id | TEXT (FK) | References clients(client_id), ON DELETE CASCADE |
| day_of_week | SMALLINT | 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat |
| route | SMALLINT | Route number (typically 1-14) |
| position | SMALLINT | Driving order within (day, route); lower = earlier stop |
| route_note | TEXT | Optional driver instruction ("BEHIND HOUSE - DONT TAKE ANY RECYCLES") |
| source | TEXT | `delta` for PDF imports, `manual` for hand-entered rows |
| created_at, updated_at | TIMESTAMPTZ | |

PK: `(client_id, day_of_week)`. Index: `(day_of_week, route, position)` for fast Routes-tab queries.

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
  - **Service Rate Sheet card** (Tip Fee $250, Special Tonnage $480/ton, Standard Tonnage $525/ton, **Insulation $575/ton**, Rolloff Delivery $100, **40 Yard Delivery $200**, Pile Pickup $160/hr per worker, Metal Tonnage Disposal $125/ton)
  - **My Notes card** — per-user free-form textarea, auto-syncs to `user_notes` table (cross-device)
  - Rate Sheet and My Notes render side-by-side on desktop (collapse to stacked under 780px)
- **Tokenized search** — "viola howard" matches "HOWARD, VIOLA" regardless of word order
- Inline client card with name + company tag, Acct #, address, phone, **email** (clickable `mailto:` link in teal when set, "No email on file" placeholder when missing), pickup days, status, autopay, **route pill**, Edit button
- Notes support 9 categories (Skip Day, 1XER, 1X WK, 2X WK, 3X WK, LPU, Special Pickup, **Driver Comment**, Misc). Complaints are no longer a note category — they have their own dedicated flow (see Complaint Pipeline below).
- **Driver Comment** is the category for things drivers call in about during their route ("bin was blocked", "client put extra trash out", etc). Reps log them on the relevant client card as they come in, then run the Driver Comments Report (see Reports tab) in the afternoon to roll through them and follow up with affected clients. Orange chip + orange border to visually distinguish from other note types.
- **Edit Client** button sits on the top-right of the info column, in line with the address/email block (above the divider that precedes the Pickup Days tiles). **Log Complaint** is a red button at the bottom right of the info column where Edit Client used to be.
- **Complaint entries appear in the Notes history alongside regular notes** — same chronological timeline. They render with a red left border + pink background tint, a `COMPLAINT — TYPE` chip, and a small status pill (NEW / CASE OPEN / RESOLVED / IGNORED). If the case was resolved, a green resolution footer shows who resolved it and the resolution notes; if ignored, a gray footer shows the ignore reason. Complaint entries are read-only in this view (no × delete button) — reps can see them but can't modify them. Gives reps a single "what's happened with this client" view when the client calls in.
- Inline Yes/No delete confirmation on notes

### Add Client (all users)
- Company picker (REIS / SANTOS) required before any other fields
- First-digit classification: 2xxxxx → REIS, 3xxxxx → SANTOS
- **Next-ID logic:** `max(per-company floor, highest matching acct in HELM) + 1`. Floors are in `ACCT_BASELINE_BY_CO`: **REIS = 209742** (last added in the legacy NetWork software as of 2026-05-07; new HELM-only adds start at 209743), **SANTOS = 300000**. Strict +1 from there — the prior +51 first-of-session safety buffer was retired since HELM is now in sync with the legacy export. Bump the floor whenever another batch of legacy adds is ingested so HELM never re-uses an ID that exists in NetWork.
- Day toggle buttons (Mon-Sat) for multi-day pickup
- Duplicate detection by address or name
- **Account # numeric-only validation** — guards against the "I tabbed past Account # and typed the name into the wrong field, so the client got saved with their last name as the ID" failure mode. The Account # input has `autocomplete="off"`, `inputmode="numeric"`, `pattern="[0-9]*"`, and `addClient()` rejects any non-digit value with a clear toast.

### Edit Client
- Name / address / phone / email / pickup days / **route 1-14 dropdown** / autopay
- Routes chosen from "Select Route" dropdown; renders as a navy pill on the card
- **Route Note** — when a route is selected, an optional textarea slides in beneath the route dropdown ("leave bins on left side", "gate code 4321", etc.). Auto-clears if the user removes the route. Saved to `clients.route_note` and surfaced inline (`📋` italic teal line beneath the address) on the Daily Action Report, Notes Added Today, and Everything Report — both screen and print versions.
- **Per-day Routes editor (all users)** — *replaces* the single Route + Route Note section for everyone. Renders one row per currently-toggled-on pickup day (re-renders live when a day is toggled), each with a Day label, Route dropdown (no route / R1-R14), and a route-note text input. Pre-populates from existing `route_assignments` rows. On save: upserts a row per selected day, deletes rows for days that were toggled off. Also syncs `clients.route` and `clients.route_note` to the first selected day's values so any legacy code path that still reads the single-field fallback gets something sensible. *(Was David-only when first shipped on 2026-05-07; rolled out to all users on 2026-05-14 after Esme flagged that she couldn't set different routes for a 3x/wk client.)*
  - **Pair auto-fill**: setting route or route-note on one day of a standard pickup pair (Mon↔Thu, Tue↔Fri, Wed↔Sat) auto-copies the value to the partner *when the partner is selected as a pickup day AND the partner's same field is empty*. Never overwrites manually-set values. So a 2x/wk Wed+Sat client gets Sat filled automatically when you pick Wed's route; a 3x/wk Mon+Wed+Sat client gets Wed↔Sat paired but Monday stays standalone (its pair Thursday isn't selected).
- **Editable Account #** — Account # is now an editable input at the top of the Edit Client form (replaces the read-only header label). Rules: digits only, must not collide with an existing acct, and a `confirm()` dialog explains the migration before proceeding. Implemented as a true PK rename via `migrateAccountId(oldId, newId)`: copies the row to the new `client_id`, re-points every `notes`, `skips`, and `route_assignments` row from old → new, then deletes the old row. On any sub-step failure, attempts to roll back the new row. Uses for: fixing a client whose Account # got accidentally saved as their last name (or anything else wrong) when they were first added.
- **Delete Client (Danger Zone)** — bottom of the Edit Client form. Pre-counts related rows (notes / skips / route_assignments) and shows the totals in the confirmation prompt. Requires the user to *type the exact account #* to confirm — `confirm()` is too easy to dismiss. Deletes child rows first (notes → skips → route_assignments) then the client row. Logs to `activity_log` with the deleted name + address for audit trail. Clears `activeClient`, the inline card, and the search field, landing back on the empty state.
- **Phone normalization on save** — Edit Client and Add Client both run user-typed phones through `normalizePhone()` before the DB write. `(508) 228-3938`, `508.228.3938`, `5082283938`, `+1 508-228-3938`, etc. all save as `508-228-3938`. Anything that's not a clean 10-digit (or 11-digit `1`-prefixed) number passes through unchanged so we never silently lose data.
- **Rate Schedule (per-pickup)** — five inputs covering R1 trash pickup, R2 extra bag, R3 recycle bag, R4 intermittent pickup (rarely used), R5 cardboard armload. Stored as `clients.rate1` … `rate5`. Surfaced on the Lookup card as a 5-cell strip with running Total below the info-tiles. Mirrors the legacy NetWork software's R1-R5 view. Rates vary per address — they are not uniform across clients. *(Was David-only when first shipped on 2026-05-05; rolled out to all users on 2026-05-14 alongside the per-day routes rollout.)*

### Reports (all users)
Seven cards on the Reports tab (the last two are gated to David + Esme):

1. **Daily Action Report** — actionable notes for a specific date
   - Split by REIS / SANTOS / Other (first-digit classification)
   - **Grouped by Route** within each company (Route 1, Route 2, … Route 14, then "No Route Assigned"); rows sorted by account # within a route
   - **Per-day route resolution:** the route used for grouping is looked up in `route_assignments` for `(client_id, day_of_week_of_action_date)`; falls back to `clients.route` if no per-day override exists. Same for the inline `📋` route_note. So a multi-day client with Mon=R4 / Wed=R2 / Sat=R2 (e.g. acct 208849) has its Mon notes land under R4 and its Wed/Sat notes under R2, automatically.
   - Columns: #, Acct, Action (colored chip), Name, Address, Note
   - Print popup mirrors the on-page layout in an Arial print template

2. **Notes Added Today** — every note input on a specific date (filters by `notes.created_at`, not `action_date`, so future-dated notes still show)
   - Section per **For Date** (the date the note's action falls on); within each section, **sorted by Route** ascending (no-route last; ties broken by acct #)
   - Date section headers include the day of week ("For Wednesday, Apr 29")
   - Columns: # / Route / Acct / Co (single-letter chip) / Action / Client / Address / Note / By / Time
   - **Post-generation filter bar** — same shape as Everything Report (Action / By / Route / Company / Search). Single-select dropdowns populated from the fetched data; filters apply client-side; Clear button resets; print honors active filters.
   - Summary strip of action-type counts at the top (reflects the filtered set)
   - Print version uses **enlarged date headers** (≈20px h2) so CSRs can scan from arm's length

3. **Driver Comments Report** — every Driver Comment note logged on the selected day, chronologically ordered (oldest first so reps work through them in input order)
   - Columns: # · Time · Acct · Client · **Phone (large, monospace, click-to-call)** · Address · Comment · By
   - Date picker defaults to today
   - Print button generates an Arial print sheet with the orange "Driver Comments" branding — phone number is rendered in 14px monospace so it's easy to read while dialing
   - Workflow: drivers call in during the morning route, reps log Driver Comment notes on the relevant client cards, then run this around 2pm to follow up with each affected client. Replaces the previous "scan Notes Added Today and filter to Driver Comment" workflow with a dedicated, dial-ready report.

4. **Everything Report** — every note ever input, with author column
   - **Custom date range filter** on `created_at` (when the note was input). `Input from` + `Input to` pickers + `Last 7d / 30d / 90d / All time` quick presets. Either side may be left blank for an open-ended range.
   - **Post-generation filter bar** (gray strip above the results) — single-select dropdowns for Action / By (user) / Route 1–14 + No Route / Company (REIS/SANTOS/Other) + a free-text search across acct # / name / address / note / user / action. Dropdown options are populated from the actual fetched data (so the user list only shows people who logged notes in this range). Filters apply instantly client-side — no re-query. A "Clear" button resets all filters; a "N of M match" label shows how many rows the active filter set yields.
   - Same layout as Notes Added Today (For Date sections, sorted by Route within), plus a **By** column showing which user logged each note
   - Header strip shows the chosen range and the For-date span across the result
   - Print version honors the active filters — what's on screen is what prints — and includes the filter description in the print header so the printout is self-explaining

5. **Export Clients to Excel** — column-picker export
   - Toggleable columns: Account # / Company / Name / Address / Phone / Email / Pickup Days / Route / Status / Autopay / Date Added
   - Filters: Company (REIS / SANTOS), Status (Active / Paused), Email (with / without — useful for gap-hunting), Route (1-14 or "no route")
   - Downloads as `HELM_Clients_YYYYMMDD.xls`

6. **Monthly Complaint Summary** *(David + Esme only)* — calendar-month rollup
   - Month dropdown (current + 23 prior months); defaults to **previous month**
   - Status mix strip at the top (NEW / CASE OPEN / RESOLVED / IGNORED counts)
   - One section per type (DRIVER / BILLING / MISSED STOP / OTHER) with a count header
   - **Driver section sub-groups by `driver_name`** — each driver gets their own orange-tinted block showing total count, status mix, and the individual complaints. Drivers sorted by complaint count descending so the noisiest driver tops the list. Complaints without a driver name fall into a "(No driver named)" bucket.
   - Each complaint row shows date · acct · client · status pill · who logged it · the notes, plus a green resolution footer if resolved or a gray ignore-reason footer if ignored
   - Print button generates a clean printable monthly archive with the same structure
7. **Complaint Report** *(David + Esme only)* — weekly view of every Complaint note logged on a client card
   - Week navigator: ‹ / › arrows, Monday date picker, This Week / Last Week shortcuts
   - Summary strip with DRIVER / BILLING / OTHER counts (reflects the filtered set)
   - **Post-generation filter bar** — Type (DRIVER/BILLING/OTHER) / By (user) / Search (free text). Filters apply instantly; print honors them.
   - Columns: # · Logged (date + time) · Type (DRIVER/BILLING/OTHER/MISSED_STOP chip) · Acct · Client · Address · Complaint · By (staff who logged it)
   - Print button opens a red-themed Arial print sheet titled "HELM — Complaint Report"
   - **Complaints are hidden from every other report** (Daily Action, Notes Added Today, Everything Report — both screen and print). The only places complaints surface in HELM are this report and the Complaint Pipeline.
   - Now reads from the **`complaints` table** (not `notes`) so the weekly view includes all the case-management metadata even though Esme can't act on it.

### Complaint Pipeline (logging = all users, inbox/case mgmt = David only)
A dedicated workflow for tracking and resolving customer complaints. Complaints used to be a category in the notes form; they've been promoted to a first-class table because they need triage, case-management, and an audit trail of how each one was handled.

**Logging a complaint (any user):**
- Red **Log Complaint** button at the bottom-right of every client card opens a centered modal
- Auto-fills the client snapshot (name / acct / address / phone / email / route / pickup days) — frozen at log-time so the case file doesn't drift if the client record changes later
- **Complaint type picker** (required): `Driver` / `Billing` / `Missed Stop` / `Other`
- When type = **Driver**, a `Driver involved` text input appears (required). Autosuggests from active drivers in `bla_staff` and from any historical `driver_name` values already in `complaints`, so spellings stay consistent. Type a new name if the driver isn't on the roster yet.
- Notes textarea is **hidden until a type is chosen** (prevents rep from typing without classifying first)
- On Submit: row inserted into `complaints` with `status='new'`; David's inbox badge increments

**David's Inbox (icon next to "David" in the topbar):**
- iMessage-style red badge shows count of complaints with `status='new'` (those still needing triage)
- Badge auto-refreshes on tab focus + every 60s; clears when complaints leave the `new` state
- Clicking the icon opens an **email-style master/detail modal**:
  - **Left list** — filter chips at top (New / Open Cases / Resolved / Ignored / All), each with a count. List rows show client name, type chip, status chip, who logged it, when, and a 2-line preview of the notes.
  - **Right detail** — full client snapshot, original complaint, and a status-dependent action area:
    - `new` → ▸ Open Case / Ignore buttons
    - `case_open` → action log timeline + + Add Entry button + ✓ Mark Resolved button
    - `resolved` → resolution banner + read-only action log
    - `ignored` → ignore-reason banner
  - **Week navigator at the top of the sidebar** — ‹ / › arrows + "This Week" / "All" shortcuts. Default is All weeks. When a specific week is selected, the chip counts and list rows scope to that Mon–Sun window so the status chips never lie about what's available.
  - **🖨 Print Week** button (enabled when a specific week is selected) writes a single document containing every complaint logged that week as its own page-broken section — client snapshot, original notes, action log, resolution/ignore details. Includes a cover sheet with by-type and by-status totals. Use this for the weekly archive print.
  - **Print** button on the detail pane writes a single-case printable file (snapshot + original + every action log entry with timestamp + by-whom + notes)

**Opening a case:**
- Status flips to `case_open`; first `complaint_actions` entry written as `opened`
- David adds entries using a small inline form: action type dropdown (Called Client / Spoke to Driver / Spoke to Rep / Note) + optional notes field. Each entry is timestamped with who added it.
- "✓ Mark Resolved" opens a modal requiring resolution notes; status flips to `resolved`, a final `resolved` action entry is written

**Ignoring a complaint:**
- "Ignore" opens a small modal that **requires a reason** (no empty submit)
- Status flips to `ignored`; reason + when + by-whom are saved on the complaint row
- Stays visible under the Ignored filter — nothing is deleted; full audit trail preserved

**Migration on rollout:** The SQL migration block (see Supabase Setup) moves every existing `Complaint - DRIVER` / `Complaint - BILLING` / `Complaint - OTHER` note from `notes` into the new `complaints` table as `status='new'`, then deletes the source notes so they don't get double-counted.

### Roll-offs (all users)
- Editable spreadsheet with sortable columns, soft delete + undo, show/restore deleted
- **Columns:** Date · Type · **Tare ID** · Customer · # · Street · **Phone** · Monthly Tip · Notes
- **Tare ID** — sticker number on the physical box (`AJ55`, `REIS12`, `30YD7`, `40YD2`, `SANTOS3`). Auto-uppercased on save, monospace render. Datalist autosuggests previously-used tare IDs (alphanumeric-aware sort). Powers the "which physical box is at this address" lookup that the new Dispatch Input form auto-fills from.
- **Phone** — job-site contact number. Saved through `normalizePhone()` so `(508) 228-3938`, `508.228.3938`, `5082283938`, `+1 508-228-3938` all canonicalize to `508-228-3938`. The input is reflected back to the cell on save so users see the canonical form.
- **Customer + Street + Tare ID auto-suggest** — all three fields use a `<datalist>` populated from previously-used values; type a few letters then Tab/Enter to accept
- **Monthly Tip** column — click the pill to toggle No (gray) ↔ Yes (green)
- **Reset Monthly Tips** button — yellow-highlighted, clears all tipped flags with confirmation
- **Banner** "⚠ RESET MONTHLY RENTAL FEES" appears on the **last day of each month** if any tipped rolloffs remain (configurable via `ROLLOFF_TIP_RESET_DAY`). Clicking Reset auto-hides the banner
- **Export Untipped** button — `.xls` of all non-deleted, untipped rolloffs. Output sheet has two trailing empty columns (manual day-count + auto `=prev*4` charge formula); the legacy "days on site" pre-calculated column was removed in favor of this manual entry pattern
- **Export Print Sheet** button — alpha-by-company `.xls` matching the legacy Times New Roman template, with 20 blank rows for handwriting

### Daily Scale Report (David / Chris / Jack / admin)
Top-level Analysis tab — replaces the old IRR Scale → Daily Scale Report sub-view.
- Drag/drop `.xls` upload
- **Review IC Tickets modal** (post-parse) lists Island / East End / **Delta** tickets with three checkbox columns:
  - **Exclude** — drop the ticket entirely (tons/tickets/revenue removed)
  - **Pile Pickup** — Island/East End only; move to walk-in
  - **Walk In** — any IC ticket that's actually a walk-in; move to walk-in
  - Exclude wins if multiple boxes are checked
- Driver hours prompt — asks for Island Rubbish driver count + hours (HH:MM input)
- Auto-save — raw .xls saved to Files → shared "Daily Scale Reports" folder
- Generates a formatted **daily email** in a five-section layout. Identical structure renders both as the in-app preview and as the email body the Copy/Gmail buttons emit. Uniform 5-row format per section (Today / MTD / MTD YoY / YTD / YTD YoY), accounting-paren convention for negatives, positive percent deltas in green:
  - **Internal Volume** — rolloff tonnage (Reis + Island + East End)
  - **External Volume** — walk-in tonnage
  - **Total Volume** — Internal + External (inbound consolidating row)
  - **Outbound** — Vinagro tonnage to mainland
  - **Revenue** — total $ + $/ton appended inline (e.g. `$525.27/ton | $733,706.86`); YoY rows show absolute $ delta + percent (e.g. `+$192,482.54 | +35.6%`); Internal/External rev/ton sub-rows under each main row
- Today rows + all main Revenue rows get a thin gray (`#f0f0f0`) row highlight; section titles underlined; bolded Today rows on every section
- Copy to clipboard / Gmail draft creation
- Historical report viewer (click any past date)
- **Historical bulk import** — upload date-range .xls to upsert history

### Intercompany Rolloff (David / Chris / Jack / admin)
Top-level Analysis tab — formerly the IRR Scale → Intercompany Rolloff Report sub-view.
- **Columns mirror the daily email** (so the on-screen table and the daily email read the same):
  - `Today` · `MTD` · `MTD YoY` · `YTD` · `YTD YoY`
  - YoY columns display signed deltas with signed percent change (e.g. `+432.50 tons | +35.6%` or `($45,200.10) | (8.4%)`)
  - Data comes from `irrLoadYTD()` — the same helper the daily email itself calls, so values reconcile exactly
- **Rows mirror the daily email's section layout**:
  - **Internal Volume** — Rolloff Tonnage (Reis + Island + East End)
  - **External Volume** — Walk-In Tonnage
  - **Total Volume** — Total Inbound (Internal + External)
  - **Outbound** — Vinagro Tonnage
  - **Revenue** — Internal Revenue, External Revenue, Total Revenue, plus indented `Internal $/ton` / `External $/ton` / `Overall $/ton` ratio sub-rows. Ratios aggregate numerator + denominator separately, then divide at display time
- **Single-date navigation** — prev day arrow, date picker, next day arrow, Today shortcut. Defaults to today.
- **Print** — print preview (mirrors the on-screen table directly, so it picks up the new layout automatically)
- **Scale Monthly Review** button (gold) — opens the month-end summary modal (see Scale Monthly Review below)
- *(Mon-Sat columns + WTD + MTD/YTD aggregate columns + week navigation + year toggle + Export File button were retired on 2026-05-14 in favor of the daily-email-shaped layout. Quarterly Report / Yearly Report / Projections / per-company REIS / ISLAND / SANTOS sub-blocks were all retired earlier. Underlying functions remain in the codebase but are unreachable from the toolbar.)*

### Consolidated Rolloff (David / Chris / Jack / admin)
Top-level Analysis tab — formerly the IRR Scale → Consolidated Rolloff sub-view.
- Weekly table combining Reis + Island + East End
- Columns: Mon–Sat + Total
- Rows (auto): Date, Revenue, Loads, Tons, Loads/Day, Rev/Load, Tons/Load
- Rows (manual, editable): # of Drivers, ST Hours, OT Hours
- Rows (derived, auto-calc with manual override): Total Hours, Hrs/Drvr, Hrs/Load
- Manual entries saved to `crc_weekly_manual` (shared across users via Supabase)
- Prev/next week arrows, date picker, **Export to Excel** button
- **2025 Historical Rolloff/C&D table** below the weekly grid — 12 month columns (Jan→Dec) with 4 rows: `Loads/Month` (rolloff), `Rev/Load (Rolloff)`, `C&D Loads/Month` (rolloff + walk-ins), `Rev/Load (C&D)`. Sourced from `irr_reports` for calendar 2025

### Scale KPIs (David / Chris / Jack / admin)
Top-level Analysis tab — rebuild of the old IRR Scale → KPIs & Tools (formerly "Dashboard") sub-view.
- **Three explicit modes** in a strip at the top: **Week** / **Month** / **Custom**
  - **Week** mode: Mon-Sat day columns + WTD + MTD + YTD with Prev/Next week navigation + date picker
  - **Month** mode: weekly buckets W1–W5 (days 1-7, 8-14, 15-21, 22-28, 29-end) + Month + YTD with month dropdown (current year + prior 2 years)
  - **Custom** mode: from/to date pickers, single Range column + YTD context
- **SEC-style table polish:** dark navy section header bars, zebra-striped data rows (`#fafbfd`), tinted aggregate columns (`#f3f6fa`), bold "Total" rows with thin top border, left-bordered YTD column to read as context, monospace right-aligned numbers
- **Six sections** as rows:
  1. **Rolloff Totals** — Loads, Tons, Tons/Load, Rev/Load, Total Revenue (bold)
  2. **Walk-Ins** — Tickets, Tons, Avg Tons/Ticket, Rev/Ton, Total Revenue (bold)
  3. **All Inbound (Rolloff + Walk-Ins)** — Loads/Tickets, Tons (volume only)
  4. **Outbound (Vinagro)** — Loads, Tons, Tons/Load
  5. **Total Revenue** — Rolloff Revenue, Walk-In Revenue, Rev/Ton (All Inbound), Total Revenue (bold)
  6. **Rolloff Breakdown** — Empty/Return + Double Drop (Reis), Delivery (Reis), Rev/Load Empty/Return; sub-row counts: Reis / Island Rubbish / Santos (East End)
- **Generate Report** — drops a PDF + XLSX matching the current window into the shared Files folder `Scale Reports`. Reuses the Scale Monthly Review export pipeline so output formatting is consistent across week / month / custom periods.
- **Print** — opens a styled printable view of the grid
- **Driver Hours Entry form** — Date + HH:MM input, saves to `irr_reports.driver_hours` for that date

### Scale Monthly Review (button on Intercompany Rolloff)
Month-end summary modal launched from the gold "Scale Monthly Review" button on the Intercompany Rolloff toolbar.
- Defaults to the previous calendar month; month dropdown lets you pick any prior month back two years
- Sections (consistent with the daily email and Scale KPIs grid via shared `kpiAggregate`):
  1. Rolloff Totals (Rev/Load, Total Revenue, Loads, Tons/Load)
  2. Walk-Ins (Tickets, Total Tons, Total Revenue, Rev/Ton, Avg Tons/Ticket)
  3. **All Inbound (Rolloff + Walk-Ins)** — consolidating block whose Total Revenue equals what the daily email's Revenue MTD line shows on month-end
  4. Vinagro (Outbound) — Loads, Total Tons, Avg Tons/Load
  5. Rolloff Breakdown — Empty/Return + Double Drop (Reis), Delivery (Reis), Rev/Load Empty/Return; per-company counts (Reis, Island, Santos)
- **Email** button copies a rich HTML version to clipboard for paste-into-Gmail
- **Save to Files (PDF + XLSX)** button auto-creates a shared `Scale Monthly Review` folder if missing and drops both formats in
- **Download PDF** / **Download XLSX** for local download

### Rolloff Visual (David / Chris / Jack / admin)
Top-level Analysis tab — stock-chart-style trend studio modeled on Schwab/Fidelity charts.
- **Single chart** with a metric dropdown, series-mode dropdown (Combined / By Company / Both), and a "Compare to Last Year" overlay toggle
- **Time-frame strip** above the chart: `1W / 1M / 3M / 6M / YTD / 1Y / 2Y / ALL / Custom` — one click swaps the visible window
- **Dark stock-terminal theme** (panel `#0e1019`, brightened series colors, soft white grid)
- **Volume sub-chart** at the bottom: faint blue bars showing daily Loads (combined activity), pinned via stacked Y-axes (3:1 weight) so the main chart gets ~75% of the height and volume gets ~25%
- **Chart toolbar** in a header strip above the chart: ↺ Reset zoom · ⛶ Fullscreen pop-out (94vw × 90vh modal). Toolbar lives outside the canvas so it never covers data.
- **Stock-chart interactions** (powered by `chartjs-plugin-zoom`):
  - Mouse-wheel zoom on X axis
  - Click-drag to pan
  - **Click-and-drag the Y or X axis labels to rescale that axis** (TradingView-style — drag toward the chart to compress, away to expand)
  - Y-axis is clamped at zero (rolloff metrics can't be negative)
- **Period summary bar** below chart: Avg/day, Min, Max, Total (level metrics only), Days, YoY %
- **Studies** (collapsible): 7-day moving average, 30-day moving average, per-company breakdown overlay
- State persisted in localStorage (`helm_rvisual_state`); default landing = Loads · Combined · 3M · no LY · no studies

### Xfer Station (David / Chris / Jack / admin)
- **Seed balance panel** — shared "on this date the C&D room held X tons" anchor; edit button requires confirmation
- **KPI cards** — Currently in station · 30-day avg daily net · Days to capacity · YTD inbound · YTD outbound
- **Weekly grid** with prev/next + date picker — Inbound / Outbound / Net / End-of-day balance rows × Mon–Sat + WTD + MTD + YTD columns
- **Running balance line chart** (Chart.js) — full history, walking forward + backward from the seed; capacity target shown as dashed red line
- **Capacity** input field — personal target (localStorage, not shared) for % over calculations on date cells

### BEACON (separate sister app at `/beacon/`) — David / Chris / admin / Jarrett
A standalone retention/sales/outreach CRM that lives next to HELM in the same repo + same Supabase project. Reachable from HELM via the amber **BEACON** button in the topbar (visible only to the allowed users), which opens a confirmation modal before navigating to `/beacon/`. Session carries over via sessionStorage so no re-login is required.

- **Visual identity is intentionally distinct from HELM** — dark mode with amber-glow accents (lighthouse-at-night theme), Inter font, lighthouse SVG logo. Standalone PWA: separate `manifest.webmanifest` + apple-touch-icon so it gets its own home-screen icon on iPhone.
- **Auth gate**: reads `helm_auth` sessionStorage on load. If valid + user in the allow-list (`david` / `chris` / `admin` / `jarrett` + anyone with role=admin), drops straight into the app. Otherwise shows its own login form pointing at the same HELM `users` table.
- **Sales-rep dropdown** pulls from HELM's `users` table, skipping the literal `admin` username (keeps real-name reps only: David, Chris, Jackie, Esme, Hannah, Maria, Kobie, Tom, Jaime, Jack, Sharon, Jarrett).
- **Four tabs**:
  - **Dashboard** — 6 KPI cards (new this month, lost this month, net monthly change, in exit pipeline, won back, recovery rate) + recent activity feed.
  - **Accounts** — filterable list (All / New Business / Lost / Won Back / At Risk / Permanently Lost / Archived) with a tokenized search bar.
  - **Exit Pipeline** — kanban-style board with four columns (`New Loss` → `First Contact` → `Engaged` → `Negotiating`). Cards show business name, sales rep, days-since-loss, monthly $ at risk. Outcomes logged via the Outreach modal auto-advance the stage.
  - **Reports** — by sales rep, by line of business, top reasons for loss.
- **Add / Edit Account modal** — radio toggle for New vs Lost business; business-name field doubles as a tokenized HELM client search (same scoring as the homepage and Bulky modal) — pick a result to auto-fill acct # + phone, or just type a fresh business name for non-HELM accounts. Required fields: business name, effective date, event type.
- **Outreach modal** — logged against any account. Type (phone/voicemail/email/SMS/in person/mailer/note), date, outcome, notes, next-step date + note. Auto-advances pipeline_stage: `interested` → `engaged`, `declined` → `permanent`, `won_back` flips event_type back to `new` and stamps stage as `won_back`.
- **Detail modal** — shows full snapshot + stage transition buttons (stage-appropriate: lost accounts see First Contact / Engaged / Negotiating / Won Back / Permanently Lost; new accounts see At Risk / Active / Convert to Lost) + outreach timeline + Edit / Archive / Delete.
- **Mobile-first**: same safe-area-inset awareness as HELM, single-column layouts at narrow widths.
- **Code lives entirely under `/beacon/`** — index.html + manifest.webmanifest. Zero CSS/JS leakage between HELM and BEACON.

### Bulky Pickups (David + admin only) — new solo nav tab
Tracks bulky / prohibited items drivers leave behind on residential routes (mattresses, appliances, freon items, construction scrap mixed into household trash). Workflow today: a driver texts David a photo + address; David logs it here. When the pending queue hits a threshold (default 15), David sends a driver out specifically to clear the pile.

- **Mobile-first** — designed for David's iPhone. Cards stack 1-up on small screens; FAB (+) bottom-right; uses `<input type="file" accept="image/*" multiple>` so iOS opens the native Photos sheet for picking from the camera roll.
- **PWA-installable** — `manifest.webmanifest` + iOS meta tags + apple-touch-icon. On iPhone: open HELM in Safari → Share → Add to Home Screen → opens full-screen with no browser chrome, indistinguishable from a native app for this workflow.
- **Three sub-views** at the top of the tab:
  - **Queue** (default) — pending records sorted oldest-first. Banner at the top: `N of THRESHOLD pending — accumulating` (blue) flips to `READY TO DISPATCH` (amber) when the count hits threshold. Threshold is configurable inline (persisted to localStorage). Each card shows up to 3 photo thumbs + `+N` overflow, the address, client name + acct # if matched, days-since-received age pill (green/amber/red).
  - **Calendar** — month grid; cells with received records get a red count badge. Click a day → drill into the records received that date below the grid. Today is bordered teal.
  - **History** — completed pickups grouped by month, newest month first.
- **Logging flow (+ FAB)**: Date received (default today, back-datable) → Address with client autosuggest (auto-fills name + acct # on match, otherwise saves as free-text address) → Reporting driver (free text, optional) → Notes → Photo picker. Photos are client-side resized to 1600px max dim + 85% JPEG quality before upload (iPhone photos go from ~4 MB → ~400 KB) and uploaded to `helm-files/bulky/YYYY-MM/...`. Save inserts one row with the photo paths embedded in the `photos` JSONB column.
- **Detail view (tap any card)**: photo carousel (‹ / ›), client snapshot, date + driver + notes. Pending cards have a green **✓ Mark Picked Up** button; clicking flips status to `completed` and stamps `picked_up_at` + `picked_up_by`. Both pending and completed have a Delete button that also removes the photos from Storage.
- **Threshold logic**: just a visual nudge — no auto-dispatch action. David sees the banner, decides to send a run, then opens each card and marks them picked up. The v1 scope deliberately skips a "Schedule Run" action; that's a future enhancement if useful.

### Files (David + admins)
- Two sub-views: Shared / My Files
- Single-level folders (create/delete with confirmation)
- Multi-file upload, any type
- Download via 5-minute signed URLs
- Auto-saves daily .xls uploads to shared "Daily Scale Reports" folder

### Business Line Analysis (David / Chris / Jack / admin)
Top-level Analysis tab — manual KPI entry + analysis for the four business lines.
- **Top toggle:** `Input` ↔ `Analysis`
- **Input view** has four sub-tabs: Residential / Commercial / Rolloff / Xfer Station
  - **Residential & Commercial:** day entry per driver — Date, Driver (`bla_staff` dropdown + add-new), Helper Time (HH:MM), Net Weight (lbs), Landfill Time (HH:MM), # of Landfill Trips, Total Miles, plus a repeating list of Routes worked (Route name + # Stops + optional helper). Notes field. Saved entries appear below the form with Edit / → Comm (or → Resi) / Del buttons. The "→ Comm" / "→ Resi" button moves an entry to the other section.
  - **Rolloff:** Manual ST/OT hours per driver (HH:MM each) for a date. Tonnage / loads / revenue auto-pull from the Daily Scale Report.
  - **Xfer Station:** Manual Trlrs Loaded, Tons Loaded, Loads Hauled override, Tons Hauled override per date. Other fields auto-pull from the Daily Scale Report.
- **Analysis view** — four stacked accordions (Resi / Comm / Rolloff / Xfer). Click ▶ to expand → metric × Mon-Sat dates × Wk / Mo / Yr columns. Click any number to jump back to Input filtered to the entries that produced that cell.
- Click-to-edit: cell click in Analysis sends you to the Input view filtered to the contributing entries (yellow filter banner with "Clear filter").

### Dispatch group — Office → Dispatcher → Docket pipeline

A new collapsible group in the side nav with three children. The premise: when an office staff member takes a phone call for a rolloff job, they enter it into HELM. HELM creates a queue of tickets the dispatcher works through; the dispatcher then enters them into Docket (external software). As a side effect, the Roll-offs spreadsheet ("the book") gets enriched with phone + tare data over time — so the office never has to do a manual data backfill.

#### Dispatch Input (all users)
The intake form. Lives at `Dispatch › Dispatch Input`.

- **Mode toggle: Existing / New** — Existing means "this customer + site is already in the book"; New means "brand-new site (existing customer or new customer)". Default: Existing.
- **Job Type dropdown** (required): `Delivery`, `Empty and Return`, `Move on Site`, `Empty and Home`. Each gets a colored chip in the preview/queue (green / blue / orange / red).
- **Box ID** — tare # like `AJ55`, or just the type like `30YD`. Auto-uppercased on input. Datalist autosuggests from every known tare in `rolloffs`.
- **Customer Name** (required) — datalist autosuggests every distinct customer in `rolloffs` regardless of mode (so a "new site" for an existing customer like Hanley Cons still gets the name autosuggest).
- **Address** (required) — in Existing mode, the datalist is populated with that customer's existing rolloffs only (selected automatically once Name is chosen). When the typed address matches an existing rolloff exactly, the form auto-anchors: address goes readonly with a `× clear` button, and Box + Phone auto-fill from the matching `rolloffs` row (only fills empty fields — never overwrites what the user has typed).
- **Phone** — any input format normalizes to `XXX-XXX-XXXX` on save via `normalizePhone()`.
- **Notes** — free-form, optional, never autofilled.
- **Live preview card** — mirrors the queue-card shape; updates as fields fill. Customer name + today's date + current time on the header row, Box + Address + Phone + italic Notes below, Job Type as a colored chip in the corner.
- **Send to Dispatch** button — triggers the bidirectional sync (see below).

#### Bidirectional sync to "the book" (rolloffs)
Every Send to Dispatch does two writes:

1. `INSERT` into `dispatch_tickets` with the next `ROLL000N` ticket number, `created_at` = now, `created_by` = username, `status` = `queued`.
2. **Sync to `rolloffs`** based on mode:
   - **Existing + anchored:** `UPDATE` that exact rolloff row with `phone` and `tare_id` from the form — but only the non-empty fields (so an empty phone in the form never wipes a phone that's already in the book).
   - **New:** `INSERT` a fresh `rolloffs` row with everything from the form (`type` inferred from the Box ID prefix, `address` parsed into `address_number` + `street`, `phone` normalized).
3. `dispatch_tickets.entry_kind` records which mode was used.

The cache `dispatchRolloffs` is invalidated after each submit so the next form open picks up the just-written data.

#### Dispatch History (all users)
Lives at `Dispatch › History`. Read-only audit log of every ticket ever sent. Pulled newest-first (LIMIT 1000) and grouped by date with a per-day section header. Columns: Time · Ticket # · Job Type (colored pill) · Box · Customer · Address · Phone · Notes · Status (queued/completed pill) · By (username).

#### Rolloff Queue (David / Chris / admin)
Lives at `Dispatch › Rolloff Queue`. Card-grid view of dispatch tickets — what dispatchers work from before they enter jobs into Docket.

- **Layout:** header strip with `Queue / Completed` toggle pill on the right + ◀ Date ▶ navigator on the left + `Today` shortcut + "X queued ticket(s)" summary. Below: responsive card grid (auto-fill, min 290px columns, 12px gap).
- **Cards** — left-edge accent stripe in the job-type color, ticket # + time on the header row, customer name + colored job-type chip, monospace box ID + address, monospace phone, italic notes if any. Hover lifts with a soft drop-shadow. Completed cards are dimmed with a green ✓ Completed by X footer.
- **Click a card → modal** with the ticket details laid out vertically (Box / Address / Phone / Notes / By / Completed-stamp), navy header with the ticket #. For queued tickets there's a green Mark Complete button.
- **Empty-and-Home auto soft-delete** — when a ticket whose Job Type is `Empty and Home` is marked complete, the matching rolloff in the book (customer + address) is soft-deleted in the same atomic flow. Other job types complete the ticket without touching the book. The modal shows a red warning banner before the user clicks Mark Complete on an Empty-and-Home so the consequence is clear.
- **Date navigator** — local-day boundaries (UTC ranges) on the fetch query, prev/next arrows, native `<input type="date">`, and a Today shortcut button when the picked date isn't today.
- **Default-landing for admin user accounts** — fresh logins with `role='admin'` and no saved tab in localStorage land here. Once they navigate elsewhere, the saved-tab restoration takes over.

### Residential Routing (David only) — new "Routing" nav group
The first deliverable from the Master List import project. Picks a date and shows that day's residential pickup routes in driving order, sourced from the new `route_assignments` table (1,999 rows / 1,068 distinct clients across all 6 days).

- **Top controls:** prev-day `‹` button + date picker + next-day `›` button (defaults to **tomorrow**, auto-skips Sundays); Route Filter dropdown (All routes / Route 1-14); Print button
- **Body:** one section per route, each with a navy header bar (`Route N · X stops`) and a table — `# / Address / Account (name + acct # + 📋 italic teal route_note) / Days`. Driving order preserved via `position` column.
- **Print** opens a popup window with one page per route, mirroring the legacy NetWork commercial route sheet (Address | Account | Days, with driver line at top). Works for any subset (single route or all).
- **Sunday handling:** date picker can land on a Sunday but the body shows "No pickups on Sunday." Prev/next buttons skip Sunday automatically.
- **Data flow:** `route_assignments` is fetched once on first tab open, cached in memory (`resiRoutesData`). Joined in-memory with the existing `clients` array for name/address/service_day. Fast enough for ~2k rows.
- Currently **gated to user `david` only** while the feature stabilizes — other users see no Routing group in the side rail. Will roll out to office staff once skip/note/LPU lifecycle wiring lands.
- **Pending integration (next iteration):** Skip Day → hide row entirely (per user direction), 1XER for the picked date → insert row even if not normally on that route, LPU after its date → auto-flip status to Paused + drop, 1X WK / 2X WK → resume Paused → Active.

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
| ROLLOFF DELIVERY (15-yard) | $100 |
| 40 YARD DELIVERY | $200 |
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

-- Route note on clients
ALTER TABLE clients ADD COLUMN IF NOT EXISTS route_note TEXT;

-- Phone + tare_id on rolloffs (Dispatch Input phase 1)
ALTER TABLE rolloffs ADD COLUMN IF NOT EXISTS phone   TEXT;
ALTER TABLE rolloffs ADD COLUMN IF NOT EXISTS tare_id TEXT;

-- Dispatch ticket queue (Office input -> Dispatcher Queue -> Docket)
CREATE TABLE IF NOT EXISTS dispatch_tickets (
  id            BIGSERIAL PRIMARY KEY,
  ticket_number TEXT UNIQUE NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  created_by    TEXT,
  entry_kind    TEXT,
  customer_name TEXT,
  address       TEXT,
  box_id        TEXT,
  phone         TEXT,
  job_type      TEXT,
  notes         TEXT,
  status        TEXT DEFAULT 'queued',
  completed_at  TIMESTAMPTZ,
  completed_by  TEXT
);
ALTER TABLE dispatch_tickets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "dispatch_tickets_all" ON dispatch_tickets FOR ALL USING (true) WITH CHECK (true);
CREATE INDEX IF NOT EXISTS dispatch_tickets_created_idx ON dispatch_tickets(created_at);
CREATE INDEX IF NOT EXISTS dispatch_tickets_status_idx  ON dispatch_tickets(status);

-- Per-pickup rate schedule on clients (R1=trash, R2=extra bag, R3=recycle, R4=intermittent, R5=cardboard armload)
ALTER TABLE clients ADD COLUMN IF NOT EXISTS rate1 NUMERIC(8,2);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS rate2 NUMERIC(8,2);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS rate3 NUMERIC(8,2);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS rate4 NUMERIC(8,2);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS rate5 NUMERIC(8,2);

-- Residential Routing: per-day route + position + note for the new Routing tab
CREATE TABLE IF NOT EXISTS route_assignments (
  client_id   TEXT NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
  day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 1 AND 6),
  route       SMALLINT NOT NULL,
  position    SMALLINT,
  route_note  TEXT,
  source      TEXT DEFAULT 'manual',
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY(client_id, day_of_week)
);
ALTER TABLE route_assignments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "route_assignments_all" ON route_assignments FOR ALL USING (true) WITH CHECK (true);
CREATE INDEX IF NOT EXISTS route_assignments_day_route_idx
  ON route_assignments(day_of_week, route, position);

-- Business Line Analysis tables
CREATE TABLE IF NOT EXISTS bla_staff (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('driver','helper')),
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS bla_resi_entries (
  id BIGSERIAL PRIMARY KEY,
  entry_date DATE NOT NULL,
  driver_id BIGINT REFERENCES bla_staff(id) ON DELETE SET NULL,
  driver_minutes INT,
  helper_minutes INT,
  net_weight_lbs NUMERIC,
  landfill_minutes INT,
  landfill_trips INT DEFAULT 1,
  total_miles NUMERIC,
  routes JSONB DEFAULT '[]'::jsonb,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS bla_resi_entries_date_idx ON bla_resi_entries(entry_date);
CREATE TABLE IF NOT EXISTS bla_comm_entries (
  id BIGSERIAL PRIMARY KEY,
  entry_date DATE NOT NULL,
  driver_id BIGINT REFERENCES bla_staff(id) ON DELETE SET NULL,
  driver_minutes INT,
  helper_minutes INT,
  net_weight_lbs NUMERIC,
  landfill_minutes INT,
  landfill_trips INT DEFAULT 1,
  total_miles NUMERIC,
  routes JSONB DEFAULT '[]'::jsonb,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS bla_comm_entries_date_idx ON bla_comm_entries(entry_date);
CREATE TABLE IF NOT EXISTS bla_rolloff_manual (
  entry_date DATE PRIMARY KEY,
  driver_hours JSONB DEFAULT '[]'::jsonb,
  notes TEXT,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS bla_xfer_manual (
  entry_date DATE PRIMARY KEY,
  trlrs_loaded INT,
  tons_loaded NUMERIC,
  loads_hauled INT,
  tons_hauled NUMERIC,
  notes TEXT,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE bla_staff           ENABLE ROW LEVEL SECURITY;
ALTER TABLE bla_resi_entries    ENABLE ROW LEVEL SECURITY;
ALTER TABLE bla_comm_entries    ENABLE ROW LEVEL SECURITY;
ALTER TABLE bla_rolloff_manual  ENABLE ROW LEVEL SECURITY;
ALTER TABLE bla_xfer_manual     ENABLE ROW LEVEL SECURITY;
CREATE POLICY "bla_staff_all"          ON bla_staff          FOR ALL USING(true) WITH CHECK(true);
CREATE POLICY "bla_resi_entries_all"   ON bla_resi_entries   FOR ALL USING(true) WITH CHECK(true);
CREATE POLICY "bla_comm_entries_all"   ON bla_comm_entries   FOR ALL USING(true) WITH CHECK(true);
CREATE POLICY "bla_rolloff_manual_all" ON bla_rolloff_manual FOR ALL USING(true) WITH CHECK(true);
CREATE POLICY "bla_xfer_manual_all"    ON bla_xfer_manual    FOR ALL USING(true) WITH CHECK(true);

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

-- Complaint pipeline (case management — David's inbox)
CREATE TABLE IF NOT EXISTS complaints (
  id BIGSERIAL PRIMARY KEY,
  client_id      TEXT NOT NULL,
  client_name    TEXT,
  client_address TEXT,
  client_phone   TEXT,
  client_email   TEXT,
  client_route   SMALLINT,
  client_days    TEXT,
  type           TEXT NOT NULL,            -- 'DRIVER'|'BILLING'|'MISSED_STOP'|'OTHER'
  notes          TEXT,
  logged_by      TEXT NOT NULL,
  logged_at      TIMESTAMPTZ DEFAULT NOW(),
  status         TEXT NOT NULL DEFAULT 'new', -- 'new'|'case_open'|'resolved'|'ignored'
  ignored_reason   TEXT,
  ignored_at       TIMESTAMPTZ,
  ignored_by       TEXT,
  case_opened_at   TIMESTAMPTZ,
  case_opened_by   TEXT,
  resolved_at      TIMESTAMPTZ,
  resolved_by      TEXT,
  resolution_notes TEXT
);
CREATE INDEX IF NOT EXISTS complaints_status_idx    ON complaints(status);
CREATE INDEX IF NOT EXISTS complaints_logged_at_idx ON complaints(logged_at DESC);
CREATE INDEX IF NOT EXISTS complaints_client_idx    ON complaints(client_id);
ALTER TABLE complaints ENABLE ROW LEVEL SECURITY;
CREATE POLICY "complaints_all" ON complaints FOR ALL USING(true) WITH CHECK(true);

CREATE TABLE IF NOT EXISTS complaint_actions (
  id BIGSERIAL PRIMARY KEY,
  complaint_id  BIGINT NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
  action_type   TEXT NOT NULL,             -- 'opened'|'called_client'|'spoke_to_driver'|'spoke_to_rep'|'note'|'resolved'|'reopened'
  notes         TEXT,
  performed_by  TEXT NOT NULL,
  performed_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS complaint_actions_complaint_idx ON complaint_actions(complaint_id);
ALTER TABLE complaint_actions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "complaint_actions_all" ON complaint_actions FOR ALL USING(true) WITH CHECK(true);

-- One-time migration of legacy "Complaint - X" notes into the new complaints table.
-- Each migrated complaint lands with status='new' so it shows up in David's inbox
-- the first time he opens it after this SQL runs.
INSERT INTO complaints (client_id, client_name, client_address, client_phone, client_email, client_route, client_days, type, notes, logged_by, logged_at, status)
SELECT
  n.client_id,
  c.client_name, c.address, c.phone, c.email, c.route, c.service_day,
  CASE
    WHEN UPPER(n.action) LIKE '%DRIVER%'  THEN 'DRIVER'
    WHEN UPPER(n.action) LIKE '%BILLING%' THEN 'BILLING'
    WHEN UPPER(n.action) LIKE '%MISSED%'  THEN 'MISSED_STOP'
    ELSE 'OTHER'
  END,
  COALESCE(NULLIF(n.note,''), 'Migrated from legacy Complaint note (no description)'),
  COALESCE(NULLIF(n.user_id,''), 'Unknown'),
  n.created_at,
  'new'
FROM notes n
LEFT JOIN clients c ON c.client_id = n.client_id
WHERE n.action LIKE 'Complaint%';

-- Then remove the migrated complaint notes from the notes table so they don't
-- appear in both places (the operational reports filter them anyway, but
-- removing keeps the notes table clean).
DELETE FROM notes WHERE action LIKE 'Complaint%';
```

### Storage buckets
- `helm-files` (Private) — with RLS policies allowing anon key to read/write/delete

---

## Known Constraints

- **Authentication** is shared password + per-user login. Fine for small internal team (~9 users).
- **No real-time sync** — users must refresh to see others' changes.
- **Single file** — all HTML, CSS, and JS in `index.html` (~13,000 lines as of May 2026). Intentional simplicity.
- **Autopay** is informational only — billing is external.
- **Driver hours** only captured for Island Rubbish on the Daily Scale Report path (entered HH:MM in the post-upload prompt). Reis hours can be entered manually via the Driver Hours Entry form on the Scale KPIs tab; East End hours are not yet tracked.
- **Walk-in revenue** pre-imports (before walk-in revenue tracking was added) show $0. Recent re-imports fixed this.
- **Xfer Station capacity** is per-browser localStorage; seed balance is shared via app state (experimental — may move to DB).

---

## File Structure

```
helm-app/
├── index.html                                    ← The entire application
├── master_list_extract.py                        ← Master List import: PDF extractor + dry-run diff (paused mid-flight, see Recent Major Changes May 5)
├── helm_delta_audit.py                           ← HELM ↔ Delta cross-reference audit; outputs HELM_Delta_Audit.xlsx
├── import_rates.py                               ← Fills clients.rate1-5 from the Delta PDF (1,292 accts done)
├── import_routes.py                              ← Upserts route_assignments from the Delta PDF (1,999 rows done)
├── .gitignore                                    ← Excludes PII-bearing extract artifacts (master_extract*.{json,csv}, dryrun_*.csv, audit_*.csv, import_*_*.csv, HELM_Delta_Audit.xlsx, peek_*.py)
├── IRR_DailyScaleReport.gs                       ← Legacy Google Apps Script (not used)
├── irr-daily-report.html                         ← Standalone daily report tool (legacy)
├── sample_clients.csv                            ← Client CSV import template
├── rolloffs_clean.csv                            ← Sample rolloff data
├── 1776188206521-JAN12025TOAPR132026.xls         ← Historical scale export (Jan 1 2025 → Apr 13 2026)
├── README.md                                     ← This file
```

---

## Recent Major Changes

Older entries are intentionally terse — full detail lives in git history. The most recent week is given fuller context.

### May 18-21, 2026

- **May 21** — Complaint pipeline v2 (case management). Complaints are now a first-class table (`complaints` + `complaint_actions`) instead of a note category. Red **Log Complaint** button on every client card opens a centered modal that auto-fills a client snapshot and forces type-before-notes (Driver / Billing / Missed Stop / Other). David gets a topbar inbox icon with an iMessage-style red badge counting `new` complaints; inbox modal is email-style master/detail with filter chips (New / Open Cases / Resolved / Ignored / All). For each complaint David either opens a case (action log timeline with standardized step types Called Client / Spoke to Driver / Spoke to Rep / Note → Mark Resolved with required notes) or ignores it (reason required). Each case prints as a complete audit-trail document. The old `Complaint` action in `ACTION_TYPES` is gone and the subtype selector was removed from the notes form. Legacy `Complaint - X` notes are auto-migrated to the new table via SQL — they show up in the inbox as `new` so nothing is lost. Edit Client moved to top-right of the client info column; Log Complaint took its old spot at the bottom.
- **May 21** — Post-generation filter bar on Everything Report, Notes Added Today, and Complaint Report. Single-select dropdowns for Action / By / Route / Company + a free-text search (Complaint Report uses a smaller Type / By / Search set). Filters apply instantly client-side off stashed data — no re-query. Print buttons honor the active filter set and embed the filter description in the print header so the printout is self-explaining. Notes Added Today gained a `By` column on both screen and print to match Everything Report. The "N of M match" counter on the right end of each filter bar makes it obvious whether a filter is active.
- **May 21** — Complaint pipeline v1 (now superseded by v2 above):
  - `Complaint` action type added to client Notes with a 3-option subtype selector (DRIVER / BILLING / OTHER) that appears when Complaint is chosen. Saved as `Complaint - DRIVER` etc in `notes.action` so subtype filtering needs no schema change.
  - Complaints are **hidden** from Daily Action Report, Notes Added Today, and Everything Report (screen + print) via `filterOutComplaints()` so they don't pollute the operational reports staff scan every day.
  - New **Complaint Report** card on the Reports tab — visible to David and Esme only. Week navigator (Mon–Sun), summary chips per type, print view in red theme. Closes the long-standing gap where complaints had no dedicated channel; now they have a private weekly review surface for the two people who actually act on them.
- **May 20** — `sharon` staff user added with restricted view (Client Lookup + Reports only — Add Client / Roll-offs / Dispatch nav group hidden via username gate in both auth paths).
- **May 19** — Bulk-loaded route notes from `STOPS WITH RT NOTES.xlsx` into `route_assignments` (7,519 upserts, 5,881 with notes). Destructive note-blanks neutralized via two-batch upsert (preserve-existing branch omits `route_note` from payload so PostgREST leaves it untouched on conflict). Then `sync_client_route_fallback.py` copied each client's first-day route + note down to `clients.route` / `clients.route_note` (3,444 PATCHes) so the lookup-card pill matches. Lookup card now renders `📋 route_note` as italic teal line under the address (same look as reports).
- **May 18** — `find_missing_accts.py` parses all 6 day-route master-list PDFs and diffs vs HELM; `bulk_import_missing_accts.py` creates the surfaced sub-accounts (160 clients + 274 route_assignments inserted, names + addresses enriched from the broader delta export where available). All 176 sub-accts now in HELM. Per-day Routes section added to Add Client (mirrors Edit Client editor).

### May 6-14, 2026

- **May 14** — Per-day Routes editor + Rate Schedule panel rolled out to all users (were David-only). Intercompany Rolloff columns flipped to mirror the daily email exactly (Today / MTD / MTD YoY / YTD / YTD YoY) — pulls from `irrLoadYTD()` so values reconcile to the cent.
- **May 9** — Dispatch feature shipped in 3 phases: schema + `rolloffs.phone`/`tare_id` + Roll-offs page columns (Phase 1); Dispatch Input form + History + bidirectional sync to "the book" (Phase 2); Rolloff Queue card grid + click-to-modal + Empty-and-Home auto soft-delete + admin default-landing (Phase 3). New collapsible Dispatch nav group with three children. Also: Intercompany Rolloff rows now mirror the daily email's section layout (Internal/External/Total Volume, Outbound, Revenue with $/ton sub-rows).
- **May 8** — Daily Action Report print header shows time-of-print.
- **May 7** — Editable Account # in Edit Client with safe PK migration (insert new → UPDATE FK tables → DELETE old, with rollback on failure); per-day route pair auto-fill (Mon↔Thu / Tue↔Fri / Wed↔Sat fill-if-empty); Delete Client (Danger Zone) with typed-acct# confirmation; phone normalization to XXX-XXX-XXXX on save; per-day route resolution in reports (`resolveRoute()` / `resolveRouteNote()`); 3X WK note action; Add Client numeric-only validation + REIS next-ID floor at 209742.
- **May 6** — Residential Routing tab launched under new Routing nav group; Master List import (1,292 clients × rate1-5 + 1,999 route_assignments populated from Delta export retry 2 PDF).

### May 1-5, 2026

- **May 5** — Per-pickup rate schedule on clients (R1-R5 NUMERIC columns + Lookup card rate panel + Edit Client rate inputs); Daily Scale Reports auto-save dedupe; tab persistence on refresh via `localStorage.helm_active_tab`.
- **May 4** — Scale KPIs tab built out (Week/Month/Custom modes, six sections, shared `kpiAggregate` helper consumed by daily email + ICR + Scale Monthly Review + KPIs grid); analysis-section restructure (IRR Scale parent retired, sub-views promoted; Quarterly / Yearly / Projections buttons removed); ICR MTD column clipping fix.
- **May 1** — Scale Monthly Review (renamed from Monthly Rolloff Report) with new Walk-Ins + All Inbound sections.

### April 2026

- **April 28-30** — Rolloff Visual stock-chart studio (dark navy theme, time-frame strip, studies, fullscreen pop-out); Business Line Analysis tab (manual KPI entry for Resi/Comm/Rolloff/Xfer, six BLA tables); Route Note field on Edit Client; 40 Yard Delivery $200 + Move Rolloff $100 fee updates.
- **April 24-27** — Side-nav grouping (Client Management + Analysis collapsible groups); Reports tab restructure (Daily Action by Route, Notes Added Today, Everything Report, Export Clients to Excel); Workflow tab (David-only Linear/Notion-style project management with recurring tasks); Lookup card email display.
- **April 23-26** — Daily email rebuild (unified sections, signed deltas, YOY blocks); HELM-vs-scale-file revenue reconciliation documented; Yearly Report + 2025 Historical Rolloff/C&D table added to Intercompany Rolloff; Roll-offs autosuggest.
- **April 17-19** — Hook fee + disposal fee split; rate cutover for ≥4/17 (rolloff service fees hardcoded, walk-in tiers $480/$525, IC rates $250+$480+0%); Route dropdown (1-14) on Edit Client; Xfer Station tab; Roll-offs Monthly Tip / Export Untipped / Export Print Sheet; Consolidated Rolloff sub-tab.
- **April 16** — Lookup empty-state redesign (Service Rate Sheet + My Notes cards); per-user themes (esme pink, jackie Jamaica); Contacts panel inline-edit.

### Pre-April 2026

- **Oct 2025 → present** — Full IRR Scale system (daily parsing, email drafts, historical viewing, intercompany report, quarterly charts, projections, dashboard).
- Files tab with Supabase Storage; Chris admin user added; Command tab deprecated + removed.
