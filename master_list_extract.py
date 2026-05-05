"""
master_list_extract.py — parse delta export PDF + diff against HELM clients

Step 1 (extractor): Parses delta export test.pdf into structured records,
strict field-level validation, flags any malformed block.

Step 2 (dry-run diff): Pulls current HELM clients via Supabase REST API,
generates per-field diff CSVs. Nothing writes to the database — this is
review-only. Authoritative overwrite policy is assumed for all proposed
changes (PDF wins).

Run: python master_list_extract.py

Outputs (in current dir):
  master_extract.json              — every client, full field set
  master_extract_anomalies.csv     — any block/field that didn't parse
  master_extract_status_codes.csv  — distribution of status codes (RAMA/RZMA/etc)
  dryrun_changes.csv               — per-field changes vs HELM (proposed)
  dryrun_pdf_only.csv              — accts in PDF not in HELM (would CREATE)
  dryrun_helm_only.csv             — accts in HELM not in PDF (NOT touched)
  dryrun_summary.txt               — human-readable counts
"""
import pdfplumber, re, json, csv, sys, collections
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# ─── config ────────────────────────────────────────────────────────────
PDF_PATH = r"C:\Users\theco\OneDrive\Desktop\Nantucket\helm-app\delta export test.pdf"
SUPABASE_URL = 'https://iiqlhqtyyqctgupalrlc.supabase.co'
SUPABASE_ANON = 'sb_publishable_JAASDdg8OERvpDTnEeLd5Q_Re48qR1I'

DAY_LETTER_TO_NAME = {
    'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday',
    'R': 'Thursday', 'F': 'Friday', 'S': 'Saturday'
}

# ─── PDF parsing ───────────────────────────────────────────────────────
SEPARATOR_RE = re.compile(r'^\s*(?:\.\s+){10,}\.?\s*$', re.MULTILINE)

HEADER_RE = re.compile(
    # City: 3+ uppercase letters/digits/spaces. Digits accepted to tolerate data-entry
    # typos like "NANTU7CKET" present in the legacy export (acct 209738).
    r'^(?P<name_addr>.+?)\s+/\s+(?P<city>[A-Z][A-Z0-9][A-Z0-9\s]*?)\s+'
    r'(?P<key_date>\d{2}/\d{2}/\d{2})(?:\s+(?P<flags>.+))?$'
)
ACCT_RE = re.compile(
    r'^(?P<acct>\d{6})\s+(?P<status_code>[A-Z]{2,4})\s+'
    r'(?:(?P<phone>\d{3}\s+\d{3}-\d{4})\s+)?'   # phone is optional — many clients have none
    r'(?P<billing>.+?)\s+UDF Code=\s*(?P<udf>\S*)\s+'
    r'Deposit=\s*(?P<deposit>[\d.]+)$'
)
COUNTY_RE = re.compile(r'^County=\s*(?P<county>.*?)\s+Compactor\(s\)\s*=\s*(?P<comp>\d+)$')
RATE_RE = re.compile(r'^Rate(?P<n>\d)\s+(?P<amt>[\d.]+)/Mo\s+Description:\s*(?P<desc>.*)$')
TOTAL_RE = re.compile(r'^Total\s+(?P<amt>[\d.]+)/Mo\s+Total Fixed Rates1-5/Month$')
ROUTE_HEADER_RE = re.compile(
    r'^(?P<count>\d+) Route Records?\s+'
    r'(?P<day>[A-Z])-(?P<route>\d+)\s+(?P<pos>\d+)(?:\s+(?P<note>.*))?$'
)
ROUTE_CONT_RE = re.compile(
    r'^(?P<day>[A-Z])-(?P<route>\d+)\s+(?P<pos>\d+)(?:\s+(?P<note>.*))?$'
)
# Strip the page-header rows that show up between client blocks:
# "Master List Residential MBQDSAABCDEFGHIJKL SCOPE = ALL , Account# Order DATED 05/05/2026 PAGE N"
# "S E R V I C E   L O C A T I O N"
# "A C C O U N T   I N F O R M A T I O N   B I L L I N G   A D D R E S S   KeyDate Toter Svc_days Codes___"
# "================="  (the row of equals signs)
PAGE_HEADER_PATTERNS = [
    re.compile(r'^Master List Residential.*PAGE\s+\d+\s*$'),
    re.compile(r'^[SAERVICLOTNB]+(\s+[SAERVICLOTNB]+)+\s*$'),
    re.compile(r'^A C C O U N T.*$'),
    re.compile(r'^=+\s*$'),
]

