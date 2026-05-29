"""
import_active_accounts.py — reconcile HELM clients against the authoritative
"ALL ACCOUNTS" PDF exports (REIS = clients 2xxxxx, SANTOS/East End = 3xxxxx).

The PDF is the source of truth for who is ACTIVE today. For each non-rolloff
account it carries: classification (R*=residential, C*=commercial, XC=sub of a
commercial master, XX=house acct/skip), service days, and Rate1-5.

Apply (per the agreed Santos test plan):
  MATCHED (PDF & HELM): PATCH status='Active', account_type, account_role,
      master_account_id, rate1..5 (overwrite all five), service_day (if days).
  PDF-only (not in HELM): INSERT new client (acct/name/address/type/role/master/
      rates/days, status='Active').
  HELM-only of same company (not in PDF, not 1xxxxx): PATCH status='Inactive'.
Name/address are only written on CREATES; matched rows keep their HELM name/addr.
Rolloff accounts (acct starts with '1') are ignored entirely.

Requires these columns on `clients` (run once in Supabase SQL editor):
  account_type TEXT, account_role TEXT, master_account_id TEXT

Usage:
  python import_active_accounts.py --company santos               # dry-run report
  python import_active_accounts.py --company santos --apply --limit 5   # smoke: 5 matched updates only
  python import_active_accounts.py --company santos --apply        # full apply (update + create + deactivate)
"""
import pdfplumber, re, json, csv, argparse, time
from collections import defaultdict, Counter
from urllib.request import Request, urlopen
from urllib.error import HTTPError

PDFS = {
    'santos': r"C:/Users/theco/Downloads/ALL ACCOUNTS MAY 29 SANTOS.pdf",
    'reis':   r"C:/Users/theco/Downloads/ALL ACCOUNTS MAY 29 REIS.pdf",
}
PREFIX = {'santos': '3', 'reis': '2'}
SUPABASE_URL  = 'https://iiqlhqtyyqctgupalrlc.supabase.co'
SUPABASE_ANON = 'sb_publishable_JAASDdg8OERvpDTnEeLd5Q_Re48qR1I'

DAYMAP = {'M':'Monday','T':'Tuesday','W':'Wednesday','R':'Thursday','F':'Friday','S':'Saturday'}
DAY_ORDER = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
ACCT_RE = re.compile(r'^\d{6}\*?$')
DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')
DAYS_X_MIN, DAYS_X_MAX = 395, 445   # day-letter column (flag 'S' sits at ~451, excluded)


def parse_days(tok):
    if not tok or not re.fullmatch(r'[MTWRFS]+', tok):
        return []
    present = {DAYMAP[c] for c in tok}
    return [d for d in DAY_ORDER if d in present]


def parse_pdf(path):
    accounts, cur = [], None
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            lines = defaultdict(list)
            for w in words:
                lines[round(w['top'])].append(w)
            for top in sorted(lines):
                ws = sorted(lines[top], key=lambda w: w['x0'])
                first = ws[0]['text']
                is_sub = (first == '<SubAccount>')
                acct_w = None
                if is_sub and len(ws) >= 2 and ACCT_RE.match(ws[1]['text']):
                    acct_w = ws[1]
                elif ACCT_RE.match(first):
                    acct_w = ws[0]
                if acct_w is not None:
                    idx = ws.index(acct_w)
                    klass = ws[idx + 1]['text'] if idx + 1 < len(ws) else ''
                    days_tok = ''
                    date_x = slash_x = None
                    for w in ws:
                        if DAYS_X_MIN <= w['x0'] <= DAYS_X_MAX and re.fullmatch(r'[MTWRFS]+', w['text']):
                            days_tok = days_tok or w['text']
                        if DATE_RE.fullmatch(w['text']) and date_x is None:
                            date_x = w['x0']
                        if w['text'] == '/' and slash_x is None:
                            slash_x = w['x0']
                    name_min = 110 if is_sub else 50
                    addr_min = 250 if is_sub else 211
                    addr_max = slash_x if slash_x is not None else (date_x if date_x is not None else 359)
                    name_words = [w['text'] for w in ws if name_min <= w['x0'] < addr_min]
                    addr_words = [w['text'] for w in ws if addr_min <= w['x0'] < addr_max]
                    cur = {
                        'acct': acct_w['text'].rstrip('*'),
                        'klass': klass, 'is_sub': is_sub,
                        'name': ' '.join(name_words).rstrip(', ').strip(),
                        'addr': ' '.join(addr_words).strip(),
                        'days': parse_days(days_tok), 'days_raw': days_tok,
                        'rates': {f'rate{n}': None for n in range(1, 6)},
                    }
                    accounts.append(cur)
                    continue
                if cur is not None and first.startswith('Rate') and len(ws) >= 2:
                    m = re.match(r'^Rate(\d)$', first)
                    am = re.match(r'^([\d.]+)/Mo', ws[1]['text'])
                    if m and am and 1 <= int(m.group(1)) <= 5:
                        cur['rates'][f'rate{int(m.group(1))}'] = float(am.group(1))
    return accounts


