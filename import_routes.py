"""
import_routes.py — fill route_assignments from delta export retry 2.pdf

For each acct in HELM that has route records in the legacy master list,
upsert one row per (client_id, day_of_week) into route_assignments.

Day-letter mapping:  M=1 T=2 W=3 R=4 F=5 S=6

Usage:
  python import_routes.py              # dry-run preview only
  python import_routes.py --apply      # actually upsert
  python import_routes.py --apply --limit 25   # apply first 25 (smoke test)

Outputs:
  import_routes_preview.csv   (always)  — every (client, day, route, pos, note) row we'd upsert
  import_routes_applied.csv   (--apply) — what made it (per-row status)

Pre-req: route_assignments table must exist in Supabase. SQL is in the README.
"""
import pdfplumber, re, json, csv, sys, time, argparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# ─── config ────────────────────────────────────────────────────────────
ROOT = r"C:\Users\theco\OneDrive\Desktop\Nantucket\helm-app"
PDF = ROOT + r"\delta export retry 2.pdf"
SUPABASE_URL  = 'https://iiqlhqtyyqctgupalrlc.supabase.co'
SUPABASE_ANON = 'sb_publishable_JAASDdg8OERvpDTnEeLd5Q_Re48qR1I'

DAY_LETTER_TO_NUM = {'M': 1, 'T': 2, 'W': 3, 'R': 4, 'F': 5, 'S': 6}

# ─── PDF parser ────────────────────────────────────────────────────────
SEPARATOR_RE = re.compile(r'^\s*(?:\.\s+){10,}\.?\s*$', re.M)
PAGE_HEADER_PATTERNS = [
    re.compile(r'^Master List.*PAGE\s+\d+\s*$'),
    re.compile(r'^[SAERVICLOTNB]+(\s+[SAERVICLOTNB]+)+\s*$'),
    re.compile(r'^A C C O U N T.*$'),
    re.compile(r'^=+\s*$'),
]
ACCT_RE = re.compile(r'^(?P<acct>\d{6})\s+(?P<status_code>[A-Za-z0-9]{2,5})\s+')
ROUTE_HEADER_RE = re.compile(
    r'^(?P<count>\d+) Route Records?\s+'
    r'(?P<day>[A-Z])-(?P<route>\d+)\s+(?P<pos>\d+)(?:\s+(?P<note>.*))?$'
)
ROUTE_CONT_RE = re.compile(
    r'^(?P<day>[A-Z])-(?P<route>\d+)\s+(?P<pos>\d+)(?:\s+(?P<note>.*))?$'
)


def is_page_header(line):
    return any(p.match(line) for p in PAGE_HEADER_PATTERNS)


