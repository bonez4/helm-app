"""
sync_client_route_fallback.py — for every client that has at least one row
in route_assignments, copy that client's first-day (lowest day_of_week)
route + route_note down to clients.route / clients.route_note.

After the May 19 XLSX import, the per-day route_assignments table is the
source of truth. The clients.route / clients.route_note columns are kept
as a single-field fallback for surfaces like the Lookup card pill. This
script syncs them so the pill matches the per-day data.

Usage:
  python sync_client_route_fallback.py            # dry-run
  python sync_client_route_fallback.py --apply    # actually patch
"""
import json, time, csv, argparse
from collections import defaultdict
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = r"C:\Users\theco\OneDrive\Desktop\Nantucket\helm-app"
SUPABASE_URL  = 'https://iiqlhqtyyqctgupalrlc.supabase.co'
SUPABASE_ANON = 'sb_publishable_JAASDdg8OERvpDTnEeLd5Q_Re48qR1I'


def fetch_route_assignments():
    headers = {'apikey': SUPABASE_ANON, 'Authorization': f'Bearer {SUPABASE_ANON}'}
    out = []
    offset = 0
    while True:
        url = f'{SUPABASE_URL}/rest/v1/route_assignments?select=client_id,day_of_week,route,route_note&offset={offset}&limit=1000'
        with urlopen(Request(url, headers=headers), timeout=30) as resp:
            batch = json.loads(resp.read().decode('utf-8'))
        if not batch: break
        out.extend(batch)
        if len(batch) < 1000: break
        offset += 1000
    return out


def fetch_clients_route():
    """Returns {client_id: {'route': X, 'route_note': Y}} for comparison."""
    headers = {'apikey': SUPABASE_ANON, 'Authorization': f'Bearer {SUPABASE_ANON}'}
    out = {}
    offset = 0
    while True:
        url = f'{SUPABASE_URL}/rest/v1/clients?select=client_id,route,route_note&offset={offset}&limit=1000'
        with urlopen(Request(url, headers=headers), timeout=30) as resp:
            batch = json.loads(resp.read().decode('utf-8'))
        if not batch: break
        for r in batch:
            out[r['client_id']] = {
                'route': r.get('route'),
                'route_note': (r.get('route_note') or '').strip(),
            }
        if len(batch) < 1000: break
        offset += 1000
    return out


def patch_client(client_id, route, route_note, max_retries=3):
    url = f'{SUPABASE_URL}/rest/v1/clients?client_id=eq.{client_id}'
    headers = {
        'apikey': SUPABASE_ANON,
        'Authorization': f'Bearer {SUPABASE_ANON}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal',
    }
    payload = {'route': route, 'route_note': route_note}
    data = json.dumps(payload).encode()
    last = None
    for attempt in range(max_retries):
        try:
            req = Request(url, data=data, headers=headers, method='PATCH')
            with urlopen(req, timeout=15) as resp: resp.read()
            return True, None
        except HTTPError as e:
            err = f'HTTP {e.code}: {e.read().decode("utf-8", errors="replace")[:200]}'
            last = err
            if 400 <= e.code < 500: return False, err
        except URLError as e:
            last = f'URLError: {e.reason}'
        time.sleep(0.4*(attempt+1))
    return False, last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='Actually PATCH clients. Default: dry-run.')
    args = ap.parse_args()

    print('Fetching route_assignments…')
    ra = fetch_route_assignments()
    print(f'  {len(ra)} route_assignments rows')

    print('Fetching clients.route / route_note current values…')
    clients = fetch_clients_route()
    print(f'  {len(clients)} clients')

    # Group route_assignments by client; pick the row with the lowest day_of_week
    by_client = defaultdict(list)
    for r in ra:
        by_client[r['client_id']].append(r)

    # For each client with at least one route row, compute the "first day" winner
    target = {}
    for cid, rows in by_client.items():
        rows.sort(key=lambda x: (x['day_of_week'], x.get('route') or 0))
        first = rows[0]
        target[cid] = {
            'route': first['route'],
            'route_note': (first.get('route_note') or '').strip() or None,
        }
    print(f'  {len(target)} clients have at least one route row')

    # Compare against current clients.route / route_note
    to_patch = []
    no_op = 0
    no_existing_client = 0
    for cid, t in target.items():
        existing = clients.get(cid)
        if not existing:
            no_existing_client += 1
            continue
        cur_route = existing['route']
        cur_note = existing['route_note'] or None  # treat empty as None for comparison
        # PostgREST returns None for null, but clients.route is SMALLINT
        new_route = t['route']
        new_note = t['route_note']
        if cur_route == new_route and (cur_note or None) == (new_note or None):
            no_op += 1
            continue
        to_patch.append({
            'client_id': cid,
            'old_route': cur_route, 'new_route': new_route,
            'old_note':  cur_note,  'new_note':  new_note,
        })

    print(f'\n  No-op (already matches first-day route_assignment):  {no_op}')
    print(f'  Will PATCH (route or route_note differs):            {len(to_patch)}')
    if no_existing_client:
        print(f'  Skipped (route_assignment row references missing client): {no_existing_client}')

    # Classify the differences
    only_route = sum(1 for r in to_patch if (r['old_note'] or None) == (r['new_note'] or None))
    only_note  = sum(1 for r in to_patch if r['old_route'] == r['new_route'])
    both       = len(to_patch) - only_route - only_note
    print(f'\n  Of those PATCHes:')
    print(f'    Only route differs:      {only_route}')
    print(f'    Only route_note differs: {only_note}')
    print(f'    Both differ:             {both}')

    # Write preview
    preview = ROOT + r'\sync_route_fallback_preview.csv'
    with open(preview, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['client_id','old_route','new_route','old_note','new_note'])
        for r in to_patch:
            w.writerow([r['client_id'], r['old_route'] if r['old_route'] is not None else '',
                        r['new_route'] if r['new_route'] is not None else '',
                        r['old_note'] or '', r['new_note'] or ''])
    print(f'-> {preview}')

    if not args.apply:
        print('\n=== DRY RUN -- no DB writes. To apply: python sync_client_route_fallback.py --apply ===')
        return

    print(f'\n=== APPLYING {len(to_patch)} PATCHes ===')
    ok = 0
    fail = 0
    started = time.time()
    for i, r in enumerate(to_patch):
        success, err = patch_client(r['client_id'], r['new_route'], r['new_note'])
        if success: ok += 1
        else: fail += 1
        if (i+1) % 50 == 0 or (i+1) == len(to_patch):
            el = time.time() - started
            rate = (i+1)/max(el, 0.01)
            eta = (len(to_patch)-(i+1))/max(rate, 0.01)
            print(f'  {i+1}/{len(to_patch)} ok={ok} fail={fail}  ({rate:.1f}/s eta {eta:.0f}s)')
    print(f'\n=== DONE === ok={ok} fail={fail}')


if __name__ == '__main__':
    main()
