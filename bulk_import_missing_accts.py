"""
bulk_import_missing_accts.py — insert every acct from missing_from_helm.csv
into HELM in one shot.

Source data:
  missing_from_helm.csv         — output of find_missing_accts.py (176 accts)
                                   — has acct, name (truncated), address (truncated),
                                     paused, days, routes, day_route_detail
  delta export retry.pdf         — broader NetWork export with FULL names,
                                   addresses, phones, status codes
                                   — used to enrich the master-list truncations

For each acct still missing in HELM (re-checked at import time, so any
manually-added rows are skipped, never overwritten):

  1. INSERT into clients with: client_id, client_name (full from delta if
     available), address (full from delta if available), phone, status
     (Active/Paused from master-list asterisk OR delta asterisk), service_day
     (from master-list day labels), route + route_note (legacy fallback from
     first day's route)
  2. UPSERT route_assignments rows from the master-list day_route_detail

Usage:
  python bulk_import_missing_accts.py              # dry-run (default)
  python bulk_import_missing_accts.py --apply      # actually insert

Outputs:
  bulk_import_preview.csv  — what would be inserted (always)
  bulk_import_applied.csv  — per-acct status log (--apply only)
"""
import pdfplumber, re, csv, json, time, argparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = r"C:\Users\theco\OneDrive\Desktop\Nantucket\helm-app"
MISSING_CSV = ROOT + r"\missing_from_helm.csv"
DELTA_RETRY = ROOT + r"\delta export retry.pdf"
SUPABASE_URL  = 'https://iiqlhqtyyqctgupalrlc.supabase.co'
SUPABASE_ANON = 'sb_publishable_JAASDdg8OERvpDTnEeLd5Q_Re48qR1I'

DAY_NAME_TO_DOW = {
    'Monday':1, 'Tuesday':2, 'Wednesday':3,
    'Thursday':4, 'Friday':5, 'Saturday':6,
}

# ─── Delta retry parsing (for full names + addresses + phones) ─────────
DELTA_HDR = re.compile(
    r'^(?P<acct>\d{6})(?P<star>\*)?\s*(?P<code>[A-Za-z0-9]{2,5})\s+'
    r'(?P<name_addr>.+?)\s+/\s+(?P<city>[A-Z][A-Z0-9][A-Z0-9\s]*?)\s+'
    r'(?P<key_date>\d{2}/\d{2}/\d{4})',
    re.M
)
PHONE_LINE = re.compile(
    r'^Phone1:\s*(?P<p1>\S.*?)?(?:\s+Phone2:\s*(?P<p2>\S.*?)?)?$',
    re.M
)


def parse_delta_retry(pdf_path):
    """Returns {acct: {'name', 'address', 'phone1', 'phone2', 'paused', 'status_code'}}."""
    with pdfplumber.open(pdf_path) as pdf:
        text = '\n'.join((p.extract_text() or '') for p in pdf.pages)
    out = {}
    lines = text.split('\n')
    for i, line in enumerate(lines):
        m = DELTA_HDR.match(line)
        if not m:
            continue
        acct = m.group('acct')
        if acct.startswith('1'):
            continue
        # Split off the trailing addr (starts with a number) from the name
        name_addr = m.group('name_addr').strip()
        addr_split = re.match(r'^(?P<name>.+?,?)\s+(?P<addr>\d+\S*(?:\s+.+)?)$', name_addr)
        if addr_split:
            name = addr_split.group('name').rstrip(',').strip()
            addr = addr_split.group('addr').strip()
        else:
            name = name_addr
            addr = ''
        rec = {
            'acct': acct,
            'name': name,
            'address': addr,
            'city': m.group('city'),
            'phone1': None,
            'phone2': None,
            'paused': bool(m.group('star')),
            'status_code': m.group('code'),
        }
        # The next line usually starts with "Phone1:"
        for j in range(i+1, min(i+4, len(lines))):
            pm = PHONE_LINE.match(lines[j].strip())
            if pm:
                p1 = (pm.group('p1') or '').strip()
                p2 = (pm.group('p2') or '').strip()
                rec['phone1'] = p1 if p1 else None
                rec['phone2'] = p2 if p2 else None
                break
        out[acct] = rec
    return out


def normalize_phone(raw):
    if not raw: return None
    s = str(raw).strip()
    if not s: return None
    digits = re.sub(r'\D', '', s)
    if len(digits) == 10:
        return f'{digits[0:3]}-{digits[3:6]}-{digits[6:]}'
    if len(digits) == 11 and digits[0] == '1':
        return f'{digits[1:4]}-{digits[4:7]}-{digits[7:]}'
    return s