def extract_route_records(pdf_path):
    """Walk PDF block-by-block and return:
        {acct: [{'day_letter': 'M', 'route': 2, 'position': 520, 'note': '...'}, ...]}
    Skips 1xxxxx system accts and any route record whose day-letter isn't M/T/W/R/F/S."""
    with pdfplumber.open(pdf_path) as pdf:
        full = '\n'.join((p.extract_text() or '') for p in pdf.pages)

    cleaned = []
    for line in full.split('\n'):
        s = line.strip()
        if not s or is_page_header(s):
            continue
        cleaned.append(s)
    text = '\n'.join(cleaned)

    blocks = SEPARATOR_RE.split(text)
    out = {}
    skipped_by_letter = {}  # letter -> count
    for blk in blocks:
        if not blk.strip():
            continue
        lines = [l for l in blk.split('\n') if l.strip()]

        # Find the acct line
        acct = None
        acct_idx = None
        for i, line in enumerate(lines):
            m = ACCT_RE.match(line)
            if m:
                acct = m.group('acct')
                acct_idx = i
                break
        if not acct or acct.startswith('1'):
            continue

        # Find "N Route Records ..." header line and parse it + N-1 continuations
        for i in range(acct_idx + 1 if acct_idx is not None else 0, len(lines)):
            mh = ROUTE_HEADER_RE.match(lines[i])
            if not mh:
                continue
            n_records = int(mh.group('count'))
            recs = []

            # First record on header line
            day_letter = mh.group('day')
            if day_letter not in DAY_LETTER_TO_NUM:
                skipped_by_letter[day_letter] = skipped_by_letter.get(day_letter, 0) + 1
            else:
                recs.append({
                    'day_letter': day_letter,
                    'route': int(mh.group('route')),
                    'position': int(mh.group('pos')),
                    'note': (mh.group('note') or '').strip(),
                })

            # Continuation rows
            for j in range(1, n_records):
                if i + j >= len(lines):
                    break
                mc = ROUTE_CONT_RE.match(lines[i + j])
                if not mc:
                    break
                dl = mc.group('day')
                if dl not in DAY_LETTER_TO_NUM:
                    skipped_by_letter[dl] = skipped_by_letter.get(dl, 0) + 1
                    continue
                recs.append({
                    'day_letter': dl,
                    'route': int(mc.group('route')),
                    'position': int(mc.group('pos')),
                    'note': (mc.group('note') or '').strip(),
                })

            if recs:
                out[acct] = recs
            break  # one route block per client

    if skipped_by_letter:
        total_skipped = sum(skipped_by_letter.values())
        breakdown = ', '.join(f'{k}={v}' for k, v in sorted(skipped_by_letter.items()))
        print(f'  skipped {total_skipped} route records with non-day letters: {breakdown}')
    return out


# ─── Supabase ──────────────────────────────────────────────────────────
def fetch_helm_acct_set():
    headers = {'apikey': SUPABASE_ANON, 'Authorization': f'Bearer {SUPABASE_ANON}'}
    accts = set()
    offset = 0
    while True:
        url = f'{SUPABASE_URL}/rest/v1/clients?select=client_id&order=client_id&offset={offset}&limit=1000'
        req = Request(url, headers=headers)
        with urlopen(req, timeout=30) as resp:
            batch = json.loads(resp.read().decode('utf-8'))
        if not batch:
            break
        for r in batch:
            accts.add(r['client_id'])
        if len(batch) < 1000:
            break
        offset += 1000
    return accts


def upsert_batch(rows, max_retries=3):
    """Upsert a batch of route_assignments rows. Returns (ok_count, error)."""
    url = f'{SUPABASE_URL}/rest/v1/route_assignments'
    headers = {
        'apikey': SUPABASE_ANON,
        'Authorization': f'Bearer {SUPABASE_ANON}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal,resolution=merge-duplicates',
    }
    data = json.dumps(rows).encode()
    last_err = None
    for attempt in range(max_retries):
        try:
            req = Request(url, data=data, headers=headers, method='POST')
            with urlopen(req, timeout=30) as resp:
                resp.read()
            return len(rows), None
        except HTTPError as e:
            err = f'HTTP {e.code}: {e.read().decode("utf-8", errors="replace")[:300]}'
            last_err = err
            if 400 <= e.code < 500:
                return 0, err
        except URLError as e:
            last_err = f'URLError: {e.reason}'
        time.sleep(0.5 * (attempt + 1))
    return 0, last_err


