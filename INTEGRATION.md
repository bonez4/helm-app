# HELM / BEACON — Integration Guide

*For the developer connecting HELM + BEACON to Reis Trucking's other office software.*
*Companion to `README.md` (which has the full per-column schema). This doc covers what you need to integrate safely.*

---

## 1. The big picture

HELM and BEACON are **two single-file front-ends** (`index.html` + `beacon/index.html`) hosted statically on GitHub Pages. They have **no application server** — all logic is client-side JS, and all data lives in **one shared Supabase project** (PostgreSQL + Storage + Auth).

**That shared Postgres database is the integration hub.** You don't integrate with the HTML apps — you connect to the same Supabase/Postgres that they read and write. Anything you add (sync jobs, the office software, QuickBooks, BI) becomes another client of the same source of truth.

```
  HELM (browser) ─┐
  BEACON (browser)─┼──► Supabase (Postgres + Storage + Auth) ◄──► your integration / office software / QuickBooks
  office software ─┘
```

- **Project URL:** `https://iiqlhqtyyqctgupalrlc.supabase.co`
- **Publishable (anon) key:** in `README.md` — safe to expose; it does nothing without a login (see §3).
- **service_role key:** in the Supabase dashboard → Project Settings → API. **Server-side only. Never commit it or put it in a browser.** (Note: a prior key was exposed in a screenshot and should be rotated — confirm it has been.)

---

## 2. Ways to connect (all standard Supabase surfaces)

| Mechanism | Use it for |
|---|---|
| **PostgREST REST API** (`/rest/v1/...`) | Simple reads/writes over HTTPS with a key |
| **Direct Postgres connection** (host/port/password in dashboard) | ETL, bulk sync, BI tools, anything SQL |
| **Realtime** (websocket subscriptions) | React to inserts/updates live (e.g. new dispatch job) |
| **Database Webhooks** (Supabase → HTTP) | Fire an outbound call on row insert/update (e.g. "job completed → create QB invoice") |
| **Edge Functions** (Deno serverless) | Custom server logic + hold secrets (e.g. a QuickBooks proxy, an AI call) |
| **Storage API** | Files/photos in the private `helm-files` bucket (signed URLs) |

---

## 3. Auth & security — read this before writing anything

**Every table and the storage bucket are RLS-locked to `authenticated` only** (hardened 2026-05-29). The publishable/anon key with no login returns `[]` from every table. This is deliberate — do not undo it.

For server-to-server integration, the two correct options:
1. **service_role key, used only on your server.** Bypasses RLS. Simplest for trusted backend sync. Keep it in server env/secrets, never client-side.
2. **A dedicated Postgres role + scoped RLS policies** for the integration (least-privilege — e.g. read-only on most tables, write only where needed). More work, safer.

**Do NOT** "open the tables back up to anon" to make integration easier — that silently reverses the whole security model. If a browser-side piece needs data, route it through an Edge Function that checks the user's Supabase Auth JWT.

- **App login:** Supabase Auth, synthetic emails `username@helm.internal`. Profiles (display_name/role) are in the `users` table; passwords live in Supabase Auth.

---

## 4. The data model (integration-relevant summary)

Full column-by-column detail is in `README.md → Database Schema`. Below is the map + the join keys.

