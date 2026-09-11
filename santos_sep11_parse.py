"""
santos_sep11_parse.py — parse Downloads/AllSantosAcctsSep11.pdf (East End Rubbish
"All Accounts" export, dated 09/11/2026) into santos_sep11.csv for cleanup work.

Based on parse_pdf()/classify() in import_active_accounts.py, with one fix:
in this export a starred account renders as a single glued token
("320368*RAMA"), which the original ACCT_RE (six digits + optional star) never matched, so
every starred account (~950 of 3,140) was silently skipped. This parser splits
that token into acct / star / class. It also captures the extra fields this
export carries: start date, TTL rate, the S flag column, and the
"Optional c/o Billing Name" line.

Output (Downloads, PII — never commit): santos_sep11.csv
"""
import re, csv, sys, pdfplumber
from collections import defaultdict

PDF = sys.argv[1] if len(sys.argv) > 1 else r"C:/Users/theco/Downloads/AllSantosAcctsSep11.pdf"
OUT = sys.argv[2] if len(sys.argv) > 2 else r"C:/Users/theco/Downloads/santos_sep11.csv"

DAYMAP = {'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 'R': 'Thursday', 'F': 'Friday', 'S': 'Saturday'}
DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
ACCT_RE = re.compile(r'^(\d{6})(\*?)([A-Za-z0-9]*)$')   # acct, star, glued class (may be empty)
DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')
MONEY_RE = re.compile(r'^\d+\.\d{2}$')
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
                toks = [w['text'] for w in ws]
                first = toks[0]
                is_sub = (first == '<SubAccount>')
                idx = 1 if is_sub else 0
                m = ACCT_RE.match(toks[idx]) if idx < len(toks) else None
                if m:
                    acct, star, klass = m.group(1), m.group(2) == '*', m.group(3)
                    nxt = idx + 1
                    if not klass and nxt < len(toks):
                        klass = toks[nxt]
                    days_tok = ''
                    date_x = slash_x = None
                    flag = ''
                    for w in ws:
                        if DAYS_X_MIN <= w['x0'] <= DAYS_X_MAX and re.fullmatch(r'[MTWRFS]+', w['text']):
                            days_tok = days_tok or w['text']
                        if DATE_RE.fullmatch(w['text']) and date_x is None:
                            date_x = w['x0']
                        if w['text'] == '/' and slash_x is None:
                            slash_x = w['x0']
                        if 446 <= w['x0'] <= 470 and re.fullmatch(r'[A-Z]', w['text']):
                            flag = w['text']
                    name_min = 110 if is_sub else 50
                    addr_min = 250 if is_sub else 211
                    addr_max = slash_x if slash_x is not None else (date_x if date_x is not None else 359)
                    name_words = [w['text'] for w in ws if name_min <= w['x0'] < addr_min]
                    addr_words = [w['text'] for w in ws if addr_min <= w['x0'] < addr_max]
                    dates = [t for t in toks if DATE_RE.match(t)]
                    money = [t for t in toks if MONEY_RE.match(t)]
                    cur = {
                        'acct': acct, 'klass': klass, 'is_sub': is_sub, 'star': star, 'flag': flag,
                        'name': ' '.join(name_words).rstrip(', ').strip(),
                        'addr': ' '.join(addr_words).strip(),
                        'days': parse_days(days_tok), 'days_raw': days_tok,
                        'start': dates[0] if dates else '', 'ttl': money[-1] if money else '',
                        'billing': '', 'rate_desc': {},
                        'rates': {f'rate{n}': None for n in range(1, 6)},
                    }
                    accounts.append(cur)
                    continue
                if cur is None:
                    continue
                line = ' '.join(toks)
                if line.startswith('Optional c/o Billing Name:'):
                    cur['billing'] = line.split(':', 1)[1].strip()
                    continue
                rm = re.match(r'^Rate(\d) ([\d.]+)/Mo(?: Description:\s*(.*))?$', line)
                if rm and 1 <= int(rm.group(1)) <= 5:
                    n = int(rm.group(1))
                    cur['rates'][f'rate{n}'] = float(rm.group(2))
                    cur['rate_desc'][n] = (rm.group(3) or '').strip()
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


def main():
    accts = classify(parse_pdf(PDF))
    cols = ['acct', 'klass', 'type', 'role', 'master', 'name', 'address', 'days', 'days_raw',
            'star', 'flag', 'start_date', 'ttl_rate', 'billing_name',
            'rate1', 'rate2', 'rate3', 'rate4', 'rate5', 'rate1_desc', 'rate3_desc', 'rate4_desc']
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(cols)
        for a in accts:
            rd = a['rate_desc']
            w.writerow([a['acct'], a['klass'], a['type'], a['role'], a['master'] or '', a['name'], a['addr'],
                        ','.join(a['days']), a['days_raw'], 'Y' if a['star'] else '', a['flag'],
                        a['start'], a['ttl'], a['billing']]
                       + [a['rates'][f'rate{n}'] if a['rates'][f'rate{n}'] is not None else '' for n in range(1, 6)]
                       + [rd.get(1, ''), rd.get(3, ''), rd.get(4, '')])
    print(f"parsed {len(accts)} accounts ({sum(1 for a in accts if a['star'])} starred) -> {OUT}")


if __name__ == '__main__':
    main()
