"""
santos_sep11_analyze.py — data-quality pass over the parsed Sep-11 East End
"All Accounts" export (santos_sep11.csv) + diff against the latest HELM
clients export (HELM_Clients_<date>.xls, HTML table).

Usage: python santos_sep11_analyze.py [path/to/HELM_Clients_YYYYMMDD.xls]

Outputs to Downloads (PII — never commit):
  santos_sep11_issues.csv     one row per (acct, issue) finding
  santos_sep11_dupes.csv      groups of accounts sharing name+address
  santos_sep11_vs_helm.csv    per-acct diff vs HELM export
Prints a summary.
"""
import csv, re, sys, html
from collections import defaultdict, Counter

CSV  = r"C:/Users/theco/Downloads/santos_sep11.csv"
HELM = sys.argv[1] if len(sys.argv) > 1 else r"C:/Users/theco/Downloads/HELM_Clients_20260723 (1).xls"
OUT  = r"C:/Users/theco/Downloads/"

ABBR = [(r'\bSTREET\b', 'ST'), (r'\bROAD\b', 'RD'), (r'\bAVENUE\b', 'AVE'), (r'\bLANE\b', 'LN'),
        (r'\bDRIVE\b', 'DR'), (r'\bCIRCLE\b', 'CIR'), (r'\bCOURT\b', 'CT'), (r'\bNORTH\b', 'N'),
        (r'\bSOUTH\b', 'S'), (r'\bEAST\b', 'E'), (r'\bWEST\b', 'W'), (r'\bPLACE\b', 'PL')]

def norm(s):
    s = (s or '').upper()
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    for pat, rep in ABBR:
        s = re.sub(pat, rep, s)
    return re.sub(r'\s+', ' ', s).strip()

rows = list(csv.DictReader(open(CSV, encoding='utf-8')))
cust = [r for r in rows if not r['acct'].startswith('1')]
print(f"PDF accounts: {len(rows)} (non-rolloff {len(cust)})")
print("types:", Counter(r['type'] for r in cust))
print("roles:", Counter(r['role'] for r in cust))
print("klass:", Counter(r['klass'] for r in cust).most_common(12))
print("star:", Counter(r['star'] for r in cust), " flag:", Counter(r['flag'] for r in cust))
print("days_raw empty:", sum(1 for r in cust if not r['days_raw']),
      " by type:", Counter(r['type'] for r in cust if not r['days_raw']))

issues = []
def issue(r, kind, detail=''):
    issues.append({'acct': r['acct'], 'klass': r['klass'], 'type': r['type'], 'role': r['role'],
                   'name': r['name'], 'address': r['address'], 'days': r['days'], 'star': r['star'],
                   'start_date': r['start_date'], 'ttl_rate': r['ttl_rate'], 'issue': kind, 'detail': detail})

JUNK_NAME = re.compile(r"DON'?T USE|DO NOT USE|\bMASTER\b|\bHUB\b|\bTEST\b|PLACEHOLDER|UNKNOWN|^\W*$", re.I)
JUNK_ADDR = re.compile(r"^(MASTER|MASTER ACCOUNT|ROLLOFF|CREDIT ON ACT|POST OFFICE|U\.?S\.? POST OFFICE|N/?A|NONE|TBD|\?+)!?$", re.I)

for r in cust:
    if JUNK_NAME.search(r['name']) and r['role'] != 'master':
        issue(r, 'junk_name', r['name'])
    if not r['address'].strip():
        issue(r, 'no_address')
    elif JUNK_ADDR.match(r['address'].strip()) or not re.search(r'[A-Z]{3}', r['address'].upper()):
        issue(r, 'placeholder_address', r['address'])
    elif not re.match(r'^\d', r['address'].strip()):
        issue(r, 'address_no_number', r['address'])
    if not r['days_raw'] and r['type'] == 'residential':
        issue(r, 'resi_no_days')
    if r['type'] == 'residential' and r['days_raw'] and len(r['days_raw']) > 3:
        issue(r, 'resi_many_days', r['days_raw'])
    if not r['rate1']:
        issue(r, 'no_rate1')
    elif float(r['rate1']) == 0:
        issue(r, 'rate1_zero')
    if r['type'] == 'unknown':
        issue(r, 'unknown_class', r['klass'])
    if not r['name'].strip():
        issue(r, 'no_name')
    try:
        s = sum(float(r[f'rate{n}']) for n in range(1, 6) if r[f'rate{n}'])
        if r['ttl_rate'] and abs(s - float(r['ttl_rate'])) > 0.011:
            issue(r, 'ttl_mismatch', f"sum={s:.2f} ttl={r['ttl_rate']}")
    except ValueError:
        pass

