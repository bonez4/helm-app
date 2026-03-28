# HELM — Route Management System
### Reis Trucking · Nantucket, MA

---

## What This Is

HELM is a single-file web application (`index.html`) that manages residential garbage pickup routes for Reis Trucking. It replaces a manual paper-based process where clients would call in to skip a week, a note would be written down, and a staff member would manually update an outdated system called Delta.

The app is hosted on GitHub Pages (free) and uses Supabase (paid, upgraded) as its database backend.

---

## Live App

**URL:** https://bonez4.github.io/helm-app/
**Office Password:** nantucket (shared gate password)
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
| Database | Supabase (PostgreSQL) | Paid (upgraded) |
| Hosting | GitHub Pages (auto-deploys from main branch) | Free |
| Fonts | Google Fonts (DM Sans, DM Mono) | Free |

No build step. No npm. No framework. One file.

---

## Database Schema

### `clients` table
| Column | Type | Notes |
|---|---|---|
| client_id | TEXT (PK) | e.g. `0001`, `0094`, `2001-1` |
| service_day | TEXT | Monday–Saturday |
| address | TEXT | Street address only, no city/state |
| phone | TEXT | Optional |
| email | TEXT | Optional |
| client_name | TEXT | Optional — full name |
| status | TEXT | `Active`, `Paused` |
| created_at | TIMESTAMP | Auto |

**Multi-day clients:** A client picked up twice a week gets two rows — `0101-1` (Monday) and `0101-2` (Thursday). Same address, same name, different `client_id` suffix and `service_day`. In the UI, these are grouped into a single search result showing all their days.

### `skips` table
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | Auto |
| client_id | TEXT (FK) | References clients |
| skip_week | DATE | The date of the skip |
| inquiry_method | TEXT | `phone`, `email`, `person` |
| logged_by | TEXT | Staff display name |
| created_at | TIMESTAMP | Auto |

### `notes` table
| Column | Type | Notes |
|---|---|---|
| id | SERIAL (PK) | Auto |
| client_id | TEXT | Base client ID (e.g. `2003` not `2003-1`) |
| user_id | TEXT | Display name of staff who added it |
| action | TEXT | One of: `One Time Pickup`, `Pile Pickup`, `Skip Day`, `Complaint`, `Note` |
| action_date | DATE | Date the action applies to (for actionable items) |
| note | TEXT | Free-text note content |
| created_at | TIMESTAMP | Auto |

**No foreign key constraint** on `notes.client_id` — this was intentionally removed so notes can be stored against base IDs for multi-day clients.

### `rolloffs` table
| Column | Type | Notes |
|---|---|---|
| id | SERIAL (PK) | Auto |
| date | DATE | Date placed/tracked |
| type | TEXT | `AJ` or `REIS` |
| customer | TEXT | Customer name |
| address_number | TEXT | Street number |
| street | TEXT | Street name |
| deleted | BOOLEAN | Soft delete flag (default false) |
| deleted_at | TIMESTAMP | When it was deleted |
| deleted_by | TEXT | Who deleted it |
| updated_at | TIMESTAMP | Auto |

### `users` table
| Column | Type | Notes |
|---|---|---|
| username | TEXT (PK) | Lowercase, used to log in |
| password | TEXT | Plaintext (simple internal tool) |
| display_name | TEXT | Shown in topbar and notes |

**Current users:** admin, david, jackie, esme, hannah, kobie

---

## App Features

### Client Lookup
- Search by client ID, name, address, or phone number
- Multi-day clients grouped into single results (shows all pickup days)
- Results ranked by relevance (exact ID match first, then name, then address)
- Clicking a result opens the client panel on the right side
- Client panel persists while navigating other tabs

### Client Panel
- Shows name, ID, address, phone, all pickup days
- Account status (Active / Paused)
- **Notes system** — add notes with action types:
  - One Time Pickup (requires date)
  - Pile Pickup (requires date)
  - Skip Day (requires date)
  - Complaint
  - Note (general)
- Notes log shows date/time, user, action type, action date, and note text
- Notes saved against base client ID so they're shared across multi-day entries

### Add Client
- Name, address, phone, email fields
- Day toggle buttons (Mon–Sat) — select multiple for multi-day pickup clients
- Multi-day clients saved as `ID-1`, `ID-2`, etc.
- Auto-suggests next client ID
- Duplicate detection — warns if address or name already exists

### Reports
- **Daily Action Report** — pick a date, see all actionable notes and scheduled skips for that day
- Pulls from both `notes` table and `skips` table
- Grouped by action type (One Time Pickup, Skip Day, Pile Pickup, etc.)
- Shows client ID, name, address, phone, and note text
- **Print Report** button — opens printer-friendly version

### Roll-offs
- Editable spreadsheet-style table for tracking construction dumpsters
- Columns: Date, Type (AJ/REIS dropdown), Customer, Number, Street
- Click any cell to edit inline, changes auto-save
- Sort by any column by clicking header
- Soft delete with 8-second undo bar
- "Show deleted" toggle to view/restore removed rows

### Import
- **Client CSV import** — headers: `client_id, service_day, address, phone, client_name`
- **Roll-offs CSV import** — headers: `date, type, customer, address_number, street`
- Both import in 500-row batches (handles large datasets)
- Client import uses upsert — re-importing won't create duplicates
- Roll-off import handles both MM/DD/YYYY and YYYY-MM-DD date formats

---

## Deployment

### To update the live site:
1. Edit `index.html`
2. Run `git add index.html && git commit -m "description" && git push`
3. GitHub Pages auto-deploys in ~1 minute
4. Live at same URL: https://bonez4.github.io/helm-app/

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
VALUES ('newname', 'reis2026', 'Display Name');
```

---

## Known Constraints

- **Authentication** is simple shared password + per-user login. Not enterprise-grade — fine for a small internal team of ~5 users.
- **No real-time sync** — if two staff members are on the app simultaneously, one won't see the other's changes until they refresh or switch tabs.
- **Single file** means all CSS, JS, and HTML are in one place. Great for simplicity, but if the app grows significantly a proper build setup would be worth considering.

---

## File Structure

```
helm-app/
├── index.html       ← The entire application. This is the only file.
├── README.md        ← This file
```

That's it. No dependencies to install, no build step, no config files.
