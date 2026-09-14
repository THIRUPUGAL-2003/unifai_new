import urllib.request, json, urllib.parse, hashlib, base64, os

test_uris = [
    'https://localhost/callback',
    'http://localhost/callback',
    'http://localhost:3000/callback',
    'http://127.0.0.1/callback',
    'https://unifaiv2.dev-yp.com/api/oauth/callback',
    'https://unifaiv2.dev-yp.com/callback',
    'https://unifaiv2.dev-yp.com',
    'http://unifaiv2.dev-yp.com/api/oauth/callback',
    'https://dev-yp.com/api/oauth/callback',
    'https://example.com/callback',
    'https://canva.com/callback',
    'https://mcp.canva.com/callback',
]

code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode('utf-8')).digest()).decode('utf-8').rstrip('=')

for uri in test_uris:
    reg_payload = {
        'client_name': 'Test Client',
        'redirect_uris': [uri],
        'grant_types': ['authorization_code'],
        'response_types': ['code'],
        'token_endpoint_auth_method': 'none'
    }
    req = urllib.request.Request(
        'https://mcp.canva.com/register',
        data=json.dumps(reg_payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            cid = data.get('client_id')
            params = {
                'client_id': cid,
                'response_type': 'code',
                'redirect_uri': uri,
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256',
                'state': 's123',
            }
            auth_url = 'https://mcp.canva.com/authorize?' + urllib.parse.urlencode(params)
            auth_req = urllib.request.Request(auth_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
            try:
                with urllib.request.urlopen(auth_req) as a_resp:
                    print(f'ALLOWED: {uri} -> {a_resp.status}')
            except urllib.error.HTTPError as ae:
                print(f'BLOCKED: {uri} -> {ae.code}: {ae.read().decode("utf-8", errors="ignore")[:100].strip()}')
    except urllib.error.HTTPError as re:
        print(f'REG FAILED: {uri} -> {re.code}: {re.read().decode("utf-8", errors="ignore")[:100].strip()}')
