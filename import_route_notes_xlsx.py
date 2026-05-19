"""
import_route_notes_xlsx.py -- bulk-upload route notes from
"STOPS WITH RT NOTES.xlsx" into HELM's route_assignments table.

Source: C:\\Users\\theco\\Downloads\\STOPS WITH RT NOTES.xlsx
  Columns: idno (acct#), typd (status code), name, svaddr,
           rsnumber ("M-09      341" = day-letter / route / position),
           guide..guide4 (driver notes; we concatenate non-empty ones)

For each row whose acct exists in HELM AND whose rsnumber starts with a
valid day letter (M/T/W/R/F/S -- skipping A-prefix auxiliary routes per
project convention), upsert one route_assignments row keyed on
(client_id, day_of_week). Position and route_note get replaced with
what's in the spreadsheet (it's the latest source).

Usage:
  python import_route_notes_xlsx.py              # dry-run (default)
  python import_route_notes_xlsx.py --apply      # actually upsert

Outputs:
  route_notes_preview.csv          -- every planned upsert (always)
  route_notes_skipped.csv          -- rows skipped + reason
  route_notes_applied_log.csv      -- per-batch status (only on --apply)
"""
import openpyxl, json, re, csv, argparse, time
from collections import Counter, defaultdict
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = r"C:\Users\theco\OneDrive\Desktop\Nantucket\helm-app"
XLSX = r"C:\Users\theco\Downloads\STOPS WITH RT NOTES.xlsx"
SUPABASE_URL  = 'https://iiqlhqtyyqctgupalrlc.supabase.co'
SUPABASE_ANON = 'sb_publishable_JAASDdg8OERvpDTnEeLd5Q_Re48qR1I'

DAY_LETTER_TO_DOW = {'M':1, 'T':2, 'W':3, 'R':4, 'F':5, 'S':6}
DAY_NAMES = {1:'Mon',2:'Tue',3:'Wed',4:'Thu',5:'Fri',6:'Sat'}

# rsnumber format: "M-09      341" -> day letter, route number, position
RSN_RE = re.compile(r'^([A-Z])-(\d+)\s+(\d+)\s*$')


def parse_xlsx(path):
    """Returns (rows, skipped). Each row: dict with acct, day_of_week, route, position, route_note."""
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    rows, skipped = [], []
    for i, r in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue  # header
        if not r or r[0] is None:
            continue
        acct = str(r[0]).strip()
        if not acct:
            continue
        rsnumber = str(r[9] or '').strip()
        if not rsnumber:
            skipped.append({'acct': acct, 'reason': 'no rsnumber'})
            continue
        m = RSN_RE.match(rsnumber)
        if not m:
            skipped.append({'acct': acct, 'reason': f'rsnumber did not match pattern: "{rsnumber}"'})
            continue
        day_letter, route_str, pos_str = m.group(1), m.group(2), m.group(3)
        if day_letter not in DAY_LETTER_TO_DOW:
            skipped.append({'acct': acct, 'reason': f'non-day letter prefix: {day_letter}-'})
            continue
        # Combine non-empty guides into a single route_note
        guides = [str(r[10] or '').strip(), str(r[11] or '').strip(),
                  str(r[12] or '').strip(), str(r[13] or '').strip(),
                  str(r[14] or '').strip()]
        guides = [g for g in guides if g]
        note = ' / '.join(guides) if guides else None
        rows.append({
            'acct': acct,
            'day_of_week': DAY_LETTER_TO_DOW[day_letter],
            'route': int(route_str),
            'position': int(pos_str),
            'route_note': note,
            'name': str(r[7] or '').strip(),  # for preview only
        })
    return rows, skipped


def fetch_helm_accts():
    headers = {'apikey': SUPABASE_ANON, 'Authorization': f'Bearer {SUPABASE_ANON}'}
    accts = set()
    offset = 0
    while True:
        url = f'{SUPABASE_URL}/rest/v1/clients?select=client_id&order=client_id&offset={offset}&limit=1000'
        with urlopen(Request(url, headers=headers), timeout=30) as resp:
            batch = json.loads(resp.read().decode('utf-8'))
        if not batch: break
        for r in batch: accts.add(r['client_id'])
        if len(batch) < 1000: break
        offset += 1000
    return accts