def classify(accounts):
    last_nonsub = None
    for a in accounts:
        k = a['klass']
        if a['is_sub'] or k == 'XC':
            a['role'], a['master'], a['type'] = 'sub', last_nonsub, 'commercial'
        elif k == 'XX':
            a['role'], a['master'], a['type'] = 'house', None, 'house'
        else:
            a['role'], a['master'] = 'standalone', None
            a['type'] = 'residential' if k.startswith('R') else 'commercial' if k.startswith('C') else 'unknown'
            last_nonsub = a['acct']
    masters = {a['master'] for a in accounts if a.get('master')}
    for a in accounts:
        if a['acct'] in masters and a['role'] == 'standalone':
            a['role'] = 'master'
    return accounts


def fetch_helm():
    headers = {'apikey': SUPABASE_ANON, 'Authorization': f'Bearer {SUPABASE_ANON}'}
    rows, offset = [], 0
    while True:
        url = (f'{SUPABASE_URL}/rest/v1/clients?select=client_id,client_name,status'
               f'&order=client_id&offset={offset}&limit=1000')
        with urlopen(Request(url, headers=headers), timeout=30) as resp:
            batch = json.loads(resp.read().decode('utf-8'))
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return rows


def http(method, url, payload=None):
    headers = {'apikey': SUPABASE_ANON, 'Authorization': f'Bearer {SUPABASE_ANON}',
               'Content-Type': 'application/json', 'Prefer': 'return=minimal'}
    data = json.dumps(payload).encode() if payload is not None else None
    try:
        with urlopen(Request(url, data=data, headers=headers, method=method), timeout=20) as resp:
            resp.read()
        return True, None
    except HTTPError as e:
        return False, f'HTTP {e.code}: {e.read().decode("utf-8", "replace")[:200]}'
    except Exception as e:
        return False, str(e)


