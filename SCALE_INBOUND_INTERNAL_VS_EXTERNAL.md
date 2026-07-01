# Scale Report Parsing — Inbound Tonnage: Internal vs. External Volume

_How HELM turns a daily scale-house `.xls` export into the **Internal Volume** and **External Volume** inbound-tonnage figures shown on the daily email + the Intercompany Rolloff tab. Written so the numbers can be reconciled against the raw scale file. All logic is in `index.html`; key functions referenced inline._

---

## 1. The two numbers, in one line

For any date (or date range):

```
Internal Volume (tons) = reis_tons + island_tons + santos_tons
External Volume (tons) = walkin_tons + pile_tons
Total Inbound   (tons) = Internal + External
Outbound        (tons) = vinagro_tons          ← separate; NOT part of inbound
```

- **Internal** = the Reis family's own + intercompany **rolloff** hauls into the transfer station: **Reis Rolloff + Island Rubbish + East End (Santos)**.
- **External** = **walk-in / drive-through** customers (third-party retail drop-offs) **+ Reis pile pickups**.
- **Outbound** = **Vinagro** tonnage hauled off-island to the mainland landfill. Tracked, but it is *not* inbound and is never added into Internal/External/Total.

Aggregation function: `irrLoadYTD()` → its inner `sum()` (index.html ~line 12309):
```js
r.rolloff += reis + island + santos;                 // Internal Volume
r.walkin  += walkin + (parseFloat(d.pile_tons)||0);  // External Volume (pile folded in)
r.vin     += vin;                                    // Outbound
```

---

## 2. Where the stored numbers live: `irr_reports`

One row per `report_date` in the Supabase `irr_reports` table. The tonnage columns:

| Column | Bucket | Volume class |
|---|---|---|
| `reis_tons` | Reis Rolloff | **Internal** |
| `island_tons` | Island Rubbish (`ZZISLAND`) | **Internal** |
| `santos_tons` | East End (`ZZEASTEND`) | **Internal** |
| `walkin_tons` | Walk-in / drive-through | **External** |
| `pile_tons` | Reis pile pickups (`ZZDELTA`) | **External** (folded into walk-in) |
| `vinagro_tons` | Vinagro output (`ZZREIS`) | **Outbound** |
| `total_inbound_tons` | = reis+island+santos+walkin+pile | **Total inbound** |

So `total_inbound_tons` (stored at save time) **equals** `Internal + External` by construction — that's *why* pile is folded into External in the aggregator (so the recomputed total matches the stored total). Written by `irrSaveReport()` (~line 12355):
```js
totalTons = reis.tons + pile.tons + island.tons + santos.tons + walkin.tons;
```

**These stored figures are the source of truth for every downstream view** — the daily email, the Intercompany Rolloff tab, Scale KPIs, etc. If a figure looks wrong, first check the `irr_reports` row, then trace back to the parse of that day's `.xls`.

---

## 3. How a ticket's tonnage is extracted (the parser)

Parser: `irrParseReport(rows)` (~line 11662). The `.xls` lists tickets grouped under company sections. The parser does two things per ticket: (a) find its **net tonnage**, (b) decide its **company bucket**.

### 3a. Net tonnage — comes ONLY from "REIS SITE TRANSFER FEE" lines
For every row whose text contains `REIS SITE TRANSFER FEE`, the **net weight (in tons)** is the value **two cells after** that label, and it is summed onto that ticket:
```js
const net = parseFloat(dataVals[fi+2]) || 0;   // fi = index of "REIS SITE TRANSFER FEE"
tickets[ticket].tons += net;
```
A ticket can have several transfer-fee lines; they sum. **This is the single source of tonnage.** ⚠️ See Caveat #1 — tonnage billed on *other* `$/tn` line types is **not** counted.

### 3b. Company bucket — from the section code (with ZZ nesting)
The parser tracks the current company **code** from the section header/total lines (`"CODE - Name"` … `"CODE - … Totals"`), using a stack so nested sections inherit a `ZZ` parent (`effectiveCode = parentCode if it starts with 'ZZ', else currentCode`). Non-`ZZ` rolloff tickets are recognized by a **rolloff service keyword**:
```js
IRR_ROLLOFF_SVC = ['ROLLOFF DELIVERY','ROLLOFF DOUBLE DROP','EMPTY ROLLOFF','EMPTY ROLL-OFF'];
```

### 3c. Ticket → bucket → volume class
Final assignment loop (~line 11717):

| Ticket's company code | Bucket (`irr_reports` col) | Volume class |
|---|---|---|
| non-`ZZ` **with** a rolloff-service keyword | `reis` (`reis_tons`) | **Internal** |
| `ZZISLAND` | `island` (`island_tons`) | **Internal** |
| `ZZEASTEND` | `santos` (`santos_tons`) | **Internal** |
| `ZZDELTA` | `pile` (`pile_tons`) | **External** (via fold-in) |
| non-`ZZ` **without** a service keyword | `walkin` (`walkin_tons`) | **External** |
| any other `ZZ*` (e.g. `ZZTNT`) | `walkin` (`walkin_tons`) | **External** |
| `ZZREIS` | `vinagro` (`vinagro_tons`) | **Outbound** |

That's the whole internal/external split: **Internal = Reis-rolloff + `ZZISLAND` + `ZZEASTEND`**, **External = walk-ins + `ZZDELTA` pile**, **Outbound = `ZZREIS`**.

