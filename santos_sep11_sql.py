"""
santos_sep11_sql.py — turn the Sep-11 NetWork PDF (santos_sep11.csv) + the
Sep-11 HELM export (HELM_Clients_20260911.xls) into corrective SQL for the
Supabase SQL editor. Every section is idempotent and independently runnable.

  Downloads/santos_sep11_cleanup.sql
    1. INSERT PDF-only accounts (skips known placeholders)
    2. Address fixes            (PDF wins; HELM's Delta import dropped unit suffixes)
    3. Name fixes               (PDF wins; NetWork is the billing system)
    4. Pickup-day fixes         (PDF wins where the PDF has days; HELM kept where PDF is blank)
    5. Classification + rates   (account_type / role / master / rate1-5 from the PDF, all matched)
  Downloads/santos_sep11_status.sql   (separate — depends on the '*' = dormant reading)
    6. Starred + Active   -> Inactive
    7. Unstarred + Inactive -> Active   (Paused left alone)

Usage: python santos_sep11_sql.py [HELM_Clients_YYYYMMDD.xls]
"""
import csv, re, sys, html
from collections import Counter

CSV  = r"C:/Users/theco/Downloads/santos_sep11.csv"
HELM = sys.argv[1] if len(sys.argv) > 1 else r"C:/Users/theco/Downloads/HELM_Clients_20260911.xls"
OUT  = r"C:/Users/theco/Downloads/santos_sep11_cleanup.sql"
OUT_STATUS = r"C:/Users/theco/Downloads/santos_sep11_status.sql"

SKIP_INSERT = {'305440', '309357'}   # DONT USE ACT / THE HUB master placeholder (excluded from the route import too)
DAYMAP = {'Monday': 'M', 'Tuesday': 'T', 'Wednesday': 'W', 'Thursday': 'R', 'Friday': 'F', 'Saturday': 'S', 'Sunday': 'N'}
PLACEHOLDER_ADDR = re.compile(r"^(MASTER|MASTER ACCOUNT!*|ROLLOFF|CREDIT ON ACT|POST OFFICE|DONT USE ACT|DON'T NEED THIS ACCCT)$", re.I)


def q(s):
    return 'NULL' if s is None or s == '' else "'" + str(s).replace("'", "''") + "'"


def num(s):
    return 'NULL' if s in (None, '') else str(float(s))


ABBR = [(r'\bSTREET\b', 'ST'), (r'\bROAD\b', 'RD'), (r'\bAVENUE\b', 'AVE'), (r'\bLANE\b', 'LN'),
        (r'\bDRIVE\b', 'DR'), (r'\bCIRCLE\b', 'CIR'), (r'\bCOURT\b', 'CT'), (r'\bNORTH\b', 'N'),
        (r'\bSOUTH\b', 'S'), (r'\bEAST\b', 'E'), (r'\bWEST\b', 'W'), (r'\bPLACE\b', 'PL'), (r'\bWY\b', 'WAY')]


def norm(s):
    """Compare-key: abbreviation-only differences (LANE/LN) are not worth a write."""
    s = re.sub(r'[^A-Z0-9 ]', ' ', (s or '').upper())
    for pat, rep in ABBR:
        s = re.sub(pat, rep, s)
    return re.sub(r'\s+', ' ', s).strip()


def hdays(s):
    return ''.join(DAYMAP.get(d.strip(), '?') for d in s.split(',') if d.strip())


pdf = [r for r in csv.DictReader(open(CSV, encoding='utf-8')) if not r['acct'].startswith('1')]
by_acct = {r['acct']: r for r in pdf}

raw = open(HELM, encoding='utf-8').read()
hdr = [html.unescape(re.sub(r'<[^>]+>', '', h)).strip() for h in re.findall(r'<th[^>]*>(.*?)</th>', raw, re.S)]
helm = {}
for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', raw, re.S):
    tds = [html.unescape(re.sub(r'<[^>]+>', '', t)).strip() for t in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)]
    if len(tds) == len(hdr) and tds[0].startswith('3'):
        helm[tds[0]] = dict(zip(hdr, tds))

matched = [r for r in pdf if r['acct'] in helm]
pdf_only = [r for r in pdf if r['acct'] not in helm and r['acct'] not in SKIP_INSERT]
stats = Counter()