def is_page_header(line):
    return any(p.match(line) for p in PAGE_HEADER_PATTERNS)


def extract_full_text(pdf_path):
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            parts.append(t)
    return "\n".join(parts)


def split_blocks(text):
    """Split full text into per-client blocks using the dotted separator,
    with page-header lines stripped out."""
    raw_blocks = SEPARATOR_RE.split(text)
    cleaned = []
    for blk in raw_blocks:
        lines = []
        for line in blk.split('\n'):
            s = line.strip()
            if not s:
                continue
            if is_page_header(s):
                continue
            lines.append(s)
        if lines:
            cleaned.append(lines)
    return cleaned


def parse_block(lines, anomalies):
    """Parse one client block. Returns dict, or None on failure (logs anomaly).
    Also returns None silently for the PDF's grand-totals footer block at the
    end of the report (not a client)."""
    if not lines:
        return None
    # Skip the grand-totals footer block at the end of the PDF
    if lines[0].startswith('Rate1/Mo Rate2/Mo'):
        return None
    rec = {
        'acct': None, 'name': None, 'service_addr': None, 'service_city': None,
        'key_date': None, 'flags_raw': None, 'days_codes': None, 'days_resolved': [],
        'status_code': None, 'phone': None,
        'billing_addr': None, 'udf_code': None, 'deposit': 0.0,
        'co_billing_name': None, 'county': None, 'compactors': 0,
        'rate1': None, 'rate2': None, 'rate3': None, 'rate4': None, 'rate5': None,
        'rate_total_pdf': None, 'route_records': [],
    }
    i = 0
    # Header (NAME + ADDR / CITY KEYDATE FLAGS)
    m = HEADER_RE.match(lines[i])
    if not m:
        anomalies.append({'reason': 'header line did not match', 'detail': lines[i][:200]})
        return None
    name_addr = m.group('name_addr').strip()
    addr_split = re.match(r'^(?P<name>.+?)\s+(?P<addr>\d+\S*(?:\s+.+)?)$', name_addr)
    if addr_split:
        rec['name'] = addr_split.group('name').strip()
        rec['service_addr'] = addr_split.group('addr').strip()
    else:
        rec['name'] = name_addr
    rec['service_city'] = m.group('city')
    rec['key_date'] = m.group('key_date')
    rec['flags_raw'] = (m.group('flags') or '').strip()
    day_m = re.match(r'^([A-Z]+)', rec['flags_raw'])
    if day_m:
        rec['days_codes'] = day_m.group(1)
        for d in rec['days_codes']:
            if d in DAY_LETTER_TO_NAME:
                rec['days_resolved'].append(DAY_LETTER_TO_NAME[d])
    i += 1

    # Acct line
    if i >= len(lines):
        anomalies.append({'reason': 'block ended after header', 'detail': str(lines)})
        return None
    m = ACCT_RE.match(lines[i])
    if not m:
        anomalies.append({'reason': 'acct line did not match', 'detail': lines[i][:200]})
        return None
    rec['acct'] = m.group('acct')
    rec['status_code'] = m.group('status_code')
    rec['phone'] = (m.group('phone') or '').strip() or None
    rec['billing_addr'] = m.group('billing').strip()
    rec['udf_code'] = m.group('udf')
    rec['deposit'] = float(m.group('deposit'))
    i += 1

    # Optional middle-section lines: c/o billing name, Sales Territory, County
    while i < len(lines):
        line = lines[i]
        if line.startswith('Optional c/o Billing Name'):
            rec['co_billing_name'] = line[len('Optional c/o Billing Name'):].strip()
            i += 1
            continue
        if line.startswith('Sales Territory'):
            # Optional sales-territory tag (only present on a handful of accounts).
            # Capture but don't surface — not used downstream.
            rec.setdefault('sales_territory', line[len('Sales Territory'):].strip())
            i += 1
            continue
        m = COUNTY_RE.match(line)
        if m:
            rec['county'] = m.group('county').strip() or None
            rec['compactors'] = int(m.group('comp'))
            i += 1
            continue
        break

    # Rates (any subset of 1-5)
    while i < len(lines):
        m = RATE_RE.match(lines[i])
        if not m:
            break
        n = int(m.group('n'))
        rec[f'rate{n}'] = float(m.group('amt'))
        i += 1

    # Total
    if i < len(lines):
        m = TOTAL_RE.match(lines[i])
        if m:
            rec['rate_total_pdf'] = float(m.group('amt'))
            i += 1
        else:
            anomalies.append({'acct': rec['acct'], 'reason': 'total line missing/malformed', 'detail': lines[i][:200]})

    # Route records
    if i < len(lines):
        m = ROUTE_HEADER_RE.match(lines[i])
        if not m:
            anomalies.append({'acct': rec['acct'], 'reason': 'route records header missing', 'detail': lines[i][:200]})
        else:
            n_records = int(m.group('count'))
            rec['route_records'].append({
                'day': m.group('day'),
                'route': int(m.group('route')),
                'position': int(m.group('pos')),
                'note': (m.group('note') or '').strip(),
            })
            i += 1
            for j in range(1, n_records):
                if i >= len(lines):
                    anomalies.append({'acct': rec['acct'], 'reason': f'expected {n_records} route records, ran out at {j+1}'})
                    break
                m2 = ROUTE_CONT_RE.match(lines[i])
                if not m2:
                    anomalies.append({'acct': rec['acct'], 'reason': f'route continuation {j+1} did not match', 'detail': lines[i][:200]})
                    break
                rec['route_records'].append({
                    'day': m2.group('day'),
                    'route': int(m2.group('route')),
                    'position': int(m2.group('pos')),
                    'note': (m2.group('note') or '').strip(),
                })
                i += 1

    # Validate: PDF total should equal sum of rates
    if rec['rate_total_pdf'] is not None:
        computed = sum(filter(None, [rec[f'rate{n}'] for n in range(1, 6)]))
        if abs(computed - rec['rate_total_pdf']) > 0.005:
            anomalies.append({
                'acct': rec['acct'],
                'reason': f'rate total mismatch: PDF says {rec["rate_total_pdf"]}, sum is {computed:.2f}',
            })

    return rec