### The spine
- **`clients`** — the master customer record for both apps. **PK = `client_id`** (the account #, a string like `200221`). This is the **universal join key** everywhere.
  - `status`: `Active` / `Paused` / `Inactive`. `account_type`: `residential` / `commercial` (**NULL on inactive/unclassified rows**). `account_role`: `standalone` / `master` / `sub` (+ `master_account_id` for subs).
  - `rate1..rate5` per-pickup rates; `route`, `service_day`, contact fields.

### HELM operational
- **`notes`** (client notes/actions), **`skips`** (weekly skips), **`route_assignments`** (per-client-per-day route + note), **`rolloffs`** (construction dumpster tracking, soft-delete via `deleted`), **`dispatch_tickets`** (rolloff request queue: `ROLL####`), **`complaints`** + **`complaint_actions`** (case-managed complaint pipeline), **`bulky_pickups`** (residential bulky queue; `photos` JSONB), **`contacts`**, **`user_notes`**, **`users`**.

### Scale / financial (intercompany)
- **`irr_reports`** (daily scale report per date — tonnage/tickets/revenue by company), **`irr_rates`** (hook fees + per-ton rates), **`crc_weekly_manual`** (JSONB weekly hours).

### Business Line Analysis
- **`bla_staff`**, **`bla_resi_entries`**, **`bla_comm_entries`**, **`bla_rolloff_manual`**, **`bla_xfer_manual`**.

### Workflow (project mgmt, David only)
- **`helm_action_projects` / `_tasklists` / `_milestones` / `_tasks` / `_dependencies` / `_activity`**.

### BEACON — commercial database (all reference `clients.client_id`, soft, no FK)
- **`commercial_accounts`** — per-commercial-client dispatch metadata: per-service weekday schedules (`trash_days`/`cardboard_days`/`recycle_days`, codes `MTWRFSN`), `dispatch_notes`, and a **needs-attention flag** (`flagged`/`flag_reason`/...).
- **`commercial_history`** — photo/video + note timeline (`photos` JSONB → `helm-files/commercial/<acct>/...`).
- **`commercial_events`** — new/lost business (`event_type` `new`/`lost`, `event_date`, `reason`).
- **`commercial_contacts`** — contact people (name/title/phone/email/is_primary).
- **`commercial_outreach`** — contact log (date/method/contacted_by/notes).

### BEACON — residential dispatch
- **`dispatch_jobs`** — bulky-pickup pipeline. `stage` = `verify`→`outreach`→`dispatch`→`completion` (+ `denied`/`archived`). `client_id` (nullable — free-address jobs allowed), `photos` JSONB, **`price_items` JSONB `[{title,price}]`** (the billable charges), `driver`, `notes`, stage timestamps.
- **`dispatch_price_templates`** — reusable `{title, price}` line-item catalog.

### Files
- **`helm_folders` / `helm_files`** (metadata) + the private **`helm-files`** Storage bucket (actual blobs; access via signed URLs).

---

## 5. Universal conventions (respect these or the apps misbehave)

- **`client_id` (account #) is the join key** across every table and both apps.
- **Company is derived from the first digit of the account #:** `2…` = REIS, `3…` = SANTOS/East End, `1…` = rolloff. (Not stored as a column.)
- **Phones are normalized to `XXX-XXX-XXXX`** on save. Match that format when writing.
- **Photos/media** are JSONB arrays of `{path, type:'image'|'video', uploaded_at, uploaded_by}` pointing into the private `helm-files` bucket. The file bytes are *not* in the DB.
- **Money** lives as `price_items` JSONB (dispatch) and the `rate1..5` columns (clients) — there is **no invoice/AR table yet** (a likely integration point — see wishlist).
- **Soft deletes / status enums** exist (`rolloffs.deleted`, `bulky_pickups.status`, `dispatch_jobs.stage`) — filter on them; don't assume hard deletes.

---

## 6. Gotchas that will bite an integrator

1. **Active-account reconciliation owns `clients.status`.** A script (`import_active_accounts.py`) periodically reconciles HELM against the legacy **NetWork** "ALL ACCOUNTS" PDF export: matched accts → `Active` (+ type/role/rates), PDF-only → created, **HELM-only → flipped to `Inactive`**. If your integration creates clients that aren't in NetWork's export, the next reconciliation may mark them Inactive. Coordinate on who owns the active list.
2. **Account-# renumbering.** HELM can rename a `client_id` (PK migration); it re-points `notes`/`skips`/`route_assignments` but **not** the BEACON `commercial_*` / `dispatch_*` tables (those soft-reference `client_id`). If you renumber accounts, handle those too.
3. **`account_type` is NULL on inactive rows** — don't assume every commercial account has `account_type='commercial'` (only active ones do).
4. **Two "dispatch" concepts:** HELM's `dispatch_tickets` (rolloff requests) vs BEACON's `dispatch_jobs` (residential bulky pipeline). Different tables, different domains.
5. **No application server** = no place that's already running business logic. Anything event-driven (sync, invoicing) needs a Webhook + Edge Function or your own service.

---

## 7. Likely integration patterns

- **Customers:** map `clients.client_id` ↔ office-software / QuickBooks customer IDs (a mapping table, or store the external ID on a new column/side table — don't overload existing columns).
- **Invoicing:** `dispatch_jobs.price_items` at `stage='completion'` (and rolloff/route billing) → push as invoices to QuickBooks via an Edge Function or your server; write back paid/AR status into a new field/table the apps can display.
- **Scale data:** auto-load the daily scale feed into `irr_reports` instead of the manual `.xls` upload.
- **Events:** Database Webhooks on insert (new complaint, new dispatch job, completed job) → notify / create records downstream.

---

## 8. Security checklist for the integration

- [ ] service_role key only on the server; rotated if ever exposed.
- [ ] Prefer a scoped DB role + RLS policies over blanket service_role where feasible.
- [ ] Never re-open tables/bucket to `anon`.
- [ ] Browser-side AI/integration calls go through an Edge Function that validates the Supabase Auth JWT.
- [ ] New columns/tables you add: enable RLS + an `authenticated` (or scoped) policy, matching the existing model.
- [ ] Write phones/dates/JSONB in the existing shapes; respect `status`/`stage` enums.

---

*Questions on any table or flow → see `README.md` for full columns + the "Recent Major Changes" log, or ask David.*