def values_update(col, pairs, cast=''):
    """UPDATE clients SET col = v.val FROM (VALUES ...) v(id,val) WHERE ..."""
    rows = ',\n'.join(f"  ({q(a)}, {v})" for a, v in pairs)
    return (f"UPDATE clients c SET {col} = v.val{cast}\nFROM (VALUES\n{rows}\n) AS v(id, val)\n"
            f"WHERE c.client_id = v.id AND c.{col} IS DISTINCT FROM v.val{cast};\n")


out = []
out.append(f"-- Santos cleanup generated from AllSantosAcctsSep11.pdf + {HELM.split('/')[-1]}\n"
           f"-- PDF accounts={len(pdf)}  matched in HELM={len(matched)}  new={len(pdf_only)}\n"
           "-- Every section is idempotent. Run all at once or one section at a time.\n")

# ---- 1. INSERT new accounts ----
ins = []
for r in pdf_only:
    addr = r['address']
    if PLACEHOLDER_ADDR.match(addr) or r['role'] == 'master':
        addr = ''
    ins.append(f"({q(r['acct'])}, {q(r['name'])}, {q(addr)}, {q(r['days'])}, 'Active', "
               f"{q(r['type']) if r['type'] != 'house' else 'NULL'}, {q(r['role']) if r['type'] != 'house' else 'NULL'}, "
               f"{q(r['master']) if r['role'] == 'sub' else 'NULL'}, "
               + ', '.join(num(r[f'rate{n}']) for n in range(1, 6)) + ")")
stats['insert'] = len(ins)
out.append(f"\n-- ===== 1. INSERT {len(ins)} accounts in NetWork but not in HELM (skipped placeholders {sorted(SKIP_INSERT)}) =====\n"
           "INSERT INTO clients (client_id, client_name, address, service_day, status, account_type, account_role, master_account_id, rate1, rate2, rate3, rate4, rate5) VALUES\n"
           + ',\n'.join(ins) + "\nON CONFLICT (client_id) DO NOTHING;\n")

# ---- 2. Address fixes ----
addr_pairs = []
for r in matched:
    h = helm[r['acct']]
    if not r['address'] or PLACEHOLDER_ADDR.match(r['address']) or r['role'] == 'master':
        continue
    if norm(r['address']) != norm(h['Address']):
        addr_pairs.append((r['acct'], q(r['address']) + f"  /* was {q(h['Address'])} */"))
stats['address'] = len(addr_pairs)
out.append(f"\n-- ===== 2. Address fixes ({len(addr_pairs)}) — NetWork address wins (HELM's Delta import dropped unit letters like 9A -> 9) =====\n"
           + values_update('address', addr_pairs))

# ---- 3. Name fixes ----
name_pairs = []
for r in matched:
    h = helm[r['acct']]
    if r['name'] and norm(r['name']) != norm(h['Name']):
        name_pairs.append((r['acct'], q(r['name']) + f"  /* was {q(h['Name'])} */"))
stats['name'] = len(name_pairs)
out.append(f"\n-- ===== 3. Name fixes ({len(name_pairs)}) — NetWork billing name wins =====\n"
           + values_update('client_name', name_pairs))

# ---- 4. Pickup days ----
day_pairs = []
kept = 0
for r in matched:
    h = helm[r['acct']]
    if not r['days_raw']:
        if h['Pickup Days']:
            kept += 1
        continue
    if r['days_raw'] != hdays(h['Pickup Days']):
        day_pairs.append((r['acct'], q(r['days']) + f"  /* was {q(h['Pickup Days'] or '')} */"))
stats['days'] = len(day_pairs); stats['days_kept_helm'] = kept
out.append(f"\n-- ===== 4. Pickup-day fixes ({len(day_pairs)}) — NetWork days win where NetWork has days.\n"
           f"--   {kept} accounts have days in HELM but none in NetWork: HELM value KEPT (not touched).\n"
           "--   Note: a day added here has no route_assignments row yet, so it falls back to clients.route on reports. =====\n"
           + values_update('service_day', day_pairs))

# ---- 5. Classification + rates ----
cls = []
for r in matched:
    if r['type'] == 'house':
        continue
    cls.append(f"  ({q(r['acct'])}, {q(r['type'])}, {q(r['role'])}, {q(r['master']) if r['role'] == 'sub' else 'NULL'}, "
               + ', '.join(num(r[f'rate{n}']) for n in range(1, 6)) + ")")