# ─── Supabase fetch ────────────────────────────────────────────────────
def fetch_helm_clients():
    headers = {
        'apikey': SUPABASE_ANON,
        'Authorization': f'Bearer {SUPABASE_ANON}',
    }
    rows = []
    offset = 0
    page_size = 1000
    while True:
        url = f'{SUPABASE_URL}/rest/v1/clients?select=client_id,client_name,address,phone,email,service_day,status,route,route_note,rate1,rate2,rate3,rate4,rate5&order=client_id&offset={offset}&limit={page_size}'
        req = Request(url, headers=headers)
        try:
            with urlopen(req, timeout=30) as resp:
                batch = json.loads(resp.read().decode('utf-8'))
        except HTTPError as e:
            print(f'Supabase fetch failed (HTTP {e.code}): {e.read().decode("utf-8", errors="replace")}')
            sys.exit(1)
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows


# ─── diff ──────────────────────────────────────────────────────────────
def norm(s):
    return (s or '').strip().upper()


def diff_records(pdf_records, helm_rows):
    pdf_by_acct = {r['acct']: r for r in pdf_records if r.get('acct')}
    helm_by_acct = {r['client_id']: r for r in helm_rows}

    changes = []
    for acct, p in pdf_by_acct.items():
        h = helm_by_acct.get(acct)
        if not h:
            continue  # captured separately as pdf_only

        def add(field, helm_val, pdf_val):
            hv = (helm_val if helm_val is not None else '')
            pv = (pdf_val if pdf_val is not None else '')
            if str(hv).strip() != str(pv).strip():
                changes.append({
                    'acct': acct,
                    'name': p.get('name') or h.get('client_name') or '',
                    'field': field,
                    'helm': hv,
                    'pdf': pv,
                })

        # Name (PDF has uppercase; HELM might be lowercase or mixed). Compare case-insensitive.
        if norm(h.get('client_name')) != norm(p.get('name')):
            changes.append({'acct': acct, 'name': p['name'] or '', 'field': 'client_name',
                            'helm': h.get('client_name') or '', 'pdf': p['name'] or ''})

        # Address — also case-insensitive comparison
        if norm(h.get('address')) != norm(p.get('service_addr')):
            changes.append({'acct': acct, 'name': p['name'] or '', 'field': 'address',
                            'helm': h.get('address') or '', 'pdf': p.get('service_addr') or ''})

        # Phone — strip non-digits, compare
        h_phone_digits = re.sub(r'\D', '', h.get('phone') or '')
        p_phone_digits = re.sub(r'\D', '', p.get('phone') or '')
        if h_phone_digits != p_phone_digits:
            changes.append({'acct': acct, 'name': p['name'] or '', 'field': 'phone',
                            'helm': h.get('phone') or '', 'pdf': p.get('phone') or ''})

        # Service days
        proposed_days = ','.join(p['days_resolved']) if p['days_resolved'] else None
        if (h.get('service_day') or None) != proposed_days:
            changes.append({'acct': acct, 'name': p['name'] or '', 'field': 'service_day',
                            'helm': h.get('service_day') or '', 'pdf': proposed_days or ''})

        # Rates 1-5 (PDF wins; treat None vs None as equal)
        for n in range(1, 6):
            hv = h.get(f'rate{n}')
            pv = p.get(f'rate{n}')
            hv_norm = None if hv in (None, '') else float(hv)
            pv_norm = None if pv in (None, '') else float(pv)
            if hv_norm != pv_norm:
                changes.append({'acct': acct, 'name': p['name'] or '', 'field': f'rate{n}',
                                'helm': '' if hv_norm is None else f'{hv_norm:.2f}',
                                'pdf':  '' if pv_norm is None else f'{pv_norm:.2f}'})

    pdf_only = [pdf_by_acct[a] for a in pdf_by_acct if a not in helm_by_acct]
    helm_only = [helm_by_acct[a] for a in helm_by_acct if a not in pdf_by_acct]

    return changes, pdf_only, helm_only