# ─── Supabase ──────────────────────────────────────────────────────────
def http_request(method, url, payload=None):
    headers = {
        'apikey': SUPABASE_ANON,
        'Authorization': f'Bearer {SUPABASE_ANON}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal',
    }
    data = json.dumps(payload).encode() if payload is not None else None
    last = None
    for attempt in range(3):
        try:
            req = Request(url, data=data, headers=headers, method=method)
            with urlopen(req, timeout=20) as resp:
                resp.read()
            return True, None
        except HTTPError as e:
            err = f'HTTP {e.code}: {e.read().decode("utf-8", errors="replace")[:200]}'
            last = err
            if 400 <= e.code < 500:
                return False, err
        except URLError as e:
            last = f'URLError: {e.reason}'
        time.sleep(0.5*(attempt+1))
    return False, last


def fetch_helm_accts():
    headers = {'apikey': SUPABASE_ANON, 'Authorization': f'Bearer {SUPABASE_ANON}'}
    accts = set()
    offset = 0
    while True:
        url = f'{SUPABASE_URL}/rest/v1/clients?select=client_id&order=client_id&offset={offset}&limit=1000'
        req = Request(url, headers=headers)
        with urlopen(req, timeout=30) as resp:
            batch = json.loads(resp.read().decode('utf-8'))
        if not batch: break
        for r in batch: accts.add(r['client_id'])
        if len(batch) < 1000: break
        offset += 1000
    return accts