# ─── main ──────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='Actually upsert. Default is dry-run.')
    ap.add_argument('--limit', type=int, default=None, help='Limit to first N clients (smoke test).')
    ap.add_argument('--batch', type=int, default=200, help='Batch size for upserts (default 200).')
    args = ap.parse_args()

    print(f'Parsing PDF: {PDF}')
    routes_by_acct = extract_route_records(PDF)
    total_recs = sum(len(v) for v in routes_by_acct.values())
    print(f'  {len(routes_by_acct)} accts, {total_recs} route records')

    print('Fetching HELM acct list...')
    helm_accts = fetch_helm_acct_set()
    print(f'  {len(helm_accts)} HELM clients')

    # Inner join: only accts in BOTH HELM and PDF
    candidates = sorted(a for a in routes_by_acct if a in helm_accts)
    print(f'  {len(candidates)} candidates (HELM ∩ PDF with routes)'.encode('ascii', 'replace').decode('ascii'))

    if args.limit:
        candidates = candidates[:args.limit]
        print(f'  --limit applied: trimmed to {len(candidates)} clients')

    # Build flat row list (deduped by (client_id, day_of_week) — PK constraint)
    seen = {}
    duplicates = []
    flat_rows = []
    for acct in candidates:
        for r in routes_by_acct[acct]:
            key = (acct, DAY_LETTER_TO_NUM[r['day_letter']])
            row = {
                'client_id': acct,
                'day_of_week': DAY_LETTER_TO_NUM[r['day_letter']],
                'route': r['route'],
                'position': r['position'],
                'route_note': r['note'] or None,
                'source': 'delta',
            }
            if key in seen:
                duplicates.append((key, seen[key], row))
                continue  # keep the FIRST occurrence per (client, day)
            seen[key] = row
            flat_rows.append(row)

    if duplicates:
        print(f'\n[WARN] {len(duplicates)} duplicate (client_id, day) pairs in source PDF — kept first, dropped rest:')
        for (acct, dow), kept, dropped in duplicates[:10]:
            day_names = {1:'Mon',2:'Tue',3:'Wed',4:'Thu',5:'Fri',6:'Sat'}
            print(f'  acct {acct} {day_names[dow]}: kept R{kept["route"]} pos {kept["position"]} -- dropped R{dropped["route"]} pos {dropped["position"]}')
        if len(duplicates) > 10:
            print(f'  ... and {len(duplicates) - 10} more')

    print(f'\nTotal route_assignments rows to upsert: {len(flat_rows)}')

    # Day distribution
    day_counts = {}
    for r in flat_rows:
        day_counts[r['day_of_week']] = day_counts.get(r['day_of_week'], 0) + 1
    print('Per-day row counts:')
    day_names = {1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat'}
    for d in sorted(day_counts):
        print(f'  {day_names[d]} (day_of_week={d}): {day_counts[d]}')

    # Notes: how many have one
    with_notes = sum(1 for r in flat_rows if r['route_note'])
    print(f'Rows with route_note populated: {with_notes}/{len(flat_rows)} ({100*with_notes/max(1,len(flat_rows)):.1f}%)')

    # Always write preview CSV
    with open('import_routes_preview.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['client_id', 'day_of_week', 'day_name', 'route', 'position', 'route_note'])
        for r in flat_rows:
            w.writerow([r['client_id'], r['day_of_week'], day_names[r['day_of_week']],
                        r['route'], r['position'], r['route_note'] or ''])
    print(f'\nPreview CSV: import_routes_preview.csv')

    if not args.apply:
        print('\n=== DRY RUN -- no DB writes ===')
        print('To apply: python import_routes.py --apply')
        return

    # Apply in batches
    print(f'\n=== APPLYING {len(flat_rows)} upserts in batches of {args.batch} ===')
    applied = 0
    failed = 0
    failures = []
    started = time.time()
    with open('import_routes_applied.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['batch_start', 'batch_size', 'status', 'error'])
        for i in range(0, len(flat_rows), args.batch):
            chunk = flat_rows[i:i + args.batch]
            ok_count, err = upsert_batch(chunk)
            if ok_count == len(chunk):
                applied += ok_count
                w.writerow([i, len(chunk), 'ok', ''])
            else:
                failed += len(chunk)
                failures.append((i, err))
                w.writerow([i, len(chunk), 'FAIL', err or ''])
            elapsed = time.time() - started
            done = i + len(chunk)
            rate = done / max(elapsed, 0.01)
            eta = (len(flat_rows) - done) / max(rate, 0.01)
            print(f'  {done}/{len(flat_rows)}  ok={applied} fail={failed}  ({rate:.0f} rows/s  eta {eta:.0f}s)')

    print(f'\n=== DONE ===  applied={applied}  failed={failed}')
    if failures:
        print('First 5 batch failures:')
        for start, err in failures[:5]:
            print(f'  batch starting at row {start}: {err}')


if __name__ == '__main__':
    main()