# ─── output ────────────────────────────────────────────────────────────
def write_csv(path, rows, fieldnames):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fieldnames})


def main():
    print(f'[{datetime.now().strftime("%H:%M:%S")}] Reading {PDF_PATH}…')
    text = extract_full_text(PDF_PATH)
    blocks = split_blocks(text)
    print(f'  extracted {len(blocks)} candidate blocks')

    anomalies = []
    records = []
    for blk in blocks:
        rec = parse_block(blk, anomalies)
        if rec:
            records.append(rec)

    print(f'[{datetime.now().strftime("%H:%M:%S")}] Parsed {len(records)} client records, {len(anomalies)} anomalies')

    # Status code distribution
    status_dist = collections.Counter(r['status_code'] for r in records if r.get('status_code'))

    # JSON dump
    with open('master_extract.json', 'w', encoding='utf-8') as f:
        json.dump({
            'extracted_at': datetime.now().isoformat(),
            'pdf_path': PDF_PATH,
            'summary': {
                'total_clients': len(records),
                'total_route_records': sum(len(r['route_records']) for r in records),
                'anomaly_count': len(anomalies),
                'status_code_distribution': dict(status_dist),
            },
            'clients': records,
            'anomalies': anomalies,
        }, f, indent=2, default=str)
    print('  ->master_extract.json')

    # Anomaly CSV
    if anomalies:
        write_csv('master_extract_anomalies.csv', anomalies, ['acct', 'reason', 'detail'])
    else:
        # Always emit the file (empty), so the user knows we checked
        write_csv('master_extract_anomalies.csv', [], ['acct', 'reason', 'detail'])
    print('  ->master_extract_anomalies.csv')

    # Status code distribution CSV
    write_csv('master_extract_status_codes.csv',
              [{'status_code': k, 'count': v} for k, v in status_dist.most_common()],
              ['status_code', 'count'])
    print('  ->master_extract_status_codes.csv')

    # ── dry-run diff ────────────────────────────────────────────────
    print(f'[{datetime.now().strftime("%H:%M:%S")}] Fetching HELM clients via Supabase…')
    helm = fetch_helm_clients()
    print(f'  fetched {len(helm)} HELM client rows')

    changes, pdf_only, helm_only = diff_records(records, helm)
    print(f'  diff: {len(changes)} field changes, {len(pdf_only)} PDF-only, {len(helm_only)} HELM-only')

    write_csv('dryrun_changes.csv', changes, ['acct', 'name', 'field', 'helm', 'pdf'])
    print('  ->dryrun_changes.csv')

    write_csv('dryrun_pdf_only.csv',
              [{'acct': r['acct'], 'name': r['name'] or '',
                'service_addr': r['service_addr'] or '', 'phone': r['phone'] or '',
                'days_codes': r['days_codes'] or '', 'status_code': r['status_code'] or ''}
               for r in pdf_only],
              ['acct', 'name', 'service_addr', 'phone', 'days_codes', 'status_code'])
    print('  ->dryrun_pdf_only.csv')

    write_csv('dryrun_helm_only.csv',
              [{'acct': r['client_id'], 'name': r.get('client_name') or '',
                'address': r.get('address') or '', 'phone': r.get('phone') or '',
                'service_day': r.get('service_day') or '', 'status': r.get('status') or ''}
               for r in helm_only],
              ['acct', 'name', 'address', 'phone', 'service_day', 'status'])
    print('  ->dryrun_helm_only.csv')

    # Summary text
    field_breakdown = collections.Counter(c['field'] for c in changes)
    summary_lines = [
        f'Master list extract + dry-run diff',
        f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        f'PDF: {PDF_PATH}',
        '',
        f'PDF clients parsed:     {len(records)}',
        f'Route records parsed:   {sum(len(r["route_records"]) for r in records)}',
        f'Parse anomalies:        {len(anomalies)}',
        '',
        f'HELM clients in DB:     {len(helm)}',
        '',
        f'Proposed field changes: {len(changes)}',
    ]
    for field, n in field_breakdown.most_common():
        summary_lines.append(f'    {field:<14} {n}')
    summary_lines.append('')
    summary_lines.append(f'PDF accts NOT in HELM (would CREATE):  {len(pdf_only)}')
    summary_lines.append(f'HELM accts NOT in PDF (NOT touched):   {len(helm_only)}')
    summary_lines.append('')
    summary_lines.append('Status code distribution in PDF:')
    for code, n in status_dist.most_common():
        summary_lines.append(f'    {code:<6} {n}')
    summary = '\n'.join(summary_lines)
    with open('dryrun_summary.txt', 'w', encoding='utf-8') as f:
        f.write(summary)
    print('  ->dryrun_summary.txt')
    print()
    print(summary)


if __name__ == '__main__':
    main()
