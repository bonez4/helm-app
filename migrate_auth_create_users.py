"""
migrate_auth_create_users.py — Phase 1 of the HELM Supabase Auth migration.

Reads the existing `users` table and creates a matching Supabase Auth account
for each, using a synthetic email (username@helm.internal) and the user's
EXISTING password, so staff log in exactly as before once the code cuts over.

Idempotent: re-running skips users that already have an Auth account.

Run ONCE, locally, with your SERVICE ROLE key
(Supabase dashboard -> Project Settings -> API -> service_role secret).
NEVER commit the key — pass it via environment variable:

  PowerShell:  $env:SUPABASE_SERVICE_ROLE="eyJ..."; python migrate_auth_create_users.py
  bash/git:    SUPABASE_SERVICE_ROLE="eyJ..." python migrate_auth_create_users.py
"""
import os, json, sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError

SUPABASE_URL = 'https://iiqlhqtyyqctgupalrlc.supabase.co'
SERVICE_ROLE = (sys.argv[1].strip() if len(sys.argv) > 1 else None) or os.environ.get('SUPABASE_SERVICE_ROLE')
EMAIL_DOMAIN = 'helm.internal'

if not SERVICE_ROLE:
    print('ERROR: pass your secret key as the first argument, e.g.:')
    print('   python migrate_auth_create_users.py "sb_secret_xxxxxxxx"')
    sys.exit(1)


def api(method, path, payload=None):
    headers = {'apikey': SERVICE_ROLE, 'Authorization': f'Bearer {SERVICE_ROLE}',
               'Content-Type': 'application/json'}
    data = json.dumps(payload).encode() if payload is not None else None
    req = Request(f'{SUPABASE_URL}{path}', data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as r:
            body = r.read().decode()
            return r.status, (json.loads(body) if body else None)
    except HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')


st, users = api('GET', '/rest/v1/users?select=username,password,display_name,role')
if st != 200:
    print('Failed to read users table:', st, users); sys.exit(1)
print(f'{len(users)} users in table\n')

created = skipped = failed = 0
short_pw = []
for u in users:
    un = (u.get('username') or '').strip().lower()
    pw = u.get('password') or ''
    if not un:
        continue
    email = f'{un}@{EMAIL_DOMAIN}'
    if len(pw) < 6:
        short_pw.append(un); failed += 1
        print(f'  SKIP {un}: password < 6 chars (Auth minimum) — will need a reset')
        continue
    payload = {'email': email, 'password': pw, 'email_confirm': True,
               'user_metadata': {'username': un,
                                 'display_name': u.get('display_name') or un,
                                 'role': u.get('role') or 'staff'}}
    st, resp = api('POST', '/auth/v1/admin/users', payload)
    if st in (200, 201):
        created += 1; print(f'  created  {email}')
    elif st == 422 and 'already' in str(resp).lower():
        skipped += 1; print(f'  exists   {email}')
    else:
        failed += 1; print(f'  FAIL     {email}: {st} {resp}')

print(f'\nDONE: created={created}  existing={skipped}  failed={failed}')
if short_pw:
    print('Users with too-short passwords (tell me and I\'ll handle them):', short_pw)
