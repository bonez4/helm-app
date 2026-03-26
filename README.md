# HELM — Route Management System
### P&M Reis Trucking · Nantucket, MA

---

## What This Is

HELM is a single-file web application (`index.html`) that manages residential garbage pickup routes for P&M Reis Trucking. It replaces a manual paper-based process where clients would call in to skip a week, a note would be written down, and a staff member would manually update an outdated system called Delta.

The app is hosted on Netlify (free) and uses Supabase (free) as its database backend.

---

## Live App

**URL:** https://tourmaline-starlight-5ab128.netlify.app
**Password:** nantucket (shared office login)
**Per-user logins:** See users table in Supabase

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
| Database | Supabase (PostgreSQL) | Free tier |
| Hosting | Netlify (drag and drop deploy) | Free tier |
| Fonts | Google Fonts (DM Sans, DM Mono) | Free |

No build step. No npm. No framework. One file.

---

## Database Schema

### `clients` table
| Column | Type | Notes |
|---|---|---|
| client_id | TEXT (PK) | e.g. `0001`, `0094`, `2001-1` |
| service_day | TEXT | Monday–Friday |
| address | TEXT | Street address only, no city/state |
| phone | TEXT | Optional |
| email | TEXT | Optional |
| client_name | TEXT | Optional — full name |
| status | TEXT | `Active`, `Paused` |
| created_at | TIMESTAMP | Auto |

**Multi-day clients:** A client picked up twice a week gets two rows — `0101-1` (Monday) and `0101-2` (Thursday). Same address, same name, different `client_id` suffix and `service_day`.

### `skips` table
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | Auto |
| client_id | TEXT (FK) | References clients |
| skip_week | DATE | Always a Monday (ISO format) |
| inquiry_method | TEXT | `phone`, `email`, `person` |
| logged_by | TEXT | Staff display name |
| created_at | TIMESTAMP | Auto |

**Unique constraint:** `(client_id, skip_week)` — a client can only be skipped once per week.

### `users` table
| Column | Type | Notes |
|---|---|---|
| username | TEXT (PK) | Lowercase, used to log in |
| password | TEXT | Plaintext (simple internal tool) |
| display_name | TEXT | Shown in topbar and skip log |

**Current users:** david, maria, tom, admin

---

## App Features

### Client Lookup
- Search by client ID, name, address, or phone
- Results ranked by relevance (exact ID match first, then name, then address)
- Clicking a result opens the full client card

### Client Card
- Shows name, ID, address, phone
- Pickup day and account status (Active / Skipped this week / Paused)
- **Date range skip picker** — select first skip week and last skip week, HELM logs every week in between automatically
- Inquiry method buttons (Phone Call / Email / In Person) — saved against each skip for audit trail
- Skips on file shown as ranges (e.g. "Mar 16 — Apr 6 (4 weeks)")
- Remove skip button on each range
- **Service Control** — Pause Service / Resume Service button
- Duplicate detection on Add Client — warns if address or name already exists

### Add Client
- Name, address, phone, email fields
- Day toggle buttons (Mon–Fri) — select multiple for multi-day pickup clients
- Multi-day clients saved as `ID-1`, `ID-2`, etc.
- Auto-suggests next client ID

### Skip Log
- Grouped by client, shows ranges not individual weeks
- Shows contact method and who logged it
- Clickable client names — jumps to client card

### Route View
- Week selector (6 weeks shown)
- Day jump buttons (Mon–Fri) with skip count badges — click to scroll to that day
- Skipped clients shown crossed out and labeled SKIP
- Active clients shown with `›` arrow — clickable to jump to client card
- **Print button** per day — opens a clean printer-friendly page that auto-triggers print dialog

### Paused Tab
- Lists all clients with status = Paused
- Red left border, shows name/ID/day/address/phone
- Resume Service button — one click restores to routes
- View button — jumps to client card
- Tab badge shows count (e.g. "Paused 3") when clients are paused

### Import
- CSV upload with headers: `client_id, service_day, address, phone, client_name`
- Imports in 500-row batches (handles 6,000+ clients)
- Upsert on conflict — re-importing won't create duplicates

---

## Deployment

### To update the live site:
1. Edit `index.html`
2. Go to https://app.netlify.com
3. Click your site → Deploys tab
4. Drag and drop `index.html` onto the deploy area
5. Live in ~10 seconds, same URL

### To wipe and re-import all clients:
Run in Supabase SQL Editor:
```sql
TRUNCATE TABLE clients CASCADE;
```
Then use the Import tab in HELM.

### To add a new staff user:
Run in Supabase SQL Editor:
```sql
INSERT INTO users (username, password, display_name)
VALUES ('newname', 'password123', 'Display Name');
```

---

## Known Constraints

- **Authentication** is simple shared password + per-user login. Not enterprise-grade — fine for a small internal team.
- **No real-time sync** — if two staff members are on the app simultaneously, one won't see the other's changes until they refresh or switch tabs.
- **Supabase free tier** limits: 500MB database, 2GB bandwidth/month. At 6,000 clients this is nowhere near the limit.
- **Single file** means all CSS, JS, and HTML are in one place. Great for simplicity, but if the app grows significantly a proper build setup (React + Vite, etc.) would be worth considering.

---

## Ongoing Feature Ideas (discussed but not yet built)
- Text/email confirmation to client when skip is logged
- Printable route sheets with better formatting
- Edit existing client details (name, phone, address) from within the app
- Notes field per client
- Export skip log to CSV for billing reconciliation
- Dark mode

---

## File Structure

```
helm-app/
├── index.html       ← The entire application. This is the only file.
├── README.md        ← This file
```

That's it. No dependencies to install, no build step, no config files.