def update_payload(a):
    p = {'status': 'Active', 'account_type': a['type'], 'account_role': a['role'],
         'master_account_id': a['master'] if a['role'] == 'sub' else None}
    for n in range(1, 6):
        p[f'rate{n}'] = a['rates'][f'rate{n}']      # overwrite all five (None clears)
    if a['days']:
        p['service_day'] = ','.join(a['days'])
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--company', choices=['santos', 'reis'], required=True)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--limit', type=int, default=None, help='smoke test: only first N matched updates')
    args = ap.parse_args()

    accts = classify(parse_pdf(PDFS[args.company]))
    cust = [a for a in accts if a['type'] != 'house' and not a['acct'].startswith('1')]
    by_acct = {a['acct']: a for a in cust}
    pdf_ids = set(by_acct)

    helm = fetch_helm()
    helm_ids = {h['client_id'] for h in helm}
    helm_co = {h['client_id'] for h in helm
               if h['client_id'].startswith(PREFIX[args.company]) and not h['client_id'].startswith('1')}

    matched    = sorted(pdf_ids & helm_ids)
    pdf_only   = sorted(pdf_ids - helm_ids)
    helm_extra = sorted(a for a in helm_co if a not in pdf_ids)

    print(f"=== {args.company.upper()} ===  matched={len(matched)}  create={len(pdf_only)}  deactivate={len(helm_extra)}")

    if not args.apply:
        type_c = Counter(a['type'] for a in cust); role_c = Counter(a['role'] for a in cust)
        print(f"parsed={len(cust)}  types={dict(type_c)}  roles={dict(role_c)}")
        with open(f'{args.company}_creates_preview.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['acct', 'type', 'role', 'master', 'name', 'address', 'days', 'rate1', 'rate2', 'rate3', 'rate4', 'rate5'])
            for acct in pdf_only:
                a = by_acct[acct]
                w.writerow([acct, a['type'], a['role'], a['master'] or '', a['name'], a['addr'], ','.join(a['days'])]
                           + [a['rates'][f'rate{n}'] if a['rates'][f'rate{n}'] is not None else '' for n in range(1, 6)])
        print(f"creates preview -> {args.company}_creates_preview.csv ({len(pdf_only)} rows)")
        print("DRY RUN — no writes.")
        return

    results = []  # (acct, phase, ok, err)

    def do(phase, acct, method, url, payload):
        ok, err = http(method, url, payload)
        results.append((acct, phase, ok, err))
        return ok

    # 1) UPDATE matched
    upd = matched[:args.limit] if args.limit else matched
    print(f"\n[1/{'1' if args.limit else '3'}] updating {len(upd)} matched ...")
    for i, acct in enumerate(upd, 1):
        do('update', acct, 'PATCH', f'{SUPABASE_URL}/rest/v1/clients?client_id=eq.{acct}', update_payload(by_acct[acct]))
        if i % 100 == 0 or i == len(upd):
            print(f"   {i}/{len(upd)}")

    if args.limit:
        ok = sum(1 for r in results if r[2]); fail = len(results) - ok
        print(f"\nSMOKE DONE: ok={ok} fail={fail}")
        print("Accounts updated (verify these cards in HELM):")
        for acct in upd:
            a = by_acct[acct]
            print(f"  {acct}  {a['type']}/{a['role']}  days={','.join(a['days']) or '-'}  R1-5={[a['rates'][f'rate{n}'] for n in range(1,6)]}")
        for acct, ph, k, err in results:
            if not k:
                print(f"  FAIL {acct} ({ph}): {err}")
        return

    # 2) CREATE pdf_only
    print(f"\n[2/3] creating {len(pdf_only)} new clients ...")
    for i, acct in enumerate(pdf_only, 1):
        a = by_acct[acct]
        p = update_payload(a)
        addr = a['addr'] or None
        if a['role'] == 'master' or (addr and addr.upper().replace('!', '').strip() in ('MASTER', 'MASTER ACCOUNT', 'ROLLOFF')):
            addr = None   # masters / placeholders have no real service address
        p.update({'client_id': acct, 'client_name': a['name'] or None, 'address': addr})
        do('create', acct, 'POST', f'{SUPABASE_URL}/rest/v1/clients', p)
        if i % 25 == 0 or i == len(pdf_only):
            print(f"   {i}/{len(pdf_only)}")

    # 3) DEACTIVATE helm_extra
    print(f"\n[3/3] deactivating {len(helm_extra)} stale accounts ...")
    for i, acct in enumerate(helm_extra, 1):
        do('deactivate', acct, 'PATCH', f'{SUPABASE_URL}/rest/v1/clients?client_id=eq.{acct}', {'status': 'Inactive'})
        if i % 200 == 0 or i == len(helm_extra):
            print(f"   {i}/{len(helm_extra)}")

    ok = sum(1 for r in results if r[2]); fail = len(results) - ok
    by_phase = Counter((r[1], 'ok' if r[2] else 'fail') for r in results)
    print(f"\n=== DONE ===  ok={ok}  fail={fail}  {dict(by_phase)}")
    with open(f'{args.company}_apply_results.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['acct', 'phase', 'ok', 'error'])
        for r in results:
            w.writerow([r[0], r[1], 'ok' if r[2] else 'FAIL', r[3] or ''])
    fails = [r for r in results if not r[2]]
    if fails:
        print(f"\nFirst 10 failures:")
        for r in fails[:10]:
            print(f"  {r[1]} {r[0]}: {r[3]}")


if __name__ == '__main__':
    main()
