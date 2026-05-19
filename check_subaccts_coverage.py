"""Quick check: how many of the 176 sub-accts from missing_from_helm.csv got
route data from today's xlsx upload? Also verify route_assignments is populated."""
import csv, json
from urllib.request import Request, urlopen

ROOT = r"C:\Users\theco\OneDrive\Desktop\Nantucket\helm-app"
SUPABASE_URL  = 'https://iiqlhqtyyqctgupalrlc.supabase.co'
SUPABASE_ANON = 'sb_publishable_JAASDdg8OERvpDTnEeLd5Q_Re48qR1I'

# Sub-account list
with open(ROOT + r'\missing_from_helm.csv', encoding='utf-8') as f:
    subaccts = set(r['acct'] for r in csv.DictReader(f))
print(f'Sub-accts in missing_from_helm.csv: {len(subaccts)}')

# Fetch route_assignments
headers = {'apikey': SUPABASE_ANON, 'Authorization': f'Bearer {SUPABASE_ANON}'}
rows = []
offset = 0
while True:
    url = f'{SUPABASE_URL}/rest/v1/route_assignments?select=client_id,day_of_week,route,route_note,source&offset={offset}&limit=1000'
    with urlopen(Request(url, headers=headers), timeout=30) as resp:
        batch = json.loads(resp.read().decode('utf-8'))
    if not batch: break
    rows.extend(batch)
    if len(batch) < 1000: break
    offset += 1000
print(f'Total route_assignments rows in HELM: {len(rows)}')

# Sub-acct coverage
sub_rows = [r for r in rows if r['client_id'] in subaccts]
sub_accts_with_routes = set(r['client_id'] for r in sub_rows)
sub_rows_with_notes = [r for r in sub_rows if (r.get('route_note') or '').strip()]
print(f'\n=== Sub-account coverage ===')
print(f'  Sub-accts with at least one route row:    {len(sub_accts_with_routes)} / {len(subaccts)}')
print(f'  Total route rows for those sub-accts:     {len(sub_rows)}')
print(f'  Route rows that have a populated note:    {len(sub_rows_with_notes)}')

# Source breakdown
from collections import Counter
sub_sources = Counter(r.get('source') for r in sub_rows)
print(f'\n  Source breakdown for sub-acct rows:')
for s, n in sub_sources.most_common():
    print(f'    {s or "(null)":<25} {n}')

# Sample of sub-accts that did NOT get any route row
no_route = subaccts - sub_accts_with_routes
print(f'\n  Sub-accts with NO route row at all: {len(no_route)}')
if no_route:
    sample = sorted(no_route)[:10]
    print(f'  First 10: {sample}')
