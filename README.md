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
| client_id | TEXT (PK) | e.g. `0001`, `0094`, `2001` |
| service_day | TEXT | Comma-separated: `Monday` or `Tuesday,Thursday` |
| address | TEXT | Street address only, no city/state |
| phone | TEXT | Optional |
| email | TEXT | Optional |
| client_name | TEXT | Optional — full name |
| autopay | BOOLEAN | Credit card on file for autopay (default false) |
| status | TEXT | `Active`, `Paused` |
| created_at | TIMESTAMP | Auto |

**Single row per client.** Multi-day clients store all pickup days comma-separated in `service_day` (e.g. `Tuesday,Thursday`). No suffixed IDs — each client has one unique `client_id`.

### `skips` table
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | Auto |
| client_id | TEXT (FK) | References clients |
| skip_week | DATE | The actual date of the skip |
| inquiry_method | TEXT | `phone`, `email`, `person` |
| logged_by | TEXT | Staff display name |
| created_at | TIMESTAMP | Auto |

### `notes` table
| Column | Type | Notes |
|---|---|---|
| id | SERIAL (PK) | Auto |
| client_id | TEXT | Client ID (e.g. `2003`) |
| user_id | TEXT | Display name of staff who added it |
| action | TEXT | One of: `One Time Pickup`, `Pile Pickup`, `Skip Day`, `Complaint`, `Note` |
| action_date | DATE | Date the action applies to (for actionable items) |
| note | TEXT | Free-text note content |
| created_at | TIMESTAMP | Auto |

**No foreign key constraint** on `notes.client_id` — intentionally removed for flexibility.

### `rolloffs` table
| Column | Type | Notes |
|---|---|---|
| id | SERIAL (PK) | Auto |
| date | DATE | Date placed/tracked |
| type | TEXT | `AJ`, `REIS`, `AJ/REIS`, `30YD`, `40YD`, `30/40YD`, `SANTOS BOX` |
| customer | TEXT | Customer name |
| address_number | TEXT | Street number |
| street | TEXT | Street name |
| notes | TEXT | Special instructions (e.g. C/C, OWN BOX, 2 BOXES) |
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
| role | TEXT | `admin` or `staff` — admins can access Import tab |

**Current users:** admin, david, jackie, esme, hannah, kobie

---

## App Features

### Client Lookup
- Search by client ID, name, address, or phone number
- Results ranked by relevance (exact ID match first, then name, then address)
- Clicking a result opens the client panel on the right side
- Client panel persists while navigating other tabs

### Client Panel
- Shows name, ID, address, phone, all pickup days (comma-separated displayed as pills)
- Account status (Active / Skipped / Paused)
- **Autopay indicator** — shows whether client has a credit card on file (Yes/No)
- **Edit Client** button — inline editing of name, address, phone, email, pickup days, and autopay status
- **Notes system** — add notes with action types:
  - One Time Pickup (requires date)
  - Pile Pickup (requires date)
  - Skip Day (requires date)
  - Complaint
  - Note (general)
- Notes log shows date/time, user, action type, action date, and note text
- **Delete notes** — each note has a delete button to remove incorrect entries

### Add Client
- Name, address, phone, email fields
- Day toggle buttons (Mon–Sat) — select multiple for multi-day pickup clients
- Single row created per client with comma-separated days
- Auto-suggests next client ID
- Duplicate detection — warns if address or name already exists

### Reports
- **Daily Action Report** — pick a date, see all actionable notes and scheduled skips for that day
- Pulls from both `notes` table and `skips` table
- Summary pills at top showing count per action type
- Grouped by action type with proper table layout (row numbers, column headers)
- Shows client ID, name, address, phone, and note text
- **Print Report** button — opens printer-friendly version with compact layout and summary line

### Roll-offs
- Editable spreadsheet-style table for tracking construction dumpsters
- Columns: Date, Type (AJ/REIS/30YD/40YD/etc. dropdown), Customer, Number, Street, Notes
- Click any cell to edit inline, changes auto-save
- Sort by any column by clicking header
- Soft delete with 8-second undo bar
- "Show deleted" toggle to view/restore removed rows

### Import (Admin Only)
- **Visible only to users with `role = 'admin'`** in the users table
- **Client CSV import** — headers: `client_id, service_day, address, phone, client_name, autopay`
- **Roll-offs CSV import** — headers: `date, type, customer, address_number, street, notes`
- Both import in 500-row batches (handles large datasets)
- Client import uses upsert — re-importing won't create duplicates
- Client import auto-merges rows with suffixed IDs (e.g. `001-1`, `001-2`) into a single row with comma-separated days
- Roll-off import handles both MM/DD/YYYY and YYYY-MM-DD date formats
- CSV parser handles quoted fields with commas (e.g. `"Smith, John"`)

### Security
- All user-generated content (names, addresses, notes, etc.) is HTML-escaped before rendering to prevent XSS
- Import data stored in JS variables instead of inline HTML to prevent injection
- Duplicate confirmation uses stored pending data instead of string interpolation
- Import tab restricted to admin users only

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
TRUNCATE TABLE notes;
TRUNCATE TABLE skips;
```
Then use the Import tab in HELM.

### To add a new staff user:
Run in Supabase SQL Editor:
```sql
INSERT INTO users (username, password, display_name, role)
VALUES ('newname', 'reis2026', 'Display Name', 'staff');
```

### To make a user admin:
```sql
UPDATE users SET role = 'admin' WHERE username = 'david';
```

---

## Known Constraints

- **Authentication** is simple shared password + per-user login. Not enterprise-grade — fine for a small internal team of ~5 users.
- **No real-time sync** — if two staff members are on the app simultaneously, one won't see the other's changes until they refresh or switch tabs.
- **Single file** means all CSS, JS, and HTML are in one place. Great for simplicity, but if the app grows significantly a proper build setup would be worth considering.
- **Autopay** is a simple yes/no flag — billing is handled externally. This field is informational only for customer reps.

---

## File Structure

```
helm-app/
├── index.html                    ← The entire application
├── sample_clients.csv            ← Template for client CSV import
├── rolloffs_clean.csv            ← Cleaned roll-off data ready for import
├── README.md                     ← This file
```

That's it. No dependencies to install, no build step, no config files.