# duplicates: same normalized name+address; and same address with >1 residential account
groups = defaultdict(list)
for r in cust:
    if r['role'] == 'sub' or not r['address'].strip():
        continue
    groups[(norm(r['name']), norm(r['address']))].append(r)
dupes = [g for g in groups.values() if len(g) > 1]
addr_groups = defaultdict(list)
for r in cust:
    if r['role'] != 'sub' and r['address'].strip() and r['type'] == 'residential':
        addr_groups[norm(r['address'])].append(r)
addr_dupes = [g for g in addr_groups.values() if len(g) > 1]

with open(OUT + 'santos_sep11_dupes.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['group', 'kind', 'acct', 'klass', 'type', 'name', 'address', 'days', 'star', 'start_date', 'ttl_rate', 'billing_name'])
    gi = 0
    seen = set()
    for kind, gl in (('same_name_addr', dupes), ('same_addr_resi', addr_dupes)):
        for g in gl:
            key = tuple(sorted(r['acct'] for r in g))
            if key in seen:
                continue
            seen.add(key); gi += 1
            for r in g:
                w.writerow([gi, kind, r['acct'], r['klass'], r['type'], r['name'], r['address'], r['days'],
                            r['star'], r['start_date'], r['ttl_rate'], r['billing_name']])
    print(f"dupe groups: same name+addr={len(dupes)}  same resi addr={len(addr_dupes)}  distinct groups written={gi}")

for g in dupes:
    for r in g:
        issue(r, 'dup_name_addr', ' / '.join(x['acct'] for x in g if x is not r))

with open(OUT + 'santos_sep11_issues.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(issues[0].keys()))
    w.writeheader(); w.writerows(sorted(issues, key=lambda i: (i['issue'], i['acct'])))
print("issues:", Counter(i['issue'] for i in issues))

# ---- HELM export diff ----
raw = open(HELM, encoding='utf-8').read()
hdr = [html.unescape(re.sub(r'<[^>]+>', '', h)).strip() for h in re.findall(r'<th[^>]*>(.*?)</th>', raw, re.S)]
helm = []
for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', raw, re.S):
    tds = [html.unescape(re.sub(r'<[^>]+>', '', t)).strip() for t in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)]
    if len(tds) == len(hdr):
        helm.append(dict(zip(hdr, tds)))
hs = {h['Account #']: h for h in helm if h['Account #'].startswith('3')}
print(f"\nHELM export {HELM.split('/')[-1]}: {len(helm)} rows, Santos={len(hs)}; columns={hdr}")
pdf_ids = {r['acct'] for r in cust}
only_pdf = sorted(pdf_ids - set(hs)); only_helm = sorted(set(hs) - pdf_ids)
print(f"in PDF not in HELM export: {len(only_pdf)}   in HELM export not in PDF: {len(only_helm)}")
DAYMAP = {'Monday': 'M', 'Tuesday': 'T', 'Wednesday': 'W', 'Thursday': 'R', 'Friday': 'F', 'Saturday': 'S', 'Sunday': 'N'}
def hdays(s):
    return ''.join(DAYMAP.get(d.strip(), '?') for d in s.split(',') if d.strip())
diff_rows = []; dc = Counter()
for r in cust:
    h = hs.get(r['acct'])
    if not h:
        diff_rows.append({'acct': r['acct'], 'diff': 'pdf_only', 'pdf': f"{r['name']} | {r['address']} | {r['days_raw']}", 'helm': ''}); dc['pdf_only'] += 1
        continue
    if norm(r['name']) != norm(h['Name']):
        diff_rows.append({'acct': r['acct'], 'diff': 'name', 'pdf': r['name'], 'helm': h['Name']}); dc['name'] += 1
    if norm(r['address']) != norm(h['Address']):
        diff_rows.append({'acct': r['acct'], 'diff': 'address', 'pdf': r['address'], 'helm': h['Address']}); dc['address'] += 1
    pd_, hd = r['days_raw'], hdays(h.get('Pickup Days', ''))
    if pd_ != hd:
        diff_rows.append({'acct': r['acct'], 'diff': 'days', 'pdf': pd_, 'helm': hd}); dc['days'] += 1
for a in only_helm:
    h = hs[a]
    diff_rows.append({'acct': a, 'diff': 'helm_only', 'pdf': '',
                      'helm': f"{h['Name']} | {h['Address']} | {hdays(h.get('Pickup Days', ''))} | R{h.get('Route', '')}"}); dc['helm_only'] += 1
with open(OUT + 'santos_sep11_vs_helm.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['acct', 'diff', 'pdf', 'helm']); w.writeheader(); w.writerows(diff_rows)
print("diff vs HELM:", dict(dc))
