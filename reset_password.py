"""
reset_password.py — set a new Supabase Auth password for one HELM user.

Usage:
  python reset_password.py "<secret_key>" <username> <newpassword>
  e.g.  python reset_password.py "sb_secret_xxx" david S0me-Strong-Pass!

Use 8+ characters. The user logs in with their username + this new password as
usual; tell them the new one.
"""
import sys, json
from urllib.request import Request, urlopen
from urllib.error import HTTPError

URL = 'https://iiqlhqtyyqctgupalrlc.supabase.co'
DOMAIN = 'helm.internal'

if len(sys.argv) < 4:
    print('Usage: python reset_password.py "<secret_key>" <username> <newpassword>')
    sys.exit(1)
key, un, pw = sys.argv[1].strip(), sys.argv[2].strip().lower(), sys.argv[3]
if len(pw) < 8:
    print('Please use at least 8 characters for the new password.')
    sys.exit(1)
email = f'{un}@{DOMAIN}'
H = {'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}


def api(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    try:
        with urlopen(Request(f'{URL}{path}', data=data, headers=H, method=method), timeout=30) as r:
            b = r.read().decode()
            return r.status, (json.loads(b) if b else None)
    except HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')


st, resp = api('GET', '/auth/v1/admin/users?per_page=200')
uid = None
if st == 200 and isinstance(resp, dict):
    for u in resp.get('users', []):
        if (u.get('email') or '').lower() == email:
            uid = u.get('id'); break
if not uid:
    print(f'No Auth account found for {email} (status {st}). Create it first with create_one_auth_user.py.')
    sys.exit(1)

st, resp = api('PUT', f'/auth/v1/admin/users/{uid}', {'password': pw})
print(f'OK — password updated for {email}' if st in (200, 201) else f'FAIL {st}: {resp}')
