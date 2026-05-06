"""
import_rates.py — fill clients.rate1-rate5 from the Delta export PDF for the
~1,292 Reis residential accts that exist in HELM and have route records.

SCOPE (intentionally narrow for the David-only test pass):
  - Only writes rate1, rate2, rate3, rate4, rate5
  - Never touches name, address, phone, service_day, status, route, route_note, etc.
  - The rate UI is already gated to user 'david' via userIsDavid(), so other
    users see zero change after this import — same cards, same data they had.

Source PDF: delta export retry 2.pdf (Master List All Accounts format,
1,564 accts, 1,521 with route records). Inner join with HELM clients_id
yields the ~1,292 candidates.

Usage:
  python import_rates.py              # dry-run (default) — preview only
  python import_rates.py --apply      # actually apply the updates
  python import_rates.py --apply --limit 5   # apply only the first 5 (smoke test)

Outputs:
  import_rates_preview.csv  (always)  — what we plan to write
  import_rates_applied.csv  (--apply) — what actually got applied (per-acct success/failure)
"""
import pdfplumber, re, json, csv, sys, time, argparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# ─── config ────────────────────────────────────────────────────────────
ROOT = r"C:\Users\theco\OneDrive\Desktop\Nantucket\helm-app"
PDF = ROOT + r"\delta export retry 2.pdf"
SUPABASE_URL  = 'https://iiqlhqtyyqctgupalrlc.supabase.co'
SUPABASE_ANON = 'sb_publishable_JAASDdg8OERvpDTnEeLd5Q_Re48qR1I'

# ─── PDF parser (subset of master_list_extract.py — only what we need for rates) ───
SEPARATOR_RE = re.compile(r'^\s*(?:\.\s+){10,}\.?\s*$', re.M)
PAGE_HEADER_PATTERNS = [
    re.compile(r'^Master List.*PAGE\s+\d+\s*$'),
    re.compile(r'^[SAERVICLOTNB]+(\s+[SAERVICLOTNB]+)+\s*$'),
    re.compile(r'^A C C O U N T.*$'),
    re.compile(r'^=+\s*$'),
]
ACCT_RE = re.compile(
    r'^(?P<acct>\d{6})\s+(?P<status_code>[A-Za-z0-9]{2,5})\s+'
    r'(?:(?P<phone>\d{3}\s+\d{3}-\d{4})\s+)?'
    r'(?P<billing>.+?)\s+UDF Code=\s*\S*\s+Deposit=\s*[\d.]+$'
)
RATE_RE = re.compile(r'^Rate(?P<n>\d)\s+(?P<amt>[\d.]+)/Mo')
ROUTE_HEADER_RE = re.compile(r'^\d+ Route Records?\s+[A-Z]-\d+\s+\d+')


def is_page_header(line):
    return any(p.match(line) for p in PAGE_HEADER_PATTERNS)


def extract_rates_by_acct(pdf_path):
    """Walk the PDF block-by-block, return {acct: {'rate1':..,'rate5':..}}.
    Only includes blocks that have at least one Route Records line (i.e. accts
    we'd consider for the import)."""
    with pdfplumber.open(pdf_path) as pdf:
        full = '\n'.join((p.extract_text() or '') for p in pdf.pages)

    # Strip page headers
    cleaned_lines = []
    for line in full.split('\n'):
        s = line.strip()
        if not s or is_page_header(s):
            continue
        cleaned_lines.append(s)
    cleaned = '\n'.join(cleaned_lines)

    blocks = SEPARATOR_RE.split(cleaned)
    out = {}
    for blk in blocks:
        if not blk.strip():
            continue
        # Acct line
        acct = None
        rates = {f'rate{n}': None for n in range(1, 6)}
        has_route = False
        for line in blk.split('\n'):
            line = line.strip()
            if not line:
                continue
            if acct is None:
                m = ACCT_RE.match(line)
                if m:
                    acct = m.group('acct')
                continue
            m = RATE_RE.match(line)
            if m:
                n = int(m.group('n'))
                rates[f'rate{n}'] = float(m.group('amt'))
                continue
            if ROUTE_HEADER_RE.match(line):
                has_route = True
        if acct and has_route:
            # Skip 1xxxxx system accts
            if acct.startswith('1'):
                continue
            out[acct] = rates
    return out


