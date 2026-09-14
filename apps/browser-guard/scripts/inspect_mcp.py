import json
import urllib.request
import urllib.error
import http.cookiejar

BASE_URL = "https://unifaiv2.dev-yp.com"
ADMIN_USER = "admin@yespanchi.com"
ADMIN_PASS = "YP2025-2026yp"

cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
urllib.request.install_opener(opener)

def req(path, method="GET", json_data=None):
    url = f"{BASE_URL}{path}"
    headers = {"User-Agent": "UnifAI-QA/1.0", "Accept": "application/json"}
    data = None
    if json_data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(json_data).encode("utf-8")
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(r, timeout=12) as response:
            b = response.read().decode("utf-8")
            try:
                return response.getcode(), json.loads(b)
            except Exception:
                return response.getcode(), b
    except urllib.error.HTTPError as e:
        b = e.read().decode("utf-8")
        try:
            return e.code, json.loads(b)
        except Exception:
            return e.code, b
    except Exception as e:
        return 0, str(e)

code, res = req("/api/session/login", "POST", {"username": ADMIN_USER, "password": ADMIN_PASS})
print("Login:", code, res)

code, res = req("/api/mcp/library?limit=25")
print(f"Library response: HTTP {code}")
print("Keys in library response:", res.keys() if isinstance(res, dict) else res)
if isinstance(res, dict):
    servers = res.get("servers", [])
    print(f"Total available in catalog: {res.get('total_count')}")
    for s in servers[:20]:
        print(f"  * {s.get('name')} | auth={s.get('auth_type')} | conn={s.get('connection_type')} | url={s.get('connection_url')}")

code, clients_res = req("/api/mcp/clients")
print(f"\nClients response: HTTP {code}")
print("Keys in clients response:", clients_res.keys() if isinstance(clients_res, dict) else clients_res)
if isinstance(clients_res, dict):
    print("Clients content:", {k: (len(v) if isinstance(v, list) else v) for k, v in clients_res.items()})