def fetch_route_assignments():
    """Returns {(client_id, day_of_week): {route, position, route_note}}."""
    headers = {'apikey': SUPABASE_ANON, 'Authorization': f'Bearer {SUPABASE_ANON}'}
    out = {}
    offset = 0
    while True:
        url = f'{SUPABASE_URL}/rest/v1/route_assignments?select=client_id,day_of_week,route,position,route_note&offset={offset}&limit=1000'
        with urlopen(Request(url, headers=headers), timeout=30) as resp:
            batch = json.loads(resp.read().decode('utf-8'))
        if not batch: break
        for r in batch:
            out[(r['client_id'], r['day_of_week'])] = {
                'route': r['route'],
                'position': r['position'],
                'route_note': (r['route_note'] or '').strip(),
            }
        if len(batch) < 1000: break
        offset += 1000
    return out


def upsert_batch(rows, max_retries=3):
    url = f'{SUPABASE_URL}/rest/v1/route_assignments'
    headers = {
        'apikey': SUPABASE_ANON,
        'Authorization': f'Bearer {SUPABASE_ANON}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal,resolution=merge-duplicates',
    }
    data = json.dumps(rows).encode()
    last = None
    for attempt in range(max_retries):
        try:
            req = Request(url, data=data, headers=headers, method='POST')
            with urlopen(req, timeout=30) as resp: resp.read()
            return len(rows), None
        except HTTPError as e:
            err = f'HTTP {e.code}: {e.read().decode("utf-8", errors="replace")[:300]}'
            last = err
            if 400 <= e.code < 500: return 0, err
        except URLError as e:
            last = f'URLError: {e.reason}'
        time.sleep(0.5*(attempt+1))
    return 0, last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='Actually upsert. Default: dry-run.')
    ap.add_argument('--batch', type=int, default=200, help='Batch size (default 200).')
    args = ap.parse_args()

    print(f'Reading {XLSX}…')
    rows, skipped = parse_xlsx(XLSX)
    print(f'  {len(rows)} rows parsed, {len(skipped)} skipped')

    # Day-letter distribution
    by_day = Counter(r['day_of_week'] for r in rows)
    print('Per-day distribution:')
    for d in sorted(by_day):
        print(f'  {DAY_NAMES[d]} (dow={d}): {by_day[d]}')

    # Skipped reason distribution (top reasons)
    if skipped:
        sk_reasons = Counter(s['reason'].split(':')[0] for s in skipped)
        print('\nSkipped reasons:')
        for reason, n in sk_reasons.most_common(8):
            print(f'  {n:>5} {reason}')

    # Filter to accts in HELM
    print('\nFetching HELM acct list…')
    helm = fetch_helm_accts()
    print(f'  HELM has {len(helm)} clients')
    in_helm = [r for r in rows if r['acct'] in helm]
    not_in_helm = [r for r in rows if r['acct'] not in helm]
    print(f'  Excel rows where acct EXISTS in HELM:     {len(in_helm)}')
    print(f'  Excel rows where acct MISSING from HELM:  {len(not_in_helm)}')

    # Dedupe by (acct, dow) -- PK on route_assignments. Keep first occurrence;
    # warn if dups exist with different routes/positions.
    by_key = {}
    dup_collisions = []
    for r in in_helm:
        key = (r['acct'], r['day_of_week'])
        if key in by_key:
            prev = by_key[key]
            if prev['route'] != r['route'] or prev['position'] != r['position']:
                dup_collisions.append((key, prev, r))
            continue  # keep first
        by_key[key] = r
    upserts = list(by_key.values())
    if dup_collisions:
        print(f'\n[WARN] {len(dup_collisions)} (acct, day) collisions in spreadsheet -- kept the first row, dropped the rest:')
        for key, prev, dupd in dup_collisions[:5]:
            print(f'  {key[0]} dow{key[1]}: kept R{prev["route"]}/pos{prev["position"]} | dropped R{dupd["route"]}/pos{dupd["position"]}')

    print(f'\nPlanned upserts: {len(upserts)}')
    with_note    = sum(1 for r in upserts if r['route_note'])
    without_note = len(upserts) - with_note
    print(f'  With route_note populated:    {with_note} ({100*with_note/max(1,len(upserts)):.1f}%)')
    print(f'  Without route_note (positional only): {without_note}')

    # ── Delta analysis: classify each upsert vs current HELM state ──────
    print('\nFetching current route_assignments from HELM…')
    current = fetch_route_assignments()
    print(f'  HELM has {len(current)} existing route_assignments rows')

    cls = {
        'new':            0,  # no existing row for this (client, day)
        'identical':      0,  # exact match -- true no-op
        'route_changed':  0,  # route number differs
        'pos_only':       0,  # only position differs (driving-order shuffle)
        'note_filled':    0,  # existing note blank/null -> new note populated (additive)
        'note_changed':   0,  # both have notes, but different text (overwrite)
        'note_blanked':   0,  # existing note populated -> new is blank (destructive)
    }
    samples = {k: [] for k in cls}
    for r in upserts:
        key = (r['acct'], r['day_of_week'])
        new_note = (r['route_note'] or '').strip()
        existing = current.get(key)
        if not existing:
            cls['new'] += 1
            if len(samples['new']) < 3: samples['new'].append((r, None))
            continue
        old_note = (existing['route_note'] or '').strip()
        # Compare route
        if existing['route'] != r['route']:
            cls['route_changed'] += 1
            if len(samples['route_changed']) < 5: samples['route_changed'].append((r, existing))
            continue
        # Same route -- compare position
        position_diff = existing['position'] != r['position']
        # Compare note buckets
        if old_note == new_note:
            if position_diff:
                cls['pos_only'] += 1
                if len(samples['pos_only']) < 3: samples['pos_only'].append((r, existing))
            else:
                cls['identical'] += 1
        else:
            # Notes differ -- categorize
            if not old_note and new_note:
                cls['note_filled'] += 1
                if len(samples['note_filled']) < 3: samples['note_filled'].append((r, existing))
            elif old_note and not new_note:
                cls['note_blanked'] += 1
                if len(samples['note_blanked']) < 5: samples['note_blanked'].append((r, existing))
            else:
                cls['note_changed'] += 1
                if len(samples['note_changed']) < 5: samples['note_changed'].append((r, existing))

    print('\n=== What this upsert would actually change ===')
    print(f'  {"NEW rows (no existing for this client+day)":<48} {cls["new"]:>5}')
    print(f'  {"NO-OP -- identical to existing":<48} {cls["identical"]:>5}')
    print(f'  {"Position only (sort order shuffle, same route)":<48} {cls["pos_only"]:>5}')
    print(f'  {"Note FILLED (existing was blank -> new note added)":<48} {cls["note_filled"]:>5}')
    print('  ---- DESTRUCTIVE CHANGES BELOW ----')
    print(f'  {"ROUTE CHANGED (acct moves to a different route)":<48} {cls["route_changed"]:>5}')
    print(f'  {"NOTE CHANGED (existing note -> different note)":<48} {cls["note_changed"]:>5}')
    print(f'  {"NOTE BLANKED (existing note -> blank)":<48} {cls["note_blanked"]:>5}')

    destructive = cls['route_changed'] + cls['note_changed'] + cls['note_blanked']
    print(f'\n  TOTAL DESTRUCTIVE overwrites: {destructive}')

    # Show samples of destructive changes
    for label, key in [('Route changes', 'route_changed'),
                        ('Note text changes', 'note_changed'),
                        ('Note blanked (existing -> empty)', 'note_blanked')]:
        if samples[key]:
            print(f'\n  --- Sample {label} (first {len(samples[key])}): ---')
            for new_row, old_row in samples[key]:
                if key == 'route_changed':
                    print(f'    acct {new_row["acct"]} {DAY_NAMES[new_row["day_of_week"]]}: '
                          f'R{old_row["route"]}->R{new_row["route"]} ({new_row["name"][:30]})')
                else:
                    old_n = (old_row["route_note"] or "")[:50]
                    new_n = (new_row["route_note"] or "")[:50]
                    print(f'    acct {new_row["acct"]} {DAY_NAMES[new_row["day_of_week"]]}:')
                    print(f'      old: "{old_n}"')
                    print(f'      new: "{new_n}"')

    # Write preview CSV
    preview_path = ROOT + r'\route_notes_preview.csv'
    with open(preview_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['acct','name','day','route','position','route_note'])
        for r in sorted(upserts, key=lambda x:(x['acct'], x['day_of_week'])):
            w.writerow([r['acct'], r['name'], DAY_NAMES[r['day_of_week']],
                        r['route'], r['position'], r['route_note'] or ''])
    print(f'-> {preview_path}')

    # Write skipped CSV (acct not in HELM)
    skipped_path = ROOT + r'\route_notes_skipped.csv'
    with open(skipped_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['acct','name','day','route','position','route_note','reason'])
        for r in not_in_helm:
            w.writerow([r['acct'], r['name'], DAY_NAMES[r['day_of_week']],
                        r['route'], r['position'], r['route_note'] or '',
                        'acct not in HELM clients'])
        for s in skipped:
            w.writerow([s['acct'], '', '', '', '', '', s['reason']])
    print(f'-> {skipped_path}')

    if not args.apply:
        print('\n=== DRY RUN -- no DB writes. To apply: python import_route_notes_xlsx.py --apply ===')
        return

    # Split into two batches to handle the "preserve existing note" cases:
    #   - normal_rows include route_note in the payload (new value wins)
    #   - preserve_rows OMIT route_note so PostgREST leaves it untouched on conflict
    # The split criterion: existing route_note is non-empty AND new is empty.
    # Per-user request 2026-05-19 ("for the notes that go from filled in to
    # blank, just keep the filled in note").
    normal_rows = []
    preserve_rows = []
    for r in upserts:
        key = (r['acct'], r['day_of_week'])
        new_note = (r['route_note'] or '').strip()
        existing = current.get(key)
        if existing and (existing['route_note'] or '').strip() and not new_note:
            preserve_rows.append(r)
        else:
            normal_rows.append(r)
    print(f'\nSplit for safety: {len(normal_rows)} normal upserts + {len(preserve_rows)} preserve-existing-note upserts')

    normal_payload = [{
        'client_id': r['acct'],
        'day_of_week': r['day_of_week'],
        'route': r['route'],
        'position': r['position'],
        'route_note': r['route_note'],
        'source': 'xlsx_route_notes',
    } for r in normal_rows]
    # NOTE: 'route_note' key intentionally omitted from this payload.
    # PostgREST's INSERT ON CONFLICT only updates columns present in the
    # incoming row set, so existing route_note values stay untouched.
    preserve_payload = [{
        'client_id': r['acct'],
        'day_of_week': r['day_of_week'],
        'route': r['route'],
        'position': r['position'],
        'source': 'xlsx_route_notes',
    } for r in preserve_rows]

    def run_batches(label, payload):
        if not payload: return 0, 0
        print(f'\n=== APPLYING {len(payload)} {label} upserts (batches of {args.batch}) ===')
        applied = 0; failed = 0
        started = time.time()
        for i in range(0, len(payload), args.batch):
            chunk = payload[i:i+args.batch]
            ok, err = upsert_batch(chunk)
            if ok == len(chunk):
                applied += ok
            else:
                failed += len(chunk)
                print(f'  batch starting {i}: FAIL — {err}')
            elapsed = time.time() - started
            done = i + len(chunk)
            rate = done/max(elapsed,0.01)
            eta = (len(payload)-done)/max(rate,0.01)
            if (i//args.batch) % 5 == 0 or done == len(payload):
                print(f'  {done}/{len(payload)} {label}  ok={applied} fail={failed}  ({rate:.0f}/s eta {eta:.0f}s)')
        return applied, failed

    a1, f1 = run_batches('normal', normal_payload)
    a2, f2 = run_batches('preserve-note', preserve_payload)

    print(f'\n=== DONE ===')
    print(f'  Normal upserts:        applied={a1} failed={f1}')
    print(f'  Preserve-note upserts: applied={a2} failed={f2}')
    print(f'  TOTAL applied={a1+a2} failed={f1+f2}')


if __name__ == '__main__':
    main()
