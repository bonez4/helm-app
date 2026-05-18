"""
find_missing_accts.py — diff the 6 day-route master-list PDFs against HELM.

Reads every PDF in `master list pdfs/`, extracts each acct (with paused flag,
name, address) tagged with which day and route it appears on, then lists every
acct that's NOT in HELM. These are the sub-accounts the office needs to
re-create manually.

Output: missing_from_helm.csv
"""
import pdfplumber, re, csv, json
from urllib.request import Request, urlopen
from collections import Counter

ROOT = r"C:\Users\theco\OneDrive\Desktop\Nantucket\helm-app"
PDF_DIR = ROOT + r"\master list pdfs"

PDFS = [
    ('Monday',    r'\master monday.pdf'),
    ('Tuesday',   r'\master tuesday.pdf'),
    ('Wednesday', r'\master wednesday.pdf'),
    ('Thursday',  r'\master thursday.pdf'),
    ('Friday',    r'\master friday.pdf'),
    ('Saturday',  r'\master saturday.pdf'),
]

SUPABASE_URL  = 'https://iiqlhqtyyqctgupalrlc.supabase.co'
SUPABASE_ANON = 'sb_publishable_JAASDdg8OERvpDTnEeLd5Q_Re48qR1I'

# Route header line: "Master Route List M-01"
ROUTE_HDR_RE = re.compile(r'^Master Route List ([A-Z])-(\d+)', re.M)
# Acct row: "200137* | BRISKMAN, EUGEN | 53 FAIR ST"
ACCT_ROW_RE  = re.compile(r'^(\d{6})(\*?)\s*\|\s*([^|]+?)\s*\|\s*(.+?)\s*$', re.M)


def parse_pdf(pdf_path, day_name):
    """Yields (acct, paused_bool, name, addr, route_letter, route_num) tuples."""
    with pdfplumber.open(pdf_path) as pdf:
        text = '\n'.join((p.extract_text() or '') for p in pdf.pages)
    # Walk page-by-page so we know which route each acct row belongs to.
    # We scan the full text and track the most recent route header.
    current_route = None  # (letter, num)
    for line in text.split('\n'):
        s = line.strip()
        if not s:
            continue
        mh = ROUTE_HDR_RE.match(s)
        if mh:
            current_route = (mh.group(1), mh.group(2))
            continue
        ma = ACCT_ROW_RE.match(s)
        if ma and current_route:
            acct   = ma.group(1)
            paused = bool(ma.group(2))
            name   = ma.group(3).strip()
            addr   = ma.group(4).strip()
            yield (acct, paused, name, addr, current_route[0], current_route[1])


def fetch_helm_accts():
    headers = {'apikey': SUPABASE_ANON, 'Authorization': f'Bearer {SUPABASE_ANON}'}
    accts = set()
    offset = 0
    while True:
        url = f'{SUPABASE_URL}/rest/v1/clients?select=client_id&order=client_id&offset={offset}&limit=1000'
        with urlopen(Request(url, headers=headers), timeout=30) as resp:
            batch = json.loads(resp.read().decode('utf-8'))
        if not batch:
            break
        for r in batch:
            accts.add(r['client_id'])
        if len(batch) < 1000:
            break
        offset += 1000
    return accts


def main():
    by_acct = {}  # acct -> {name, addr, paused, days:[(day_name, 'M-01'), ...]}
    per_pdf_counts = {}

    for day_name, fname in PDFS:
        path = PDF_DIR + fname
        n = 0
        for acct, paused, name, addr, rt_letter, rt_num in parse_pdf(path, day_name):
            n += 1
            if acct not in by_acct:
                by_acct[acct] = {
                    'acct': acct,
                    'name': name,
                    'addr': addr,
                    'paused': False,
                    'day_route_pairs': [],
                }
            entry = by_acct[acct]
            # Prefer the fullest name we see (longest non-truncated string)
            if len(name) > len(entry['name']):
                entry['name'] = name
            if len(addr) > len(entry['addr']):
                entry['addr'] = addr
            if paused:
                entry['paused'] = True
            entry['day_route_pairs'].append((day_name, f'{rt_letter}-{rt_num}'))
        per_pdf_counts[day_name] = n
        print(f'  {day_name:<10} {n:>4} acct rows')

    print(f'\nUnique accts across all 6 PDFs: {len(by_acct)}')

    print('Fetching HELM acct list…')
    helm = fetch_helm_accts()
    print(f'  {len(helm)} HELM clients')

    missing = [by_acct[a] for a in sorted(by_acct) if a not in helm]
    print(f'\nMissing from HELM: {len(missing)}')

    paused_n = sum(1 for m in missing if m['paused'])
    active_n = len(missing) - paused_n
    print(f'  Active (no asterisk on any master list): {active_n}')
    print(f'  Paused (asterisk seen):                  {paused_n}')

    # First-digit + day spread for context
    by_prefix = Counter(m['acct'][0] for m in missing)
    print('\nMissing by acct first digit:')
    for p, n in sorted(by_prefix.items()):
        print(f'  {p}xxxxx  {n}')

    days_per_acct = Counter(len(set(d for d,_ in m['day_route_pairs'])) for m in missing)
    print('\nMissing by # of distinct pickup days:')
    for n, c in sorted(days_per_acct.items()):
        print(f'  {n} day{"s" if n!=1 else ""}: {c}')

    # CSV
    out_path = ROOT + r"\missing_from_helm.csv"
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['acct', 'name', 'address', 'paused', 'days', 'routes', 'day_route_detail'])
        for m in missing:
            # Collapse to unique days and unique route labels for compact columns
            days = sorted(set(d for d,_ in m['day_route_pairs']),
                key=lambda x: ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'].index(x))
            routes = sorted(set(r for _,r in m['day_route_pairs']))
            detail = '; '.join(f'{d}={r}' for d,r in m['day_route_pairs'])
            w.writerow([
                m['acct'], m['name'], m['addr'],
                'YES' if m['paused'] else 'no',
                ', '.join(days),
                ', '.join(routes),
                detail,
            ])
    print(f'\n-> {out_path}')


if __name__ == '__main__':
    main()