# ─── Supabase ──────────────────────────────────────────────────────────
def fetch_helm_acct_set():
    """Return set of HELM client_ids."""
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


def patch_one(client_id, payload, max_retries=3):
    url = f'{SUPABASE_URL}/rest/v1/clients?client_id=eq.{client_id}'
    headers = {
        'apikey': SUPABASE_ANON,
        'Authorization': f'Bearer {SUPABASE_ANON}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal',
    }
    data = json.dumps(payload).encode()
    last_err = None
    for attempt in range(max_retries):
        try:
            req = Request(url, data=data, headers=headers, method='PATCH')
            with urlopen(req, timeout=15) as resp:
                resp.read()  # drain
            return True, None
        except HTTPError as e:
            err = f'HTTP {e.code}: {e.read().decode("utf-8", errors="replace")[:200]}'
            last_err = err
            # don't retry 4xx
            if 400 <= e.code < 500:
                return False, err
        except URLError as e:
            last_err = f'URLError: {e.reason}'
        time.sleep(0.5 * (attempt + 1))
    return False, last_err


# ─── main ──────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='Actually write to Supabase. Default is dry-run.')
    ap.add_argument('--limit', type=int, default=None, help='Limit to first N accts (smoke test).')
    args = ap.parse_args()

    print(f'Parsing PDF: {PDF}')
    rates_by_acct = extract_rates_by_acct(PDF)
    print(f'  {len(rates_by_acct)} accts with route records and parsed rates')

    print('Fetching HELM acct list...')
    helm_accts = fetch_helm_acct_set()
    print(f'  {len(helm_accts)} HELM clients')

    # Inner join: only accts in BOTH
    candidates = sorted(a for a in rates_by_acct if a in helm_accts)
    print(f'  {len(candidates)} candidates (intersection)')

    if args.limit:
        candidates = candidates[:args.limit]
        print(f'  --limit applied: trimmed to {len(candidates)} accts')

    # Build payload list
    payloads = []
    for acct in candidates:
        rates = rates_by_acct[acct]
        payload = {f'rate{n}': rates[f'rate{n}'] for n in range(1, 6)}
        payloads.append((acct, payload))

    # Stats: how many rates of each type are populated
    stats = {f'rate{n}': 0 for n in range(1, 6)}
    for _, p in payloads:
        for k, v in p.items():
            if v is not None:
                stats[k] += 1
    print(f'\nRate population in payloads:')
    for k, n in stats.items():
        pct = 100 * n / max(1, len(payloads))
        print(f'  {k}: {n}/{len(payloads)} ({pct:.1f}%)')

    # Always write the preview CSV
    with open('import_rates_preview.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['acct', 'rate1', 'rate2', 'rate3', 'rate4', 'rate5'])
        for acct, p in payloads:
            w.writerow([acct] + [p[f'rate{n}'] if p[f'rate{n}'] is not None else '' for n in range(1, 6)])
    print(f'\nPreview CSV written: import_rates_preview.csv')

    if not args.apply:
        print('\n=== DRY RUN — no DB writes ===')
        print('To apply: python import_rates.py --apply')
        return

    # Apply
    print(f'\n=== APPLYING {len(payloads)} updates ===')
    applied = 0
    failed = 0
    failures = []
    started = time.time()
    with open('import_rates_applied.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['acct', 'status', 'error', 'rate1', 'rate2', 'rate3', 'rate4', 'rate5'])
        for i, (acct, payload) in enumerate(payloads):
            ok, err = patch_one(acct, payload)
            if ok:
                applied += 1
                status = 'ok'
            else:
                failed += 1
                status = 'FAIL'
                failures.append((acct, err))
            w.writerow([acct, status, err or ''] + [payload[f'rate{n}'] if payload[f'rate{n}'] is not None else '' for n in range(1, 6)])
            if (i + 1) % 50 == 0 or (i + 1) == len(payloads):
                elapsed = time.time() - started
                rate = (i + 1) / elapsed
                eta = (len(payloads) - (i + 1)) / max(rate, 0.01)
                print(f'  {i+1}/{len(payloads)} done  ok={applied} fail={failed}  ({rate:.1f}/s  eta {eta:.0f}s)')

    print(f'\n=== DONE ===  applied={applied}  failed={failed}')
    if failures:
        print('\nFirst 10 failures:')
        for acct, err in failures[:10]:
            print(f'  {acct}: {err}')


if __name__ == '__main__':
    main()
