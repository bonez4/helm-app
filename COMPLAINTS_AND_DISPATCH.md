# Complaints (HELM) & Bulky Dispatch (BEACON) — Current Build

_Reference for the complaint case-management system in **HELM** and the residential bulky-pickup dispatch pipeline in **BEACON**, as built. Last updated 2026-06-17 (after the complaint Console + reporting overhaul)._

Both apps are single HTML files in the same repo sharing one Supabase project + auth session:
- **HELM** — `index.html`
- **BEACON** — `beacon/index.html`

---

# Part 1 — HELM Complaint System

A first-class case-management pipeline: any rep can log a complaint against a client; **David** triages and manages cases in a full-page **Console**; **supervisors** (Dane, Brian) resolve the ones routed to them. Everything David and the supervisors do is one shared, timestamped audit trail, and it all feeds the reporting.

## 1.1 Data model (the stable contract)

Three tables + one user flag. **All presentation reads/writes go through these — the UI can be rebuilt freely without touching the data.**

### `complaints` — one row per complaint (the case record)
| Column | Notes |
|---|---|
| `id` | BIGSERIAL PK |
| `client_id` | Account the complaint is about |
| `client_name` / `client_address` / `client_phone` / `client_email` / `client_route` / `client_days` | **Snapshot** frozen at log time — the case file never drifts if the client record changes later |
| `type` | Complaint type token. Built-ins `DRIVER` / `BILLING` / `MISSED_STOP` / `OTHER`, plus any admin-added types (see taxonomies) |
| `driver_name` | Required when the type has `needs_driver` (built-in `DRIVER`); also back-filled when a supervisor logs "Spoke to Driver" on any routed complaint (incl. Missed Stop). Plain text. **Displayed wherever it's set** — cards, report rows, case detail, prints — not only on Driver-type. |
| `priority` | `urgent` / `high` / `normal` / `low` (default `normal`) |
| `notes` | The rep's description of the complaint |
| `logged_by` / `logged_at` | Who logged it + when |
| `status` | `new` / `case_open` / `resolved` / `ignored` |
| `case_opened_at` / `case_opened_by` | Set when a case is opened |
| `resolved_at` / `resolved_by` / `resolution_notes` | Set on resolve |
| `ignored_at` / `ignored_by` / `ignored_reason` | Set on ignore (reason required) |
| `routed_to_supervisor` | TRUE once it's in the Supervisor Queue |
| `assigned_to` / `assigned_at` / `assigned_by` | The supervisor it's assigned to (NULL = unclaimed pool) |

### `complaint_actions` — the shared per-case audit trail
| Column | Notes |
|---|---|
| `id` | BIGSERIAL PK |
| `complaint_id` | FK → complaints, ON DELETE CASCADE |
| `action_type` | System: `opened` / `resolved` / `reopened` / `routed` / `escalated`. David's case notes (`called_client` / `spoke_to_driver` / `spoke_to_rep` / `supervisor_informed` / `note`, admin-managed). Supervisor buttons (`spoke_to_driver` / `spoke_to_client` / `contacted_office` / `on_site_visit`) |
| `notes` | Free-text detail |
| `performed_by` / `performed_at` | Who + when |

> Every supervisor tap, case note, resolve, escalate, and route writes a row here. **This is why the reporting needs no extra tracking — the outcome data already exists.**

### `complaint_taxonomies` — admin-managed picklists
`kind` (`type` | `action`), `value`, `label`, `needs_driver`, `sort_order`, `active`, `is_builtin`. Managed via **⚙ Manage types** in the Console header (David). Built-ins are the hard fallback.

### `users.is_supervisor`
BOOLEAN — grants the Supervisor Queue (Dane, Brian).

## 1.2 Roles & access
- **All users** — log a complaint from any client card.
- **David** (`username==='david'`) — the Complaint Console (triage + case management) + ⚙ Manage types. Topbar complaint icon + new-count badge.
- **Supervisors (Dane, Brian)** — the Supervisor Queue (they land on it at login). David/admin can open it for oversight.
- **David + Esme** — the separate Reports-tab cards (weekly Complaint Report + Monthly Complaint Summary) — left intact, distinct from the Console.

## 1.3 Logging a complaint (all users)
Red **Log Complaint** button on every client card → centered modal (`#complaintModal`):
- Auto-fills the client snapshot (frozen at log time).
- **Type picker** (required); a **Driver involved** field appears for driver-type complaints.
- Notes textarea is hidden until a type is chosen.
- On submit → inserts a `complaints` row, `status='new'`. **Driver + Missed-Stop auto-route to the supervisor pool on log** (`SUP_AUTOROUTE_TYPES`).

Complaints also appear **read-only in the client-card notes timeline** (red-bordered rows with a status pill), so reps see "what's happened with this client" in one place.