stats['classify'] = len(cls)
out.append(f"\n-- ===== 5. Classification + rate schedule sync ({len(cls)} matched accounts) — same fields import_active_accounts.py set on 5/29,\n"
           "--   refreshed from the Sep-11 export (covers the 48 route-import + 63 new accounts that never got a type). Rates overwrite, NULL clears. =====\n"
           "UPDATE clients c SET account_type = v.t, account_role = v.r, master_account_id = v.m,\n"
           "  rate1 = v.r1, rate2 = v.r2, rate3 = v.r3, rate4 = v.r4, rate5 = v.r5\n"
           "FROM (VALUES\n" + ',\n'.join(cls) + "\n) AS v(id, t, r, m, r1, r2, r3, r4, r5)\n"
           "WHERE c.client_id = v.id AND (c.account_type IS DISTINCT FROM v.t OR c.account_role IS DISTINCT FROM v.r\n"
           "  OR c.master_account_id IS DISTINCT FROM v.m OR c.rate1 IS DISTINCT FROM v.r1 OR c.rate2 IS DISTINCT FROM v.r2\n"
           "  OR c.rate3 IS DISTINCT FROM v.r3 OR c.rate4 IS DISTINCT FROM v.r4 OR c.rate5 IS DISTINCT FROM v.r5);\n")

# ---- manual-review notes ----
out.append("\n-- ===== Manual review (no SQL generated) =====\n"
           "-- 310337 WISINSKI, GUY — address 'DON'T NEED THIS ACCCT', no days: likely junk, still Active-eligible in NetWork.\n"
           "-- 302396 DECOSTA / 310205 WIGGIN — address 'ROLLOFF': rolloff-only customers living in the residential list.\n"
           "-- 310109 HICKS, PETER — 'CREDIT ON ACT' house account (XX).\n"
           "-- Same-name+address pairs with NO distinguishing billing name (possible double entry):\n")
dupes = list(csv.DictReader(open(r"C:/Users/theco/Downloads/santos_sep11_dupes.csv", encoding='utf-8')))
groups = {}
for d in dupes:
    if d['kind'] == 'same_name_addr':
        groups.setdefault(d['group'], []).append(d)
for g in groups.values():
    if all(not d['billing_name'] for d in g):
        out.append("--   " + ' | '.join(f"{d['acct']}{'*' if d['star'] else ''} {d['days'] or 'no days'} start {d['start_date']}" for d in g)
                   + f"   {g[0]['name']} @ {g[0]['address']}\n")

open(OUT, 'w', encoding='utf-8').write(''.join(out))

# ---- 6/7. Status (separate file) ----
starred = [r['acct'] for r in matched if r['star']]
unstarred = [r['acct'] for r in matched if not r['star'] and r['type'] != 'house']
st = [f"-- Santos status sync — ASSUMES '*' in the NetWork All-Accounts export = dormant/closed account.\n"
      f"-- Do not run until that reading is confirmed. Idempotent; Paused accounts are never touched.\n",
      f"\n-- ===== 6. Starred in NetWork ({len(starred)}) -> Inactive (only rows currently Active) =====\n"
      f"UPDATE clients SET status = 'Inactive' WHERE status = 'Active' AND client_id IN (\n"
      + ',\n'.join('  ' + ', '.join(q(a) for a in starred[i:i + 12]) for i in range(0, len(starred), 12)) + "\n);\n",
      f"\n-- ===== 7. Unstarred in NetWork ({len(unstarred)}) -> Active (only rows currently Inactive; Paused kept) =====\n"
      f"UPDATE clients SET status = 'Active' WHERE status = 'Inactive' AND client_id IN (\n"
      + ',\n'.join('  ' + ', '.join(q(a) for a in unstarred[i:i + 12]) for i in range(0, len(unstarred), 12)) + "\n);\n"]
open(OUT_STATUS, 'w', encoding='utf-8').write(''.join(st))
stats['starred'] = len(starred); stats['unstarred'] = len(unstarred)

print(dict(stats))
print(f"-> {OUT}\n-> {OUT_STATUS}")
