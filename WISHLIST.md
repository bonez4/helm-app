# HELM / BEACON — Wishlist & Vision

*Working wishlist for the centralization/integration effort. **Not exhaustive** — a living list.*
*Pair with `INTEGRATION.md` (how the systems connect) + `README.md` (current state).*

### Who-builds-what legend
- ✅ **In-app, buildable now** — lives in HELM/BEACON + Supabase; Claude can build against data we already have.
- 🔧 **In-app, needs a small new tracker first** — buildable by Claude, but we must start capturing the data (e.g. a status-change log) before the report is possible.
- 🔌 **Needs external integration** — the software developer must connect an outside system (Nextiva, Delta, QuickBooks) and get its data into Supabase; *then* Claude builds the in-app report on top.

---

## A. Reporting — run Daily / Weekly / Monthly

### i. Phone calls (Nextiva)
- 🔌 Calls per day
- 🔌 Average duration per call
- 🔌 "Rings to answer"
> All require a **Nextiva integration** (their API/call-analytics → Supabase). Once call data lands in a table, the reports are easy.

### ii. Clientele
- 🔧 New account **turn-ons** (reactivations: Paused/Inactive → Active)
- ✅ New account **creations** (from the client record's created/added date)
- 🔧 **Turned-off** accounts (→ Inactive)
- 🔧 **Paused** accounts (→ Paused)
- ✅ **Note submissions** (already in HELM — `notes`)
- ✅ **Complaints / resolutions achieved** (already in HELM — `complaints` + `complaint_actions`)
> The 🔧 items need a **status-change log**: today `clients.status` only holds the *current* value with no history, so turn-ons/turn-offs/pauses aren't reportable until we start recording each change. **This should be turned on ASAP — you can't report history you didn't capture.**

### iii. Sales / CRM
- 🔧 **Sales — "clients located"** *(needs a definition — see open questions)*
- ✅ **Images uploaded to BEACON** — **already shipped** (BEACON → Reports → Activity Report, date-filtered)
- 🔧 **Calls made to clients for bulky dispatch** — the dispatch Outreach stage isn't logged per-call yet; small add to capture each call
- ✅/🔧 **Conversion: % of outreach → sales** — from `dispatch_jobs` (accepted vs denied at Outreach) + the job's `price_items` for the $ amount. (Note: $ was deliberately removed from the *commercial* business tracking; dispatch jobs still carry line-item $.)

---

## B. The "Big" Projects

### 1. HELM/BEACON as a legitimate client-service platform — a true customer 360
Everything about a customer in one place: notes, complaints + resolutions, service records, **billing records**, route notes/integration, history, contacts.
- ✅ Notes, complaints/resolutions, route notes, contacts, photo history — **largely exist today**; the work is a unified "customer profile" view that pulls it together.
- 🔌 **Billing/service records** — needs the billing system (QuickBooks?) connected; then surfaced on the customer profile.

### 2. Real CRM tools — outreach, new & lost business tracking
- ✅ **Largely shipped in BEACON** already: new/lost business events, contact log (outreach), contact-recency, dashboard + reports, lost-clients log. The work is extending/refining (e.g. conversion metrics, pipelines).

---

## C. Known pain points
- 🔌 **Delta (legacy software) is single-computer access.** This is the core reason for the whole centralization effort. Two angles: (1) *stopgap* — remote-access that one PC so staff aren't bottlenecked; (2) *real fix* — migrate Delta's data into Supabase so HELM/BEACON (cloud, multi-user, accessible anywhere) becomes the system of record and Delta can be retired.

---

## Open questions to resolve
1. **Define "clients located" / "sales"** — a newly-signed commercial account? A qualified lead? A bulky job sold? This decides how we count it.
2. **Where do business-wide reports live** — one Reports hub (in HELM? BEACON?) spanning office staff + clientele + commercial + bulky dispatch, or per-app?
3. **Office software names** — QuickBooks? a hauling system? Is Delta the only legacy app, or also NetWork? (Shapes every 🔌 item.)
4. **Billing master** — stays in the billing software, or Supabase becomes master?