## 1.4 David's Complaint Console — full page

The topbar complaint icon (`openComplaintInbox`) opens a **full-viewport page** (not a modal). Three internal views, switched by `_consoleMode` + `_inboxSelectedId`:

### Triage view (default)
- **4 clickable stat boxes** drive one card grid:
  | Box | Shows |
  |---|---|
  | **New** | `status='new'` AND **not** routed to a supervisor (needs David) |
  | **Open** | In progress — `case_open` OR routed-to-supervisor, not resolved/ignored |
  | **Resolved this week** | Resolved with `resolved_at` in the current Mon–Sun week |
  | **Avg. resolve this week** | Mean resolve time over that set (click → those cards, slowest first) |
  - Low-key **All** / **Ignored** chips next to the search box (nothing is ever lost).
- **Complaint cards** (bulky-pickup style) show client name + address, time logged, type chip, and a priority chip when not "normal."
- **Age shading** on New/Open cards by time since logged: 🟢 `<8h` · 🟡 `8–24h` · 🔴 `24h+` (soft background tint + colored left edge + an elapsed pill). `complaintBucketOf` / `ccAgeTint`.
- **Supervisor-routed cards are visually distinct** — a blue "👤 _name_ / Supervisor pool" ribbon + blue ring (`.cc-card.routed`), so Open shows at a glance what's in a supervisor's hands.
- Full-text search across client / address / driver / note / acct / assignee.

### Case detail (click any card)
The existing case-management UI (`renderInboxDetail`), unchanged by the rebuild:
- Client snapshot + original complaint.
- **Re-categorize** — the complaint **type** in the case header is an editable dropdown (`setComplaintType`, populated from the live taxonomy). David can fix a miscategorized complaint at **any** status; the change is logged to the audit trail as a `recategorized` entry ("Re-categorized: X → Y"). Routing/driver are left as-is.
- **new** → **▸ Open Case** / **Ignore** (reason required).
- **case_open** → action-log timeline + **＋ Add Entry** (typed case-note) + **✓ Mark Resolved** (resolution notes required).
- **Hand to a supervisor** → assign to Dane/Brian or drop in the pool.
- **📧 Email complaint** (Gmail compose prefilled) · **Print** (single case file).
- **resolved / ignored** → read-only banner with who/when/notes, plus **↩ Reopen & add entries** (`reopenComplaint`) — flips it back to Open (writes a `reopened` audit entry; the prior resolution/ignore stays in the action log), so David can add entries and re-resolve. A reopened supervisor-handled case returns to that supervisor's queue.

Acting on a card moves it between boxes (New → Open → Resolved). The topbar badge counts **new & not-routed**, matching the New box.

## 1.5 Supervisor Queue (Dane, Brian; David/admin oversee)
Mobile-first modal (`openSupervisorQueue`). Same `complaints` / `complaint_actions` data as David's Console.
- **My cases / Available (pool) / Solved** tabs; **Claim** pulls a pool case into "mine."
- **Solve screen (stage, then commit):** toggle buttons **Spoke to Driver** (prompts for name) · **Spoke to Client** · **Contacted Office** · **On-site Visit** — tap to stage (highlight), nothing is written until **✓ Resolve** (`supCommitPending` writes the staged actions + note at once). **↩ Send back to David** and **Reopen** also commit.
- **Realtime** (Supabase broadcast, channel `helm-complaints`): supervisors pinged when a complaint is routed to them; David/admin pinged on solve/escalate.

## 1.6 Reporting — Daily / Weekly / Custom

Reached from the Console's **📊 Reports** button (`ccShowReports`). Compact, dense, descriptive — **one row per complaint** (not a page per case). Derived entirely from the already-loaded complaints; no extra query.
- **Modes:** Daily (day ‹ › + Today), Weekly (week ‹ › + This week), Custom (from–to + Last 7d / 30d / This month).
- **Summary KPIs:** Submitted · Resolved · Still open (now) · Avg. resolve — plus a **Submitted-by-type** breakdown (Driver / Billing / Missed Stop / Other + any custom types, with counts).
- **Two sections:**
  | Section | Rows |
  |---|---|
  | **Submitted in this period** | one row per complaint (time · type · client+address · route · complaint · by · status); **the resolution — or ignore reason — shows inline directly beneath** each complaint that has one (`crComplaintsSection`) |
  | **Still open — current backlog** | age (color) · type · client · route · complaint · by · status |
  - Routed rows show the supervisor inline; click a row to drill into the case detail.
- **🖨 Print** (`printConsoleReport`) → the same dense layout (inline resolutions + the by-type header), `page-break-inside:avoid` per row + repeating headers, so a busy week is a few pages, not dozens.

