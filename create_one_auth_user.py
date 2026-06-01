"""
create_one_auth_user.py — create a single Supabase Auth account (synthetic
username@helm.internal email). Reuse this for new hires too.

Usage:
  python create_one_auth_user.py "<secret_key>" <username> <password>
  e.g.  python create_one_auth_user.py "sb_secret_xxx" jack jacknew1
"""
import sys, json
from urllib.request import Request, urlopen
from urllib.error import HTTPError

SUPABASE_URL = 'https://iiqlhqtyyqctgupalrlc.supabase.co'
EMAIL_DOMAIN = 'helm.internal'

if len(sys.argv) < 4:
    print('Usage: python create_one_auth_user.py "<secret_key>" <username> <password>')
    sys.exit(1)

key = sys.argv[1].strip()
un  = sys.argv[2].strip().lower()
pw  = sys.argv[3]
if len(pw) < 6:
    print('Password must be at least 6 characters.')
    sys.exit(1)

email = f'{un}@{EMAIL_DOMAIN}'
H = {'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}


def api(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    try:
        with urlopen(Request(f'{SUPABASE_URL}{path}', data=data, headers=H, method=method), timeout=30) as r:
            b = r.read().decode()
            return r.status, (json.loads(b) if b else None)
    except HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')


meta = {'username': un, 'display_name': un, 'role': 'staff'}
st, rows = api('GET', f'/rest/v1/users?username=eq.{un}&select=display_name,role')
if st == 200 and rows:
    meta['display_name'] = rows[0].get('display_name') or un
    meta['role'] = rows[0].get('role') or 'staff'

st, resp = api('POST', '/auth/v1/admin/users',
               {'email': email, 'password': pw, 'email_confirm': True, 'user_metadata': meta})
if st in (200, 201):
    print(f'created {email}  (password set to what you passed)')
elif st == 422 and 'already' in str(resp).lower():
    print(f'{email} already exists.')
else:
    print(f'FAIL {email}: {st} {resp}')