# ─── Main ──────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='Actually insert into HELM. Default: dry-run.')
    ap.add_argument('--limit', type=int, help='Limit to first N missing accts (smoke test).')
    args = ap.parse_args()

    # Load missing-list CSV (intended)
    intended = []
    with open(MISSING_CSV, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            intended.append(r)
    print(f'Intended (from missing_from_helm.csv): {len(intended)} accts')

    # Re-fetch HELM accts so we skip any that have been manually added since the CSV was generated
    print('Re-fetching HELM acct list…')
    helm = fetch_helm_accts()
    print(f'  HELM currently has {len(helm)} clients')
    to_do = [r for r in intended if r['acct'] not in helm]
    skipped_already_added = len(intended) - len(to_do)
    if skipped_already_added:
        print(f'  Skipping {skipped_already_added} that are already in HELM (manually-added since CSV gen)')
    print(f'  Will process {len(to_do)} accts')

    # Enrich with delta retry.pdf data (full names, addresses, phones)
    print(f'\nParsing {DELTA_RETRY} for enrichment…')
    delta = parse_delta_retry(DELTA_RETRY)
    print(f'  Got {len(delta)} delta records')
    enriched_count = sum(1 for r in to_do if r['acct'] in delta)
    print(f'  {enriched_count} of {len(to_do)} have a delta match (will get full name/addr/phone)')

    if args.limit:
        to_do = to_do[:args.limit]
        print(f'  --limit applied: trimmed to {len(to_do)}')

    # Build client + route payloads
    client_records = []
    route_records  = []
    skipped = []
    for r in to_do:
        acct = r['acct']
        delta_rec = delta.get(acct)
        # Name + address: prefer delta (un-truncated) over master-list CSV (truncated)
        name = (delta_rec['name'] if delta_rec and delta_rec.get('name') else r['name']).strip()
        addr = (delta_rec['address'] if delta_rec and delta_rec.get('address') else r['address']).strip()
        # Phone: prefer Phone1 from delta
        phone = normalize_phone(delta_rec.get('phone1') if delta_rec else None)
        # Paused: master-list asterisk OR delta asterisk
        paused = (r['paused'] == 'YES') or bool(delta_rec and delta_rec.get('paused'))
        # service_day = master list days, normalized to "Monday,Thursday" (no spaces)
        days_full = [d.strip() for d in r['days'].split(',') if d.strip()]
        service_day = ','.join(days_full) if days_full else None

        # Parse routes: "Monday=M-02; Thursday=R-02" → [(1,2), (4,2)] (dow, route_num)
        route_pairs = []
        for piece in r['day_route_detail'].split(';'):
            piece = piece.strip()
            if not piece or '=' not in piece: continue
            day_name, route_label = piece.split('=', 1)
            day_name = day_name.strip()
            dow = DAY_NAME_TO_DOW.get(day_name)
            if not dow: continue
            m = re.match(r'^[A-Z]-(\d+)$', route_label.strip())
            if not m: continue
            route_pairs.append((dow, int(m.group(1))))

        # Dedupe (dow uniqueness — PK on route_assignments is client_id+dow)
        seen_dows = set()
        unique_pairs = []
        for dow, rn in route_pairs:
            if dow in seen_dows: continue
            seen_dows.add(dow)
            unique_pairs.append((dow, rn))

        # clients.route + route_note synced to FIRST day's route (legacy fallback)
        first_route = unique_pairs[0][1] if unique_pairs else None

        # Validate minimal required fields
        if not addr:
            skipped.append({'acct': acct, 'reason': 'no address'})
            continue
        if not service_day:
            skipped.append({'acct': acct, 'reason': 'no service days'})
            continue

        client_records.append({
            'client_id': acct,
            'client_name': name or None,
            'address': addr,
            'phone': phone,
            'service_day': service_day,
            'status': 'Paused' if paused else 'Active',
            'route': first_route,
            'route_note': None,
            'autopay': False,
        })
        for dow, rn in unique_pairs:
            route_records.append({
                'client_id': acct,
                'day_of_week': dow,
                'route': rn,
                'position': None,
                'route_note': None,
                'source': 'master_list_import',
            })

    print(f'\nPlanned writes:')
    print(f'  clients INSERTs:           {len(client_records)}')
    print(f'  route_assignments UPSERTs: {len(route_records)}')
    if skipped:
        print(f'  Skipped (missing data):    {len(skipped)}')
        for s in skipped[:10]:
            print(f'    {s["acct"]}: {s["reason"]}')

    # Always write the preview CSV
    preview_path = ROOT + r'\bulk_import_preview.csv'
    with open(preview_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['acct','client_name','address','phone','service_day','status','route','route_assignments'])
        rt_by_acct = {}
        for r in route_records:
            rt_by_acct.setdefault(r['client_id'], []).append(f'dow{r["day_of_week"]}=R{r["route"]}')
        for c in client_records:
            rts = ', '.join(rt_by_acct.get(c['client_id'], []))
            w.writerow([c['client_id'], c['client_name'] or '', c['address'], c['phone'] or '',
                        c['service_day'], c['status'], c['route'] or '', rts])
    print(f'\nPreview -> {preview_path}')

    if not args.apply:
        print('\n=== DRY RUN — no DB writes. To apply: python bulk_import_missing_accts.py --apply ===')
        return

    # Apply: insert clients one-by-one, then upsert route_assignments per acct
    print(f'\n=== APPLYING {len(client_records)} client inserts + {len(route_records)} route upserts ===')
    applied_clients = 0
    applied_routes  = 0
    fail_clients    = 0
    fail_routes     = 0
    log_rows = []
    started = time.time()

    rt_by_acct = {}
    for r in route_records:
        rt_by_acct.setdefault(r['client_id'], []).append(r)

    for i, c in enumerate(client_records):
        ok, err = http_request('POST', f'{SUPABASE_URL}/rest/v1/clients', [c])
        if not ok:
            fail_clients += 1
            log_rows.append({'acct': c['client_id'], 'step': 'client_insert', 'status': 'FAIL', 'error': err or ''})
        else:
            applied_clients += 1
            # Upsert route_assignments for this acct
            rts = rt_by_acct.get(c['client_id'], [])
            if rts:
                url = f'{SUPABASE_URL}/rest/v1/route_assignments'
                headers = {
                    'apikey': SUPABASE_ANON,
                    'Authorization': f'Bearer {SUPABASE_ANON}',
                    'Content-Type': 'application/json',
                    'Prefer': 'return=minimal,resolution=merge-duplicates',
                }
                try:
                    req = Request(url, data=json.dumps(rts).encode(), headers=headers, method='POST')
                    with urlopen(req, timeout=20) as resp: resp.read()
                    applied_routes += len(rts)
                    log_rows.append({'acct': c['client_id'], 'step': 'routes_upsert', 'status': 'ok', 'error': f'{len(rts)} rows'})
                except Exception as e:
                    fail_routes += len(rts)
                    log_rows.append({'acct': c['client_id'], 'step': 'routes_upsert', 'status': 'FAIL', 'error': str(e)[:200]})
            else:
                log_rows.append({'acct': c['client_id'], 'step': 'client_insert', 'status': 'ok', 'error': '(no route rows)'})
        if (i+1) % 25 == 0 or (i+1) == len(client_records):
            elapsed = time.time() - started
            rate = (i+1)/max(elapsed,0.01)
            eta = (len(client_records)-(i+1))/max(rate,0.01)
            print(f'  {i+1}/{len(client_records)}  clients ok={applied_clients} fail={fail_clients} | routes ok={applied_routes} fail={fail_routes}  ({rate:.1f}/s eta {eta:.0f}s)')

    print(f'\n=== DONE === clients applied={applied_clients}/{len(client_records)}  routes applied={applied_routes}/{len(route_records)}  failures: clients={fail_clients} routes={fail_routes}')

    log_path = ROOT + r'\bulk_import_applied.csv'
    with open(log_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['acct','step','status','error'])
        w.writeheader()
        for r in log_rows: w.writerow(r)
    print(f'Log -> {log_path}')


if __name__ == '__main__':
    main()