### Driver Complaints — interactive view
A **🚛 Drivers** button in the Console opens a per-driver rollup (`ccShowDrivers` / `renderDriverReport`) — every complaint with a `driver_name`, grouped by driver, over an optional date range (From/To + All time / Last 30d / Last 90d):
- **Leaderboard** of driver cards (`drvCardHTML`) sorted by complaint count; each shows the type mix, open/resolved split, and last-complaint date.
- **Drill-in:** tap a driver → their full complaint list (date · type · client · complaint · status · resolution inline), each row click-through to the case detail.
- Summary KPIs: driver complaints · drivers named · still open · most complaints.
- Driver names come from Driver-type complaints (logged) **and** the supervisor "Spoke to Driver" back-fill, so Missed Stops with a known driver show up too. No new capture step + no new query (reads `_inboxComplaints`).

### Complaint Insights — analytics dashboard
A **📈 Insights** button opens a dynamic dashboard (`ccShowInsights` / `renderComplaintInsights`) over an optional date range (All time / 30d / 90d / This year / Custom):
- **KPI strip:** complaints · open now · resolved · avg resolve · repeat clients · % of complaints from repeat clients.
- **Live Chart.js charts:** complaints over time (stacked unresolved / resolved / ignored — weekly buckets when the span ≤120 days, else monthly), a by-type doughnut, and a by-route bar — **click a route bar to drill into that route's complaints**.
- **Repeat-customer table** (`ciData().repeat`): every client with **2+ complaints** is flagged (amber for 2, red for 3+), sorted by count — click a row to drill into that client's complaints. Every drilled complaint clicks through to the case detail.
- Reads `_inboxComplaints` only (no new query); charts are destroyed + rebuilt on each filter change (`_ciCharts`).

> The older per-case print functions (`printComplaintDay` / `Week` / `Range` / `List`) are superseded and unwired (kept only as dead code). The single-case **Print** in the detail view (`printComplaintCase`) remains.

## 1.7 Cross-app integration ("the seams" — read-only consumers of the data)
- **Operational reports exclude complaints** via `filterOutComplaints()` — Daily Action Report, Notes Added Today, Everything Report.
- **Client-card notes timeline** interleaves complaint rows (`renderComplaintHistoryRow`, styled `at-complaint`).
- **Log Complaint** button on the client card.
- **Topbar badge** poll (`refreshComplaintBadge`, every 60s + on focus).
- **Realtime channel** `helm-complaints`.

## 1.8 Key functions (quick index)
`openComplaintInbox` · `renderInbox` · `complaintBucketOf` · `ccAgeTint` · `ccFriendlyAge` · `renderConsoleCards` · `ccCardHTML` · `setInboxFilter` · `selectInboxRow` · `renderInboxDetail` · `openCase` · `submitCaseAction` · `confirmResolveCase` · `confirmIgnoreComplaint` · `davidSendToSupervisor` · **Reporting:** `ccShowReports` · `renderComplaintReport` · `crData` · `crPeriod` · `crSection` · `printConsoleReport` · **Supervisor:** `openSupervisorQueue` · `renderSupervisorList` · `supClaim` · `supToggleAction` · `supResolve` · `supEscalate` · **Taxonomies:** `loadComplaintTaxonomies` · `ensureTaxonomies`.

---

# Part 2 — BEACON Bulky Dispatch

A **residential bulky-pickup pipeline** as a 4-stage Kanban board (BEACON `#dispatch` tab). A photo + address comes in → it's priced, the client is called, a driver is dispatched, the charge is confirmed. (Distinct from HELM's "Bulky Pickups" tab, which is David's photo-log of items left on routes.)

## 2.1 Data model — `dispatch_jobs`
| Column | Notes |
|---|---|
| `id` | BIGSERIAL PK |
| `stage` | `verify` → `outreach` → `dispatch` → `completion`, plus terminal `denied` / `unreachable` / `archived` (History) |
| `client_id` / `address` / `client_name` / `phone` | Snapshot; autofilled from a matched client or free-typed |
| `photos` | JSONB `[{path,type,uploaded_at,uploaded_by}]` → `helm-files/dispatch/<job>/…` |
| `quoted_price` | **The job charge** — set in Verify, read-only in Outreach, confirmed at Completion |
| `price_items` | _Legacy_ line items — superseded by `quoted_price` |
| `outreach_log` | JSONB `[{at,outcome,number,by,notes}]` — every call attempt (`accepted`/`denied`/`no_answer`) |
| `callback_due` | Set 30 min out on a 1st no-answer (drives the ⏰ badge + desktop reminder) |
| `phone_ok` / `alt_phone` | Outreach phone check |
| `driver` | Assigned at Dispatch |
| `completion_notes` / `denial_note` | Completion notes / denial reason (or "Unreachable — N no-answers") |
| `dispatched_at` / `completed_at` / `denied_at` / `archived_at` | Stage stamps (`dispatched_at` = card goes live/green) |
| `notes` | Free-form, on every stage, printed on the ticket |
| `created_at/by`, `updated_at/by` | Audit |