---

## 4. Post-parse reclassification (Review IC Tickets modal)

Before the row is saved, `irrShowReclassify()` (~line 13626) surfaces every `ZZISLAND` / `ZZEASTEND` / `ZZDELTA` ticket with three checkboxes. This **moves tons between buckets**, so the stored numbers reflect the *post-reclassification* state, not the raw file:

- **Exclude** — drop the ticket entirely (its tons are zeroed and removed from all totals). For misclassified/duplicate tickets. *Exclude wins if multiple boxes are checked.*
- **Pile Pickup** — an Island/East End ticket that was actually a pile pickup → its tons **move from Internal (`island`/`santos`) to External (`walkin`)**.
- **Walk In** — an IC ticket that was actually a walk-in → tons **move to External (`walkin`)**.

So a day where tickets were reclassified will not foot to the raw file section totals — that's expected.

---

## 5. What the daily email / Intercompany Rolloff tab display

Same `irrLoadYTD()` values, laid out (~line 12172) as five rows each (Today / MTD / MTD YoY / YTD / YTD YoY):

- **Internal Volume** → `rolloff` (reis+island+santos). Today row shows internal ticket count = `reis+island+santos` tickets.
- **External Volume** → `walkin` (walkin+pile). Today row shows external ticket count = `walkin` tickets.
- **Total Volume** → Internal + External.
- **Outbound** → `vin` (vinagro).

The Intercompany Rolloff tab pulls the **same** `irrLoadYTD()` values, so the on-screen table and the email reconcile to the cent.

---

## 6. Verifying against the raw scale `.xls`

To reconcile a day's **Internal** and **External** tonnage by hand:

1. **Internal** = Σ net tons of every **non-ZZ rolloff-service ticket** + every **`ZZISLAND`** ticket + every **`ZZEASTEND`** ticket.
2. **External** = Σ net tons of every **walk-in ticket** (non-ZZ with no rolloff-service line, plus any `ZZ*` that isn't ISLAND/EASTEND/DELTA/REIS) + every **`ZZDELTA`** ticket.
3. **Total inbound** = Internal + External (should equal stored `total_inbound_tons`).
4. Net tons per ticket = the value 2 cells right of each `REIS SITE TRANSFER FEE` line, summed.
5. Then apply any **reclassifications** that were made in the Review IC modal for that date (exclude / move-to-walk-in), because the stored figures already reflect them.

If HELM's stored number differs from your hand total, the gap is almost always one of the caveats below.

---

## 7. Known caveats (read before flagging a discrepancy)

1. **Tonnage undercount on non-transfer-fee lines (KNOWN OPEN ISSUE).** Tonnage is summed **only** from `REIS SITE TRANSFER FEE` lines. Weight billed on other `$/tn` line items — e.g. **`METAL DROPPED OFF @ REIS YARD`** — is **not** counted. Real example: East End read **6.02 t** vs. the true **6.84 t** on 6/4 (~0.8 t/day gap). This is why the Delta-side `deltawaste_display` report can run slightly higher than HELM. Fix would be: sum net from any `$/tn` line, not just transfer fees. *Not yet applied.*
2. **Pile (`ZZDELTA`) is folded into External.** Counted as External and included in Total Inbound. Before the June 2026 fix it was omitted from Total Inbound, which ran MTD ~54 t low vs. the stored `total_inbound_tons`. If comparing to an old export, check whether pile was included.
3. **Reclassification changes the stored numbers.** Exclude / Pile / Walk-In moves in the Review IC modal (§4) mean stored figures ≠ raw file section totals for that day.
4. **`ZZREIS` is Outbound, not inbound.** Don't add Vinagro tonnage into Internal/External/Total inbound. It's the haul *off* the island.
5. **Revenue ≠ tonnage, and revenue ≠ the file's "Report Totals."** This doc is tonnage only. Revenue is recomputed (hardcoded rolloff fees, per-unit disposal fees, intercompany hook fees) and intentionally diverges from the file's grand total — a separate topic.
6. **Timezone / date.** `report_date` is a plain date; ranges (MTD/YTD/etc.) in `irrLoadYTD` are computed from the report's own date, not wall-clock.

---

## 8. Code map (index.html)

| Function | ~Line | Role |
|---|---|---|
| `irrParseReport(rows)` | 11662 | Parse `.xls` → per-ticket tons + company bucket |
| `IRR_ROLLOFF_SVC` | 11563 | Keywords that mark a non-ZZ ticket as Reis rolloff |
| `irrShowReclassify()` / `irrReclassifyConfirm()` | 13626 / 13697 | Review IC Tickets modal (Exclude / Pile / Walk-In) |
| `irrSaveReport(data)` | 12355 | Upsert the day's buckets → `irr_reports` |
| `irrLoadYTD(asOfDate)` | 12252 | Aggregate `irr_reports` → Internal/External/Total/Outbound over Today/WTD/MTD/YTD/YoY |
| daily-email builder | ~12172 | Renders the Internal/External/Total/Outbound sections |

**Bottom line for verification:** Internal = Reis-rolloff + Island + East End; External = walk-ins + pile; both are built from `REIS SITE TRANSFER FEE` net tons, bucketed by company code, adjusted by any IC reclassification, and stored in `irr_reports`. Discrepancies vs. the raw file are almost always Caveat #1 (metal/other $/tn lines) or a reclassification.