All BEACON tables are RLS-locked to `authenticated`.

## 2.2 The board (`renderDispatchBoard`)
Four columns; a card is pushed to the next stage by a per-stage button (`moveStage` / `persistJob`).

| Stage | What happens |
|---|---|
| **Verify** | **＋ New job** → add photo(s) + address (an address typeahead against active clients autofills acct/name/phone, or save a free address). **Set the quoted price** here (priced from the photo). |
| **Outreach** | Quote shows **read-only**; a **phone check** (is the file # right + an alternate number) + a call-attempt log. Three outcomes — **Accepted → Dispatch**, **Denied** (preset reason → History), **No answer** (1st → 30-min callback + desktop notification + ⏰ badge; 2nd → **Unreachable**, terminal). |
| **Dispatch** | Full contact block (name · acct # · click-to-call phone) + quote; assign a **driver**; **Dispatch — go live** (`dispatchGoLive`) turns the card green + LIVE, then **Mark complete →**. |
| **Completion** | Reached via a **Confirm charge** modal (the quote, editable) so billing is deliberate; per-ticket print + a board-level **🖨 Print completed (N)** bulk print (page-broken tickets with embedded photos). |

- **Live client data:** for jobs linked to an account, name/address/phone are pulled live from the HELM `clients` table on every load (`overlayLiveClients`) — HELM edits always show, even mid-pipeline. The stored snapshot is a fallback only for free-address jobs.
- **History** (`renderDispatchHistory`) — denied / unreachable / archived jobs by day, with photo thumbnails + lightbox.
- **Void** (`voidJob`, on dispatch + completion cards) — a **true removal**: hard-deletes the row + its photos so the ticket disappears from the board, History, **and** the conversion reporting, exactly as if it was never entered. Distinct from **Archive** (which keeps the job as a completed **sale**). Use it for mistakes / cancellations that shouldn't count.

## 2.3 Cross-user notifications (realtime)
Supabase broadcast, channel `beacon-dispatch-moves` (`initDispatchRealtime` / `broadcastDispatchMove` / `handleDispatchMove`, centralized in `persistJob`): the `admin` user is alerted when a card enters **Outreach** (he makes the calls); `david` on **every** stage move. The actor isn't self-alerted; recipients need BEACON open.

## 2.4 Conversion reporting (on the board)
Under the Kanban, `renderDispatchStats` shows cards created → conversions, filterable by **Day / Week / Month / Custom (From–To)**:
- **Outcome model** (`bulkyOutcome`): **sale** = `dispatch` / `completion` / `archived`; **denied** = `denied` / `unreachable`; else **in progress**.
- **Cohort** = cards **created** in the selected period (by `created_at`), computed from the already-loaded `_jobs` (no extra fetch). **Custom** mode (`_dispStatsFrom` / `_dispStatsTo`, defaulting to the last 30 days) takes a From/To date-range picker.
- Shows: cards created · converted-to-sale + **rate** · denied · in-progress · sales value vs total value · **Avg $ / trip** · **denied-by-reason** · **completed-by-driver** counts (with $ each) · a per-card table (incl. **Service Address**, Driver, Completed).
- A **"trip"** = a job actually completed (`completed_at` set). **Avg $ / trip** = average final charge over completed trips; **completed-by-driver** counts those completed jobs per `driver`.
- **🖨 Print** (`printBulkyReport`) and **Excel** (`exportBulkyReport`) emit the same figures (incl. avg $/trip + a completed-by-driver table).

## 2.5 Key functions (quick index)
`loadDispatch` · `overlayLiveClients` · `renderDispatchBoard` · `jobCardHtml` · `newJob` · `collectPatch` · `persistJob` · `advance` (push stage) · `dispatchGoLive` · `scheduleCallback` / `notifyCallback` · `archiveJob` · `deleteJob` (Verify) · `voidJob` (dispatch/completion — true removal) · `renderDispatchHistory` · `bulkPrintCompleted` · `renderDispatchStats` · `bulkyOutcome` · `printBulkyReport` · `exportBulkyReport` · `initDispatchRealtime` / `broadcastDispatchMove` / `handleDispatchMove`.

---

## Deploy
Edit the file → `git commit` → `git push` → GitHub Pages auto-deploys in ~1–2 min.
- HELM: <https://bonez4.github.io/helm-app/>
- BEACON: <https://bonez4.github.io/helm-app/beacon/>
